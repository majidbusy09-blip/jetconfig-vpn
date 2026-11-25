"""Local content-addressed patch artifact storage and validation.

Artifacts are stored only in an explicitly supplied local directory. This
module does not fetch from remote services, apply patches, or execute code.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import stat
from pathlib import Path
from typing import Any

from .patch_pipeline import PatchPipelineError, validate_completed_patch
from .project_artifact_namespace import (
    ProjectArtifactNamespaceError,
    ensure_namespace_directory,
    namespace_segments,
    verify_store_namespace,
)

_ARTIFACT_RE = re.compile(r"^artifact:sha256:([0-9a-f]{64})$")
_MAX_ARTIFACT_BYTES = 2_000_000


class PatchArtifactError(ValueError):
    """A patch artifact is missing, unsafe, oversized, or corrupt."""


class LocalPatchArtifactStore:
    """Store immutable UTF-8 patches by SHA-256 in a caller-owned directory."""

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        max_bytes: int = _MAX_ARTIFACT_BYTES,
        project_binding: dict | None = None,
        source_revision: str | None = None,
    ):
        supplied = Path(root)
        if supplied.is_symlink() or not supplied.is_dir():
            raise PatchArtifactError("Artifact root must be an existing regular directory, not a symlink.")
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 1 <= max_bytes <= _MAX_ARTIFACT_BYTES:
            raise PatchArtifactError("Artifact size limit must be between 1 byte and 2 MB.")
        self.project_binding = dict(project_binding) if project_binding is not None else None
        self.source_revision = source_revision
        self.base_root = supplied.resolve(strict=True)
        if project_binding is None:
            if source_revision is not None:
                raise PatchArtifactError("A source revision cannot be supplied without a project binding.")
            self.root = self.base_root
            self.namespace_segments: tuple[str, ...] = ()
        else:
            if source_revision is None:
                raise PatchArtifactError("A project-scoped artifact store requires a pinned source revision.")
            try:
                self.root = ensure_namespace_directory(
                    self.base_root, "patches", project_binding=project_binding,
                    source_revision=source_revision,
                )
                self.namespace_segments = (
                    ("projects",) + namespace_segments(project_binding, source_revision) + ("patches",)
                )
            except ProjectArtifactNamespaceError as exc:
                raise PatchArtifactError("Project artifact namespace is invalid or unsafe.") from exc
        self.max_bytes = max_bytes

    def _open_store_directory(self) -> int:
        """Open the root and namespace by descriptor-relative no-follow traversal."""
        if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
            raise PatchArtifactError("Safe no-follow directory operations are unavailable.")
        if os.open not in getattr(os, "supports_dir_fd", set()):
            raise PatchArtifactError("Descriptor-relative artifact operations are unavailable.")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parts = self.base_root.parts
        if not self.base_root.is_absolute() or not parts or parts[0] != os.sep:
            raise PatchArtifactError("Artifact root must be an absolute resolved directory.")
        try:
            current = os.open(os.sep, flags)
            try:
                for segment in parts[1:] + self.namespace_segments:
                    child = os.open(segment, flags, dir_fd=current)
                    metadata = os.fstat(child)
                    if not stat.S_ISDIR(metadata.st_mode):
                        os.close(child)
                        raise PatchArtifactError("Artifact namespace contains a non-directory component.")
                    os.close(current)
                    current = child
                return current
            except Exception:
                os.close(current)
                raise
        except OSError as exc:
            raise PatchArtifactError("Artifact namespace could not be opened safely.") from exc

    def assert_namespace(self, project_binding: dict | None, source_revision: str) -> None:
        """Verify this store belongs to the exact task project and pinned source."""
        try:
            verify_store_namespace(
                self.project_binding, self.source_revision, project_binding, source_revision
            )
        except ProjectArtifactNamespaceError as exc:
            raise PatchArtifactError("Artifact store belongs to a different project or source revision.") from exc

    def _path_for_ref(self, artifact_ref: str) -> tuple[str, str]:
        if not isinstance(artifact_ref, str):
            raise PatchArtifactError("Artifact reference must be text.")
        match = _ARTIFACT_RE.fullmatch(artifact_ref)
        if not match:
            raise PatchArtifactError("Artifact reference must be artifact:sha256:<64 lowercase hex characters>.")
        digest = match.group(1)
        return digest, digest + ".patch"

    def store_patch(self, patch_text: str) -> str:
        """Persist exact patch text without overwriting an existing digest path."""
        if not isinstance(patch_text, str):
            raise PatchArtifactError("Patch must be UTF-8 text.")
        try:
            encoded = patch_text.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise PatchArtifactError("Patch is not valid UTF-8.") from exc
        if not encoded or len(encoded) > self.max_bytes:
            raise PatchArtifactError("Patch is empty or exceeds the configured artifact size limit.")
        digest = hashlib.sha256(encoded).hexdigest()
        artifact_ref = "artifact:sha256:" + digest
        _, filename = self._path_for_ref(artifact_ref)
        directory = self._open_store_directory()
        temporary = ".tmp-" + secrets.token_hex(12)
        descriptor = None
        published = False
        try:
            descriptor = os.open(
                temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600, dir_fd=directory,
            )
            view = memoryview(encoded)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise PatchArtifactError("Patch artifact write made no progress.")
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            # Atomic immutable publication; a pre-existing digest path is never replaced.
            os.link(temporary, filename, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
            published = True
            os.fsync(directory)
        except FileExistsError:
            existing = self.load_patch(artifact_ref)
            if existing != patch_text:
                raise PatchArtifactError("Existing artifact at this digest does not match its reference.")
            return artifact_ref
        except OSError as exc:
            if published:
                try:
                    os.unlink(filename, dir_fd=directory)
                except OSError:
                    pass
            raise PatchArtifactError("Could not publish the patch artifact safely.") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass
            os.close(directory)
        return artifact_ref

    def load_patch(self, artifact_ref: str) -> str:
        """Read a regular non-symlink artifact and verify its exact digest."""
        digest, filename = self._path_for_ref(artifact_ref)
        directory = self._open_store_directory()
        descriptor = None
        try:
            try:
                descriptor = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            except FileNotFoundError as exc:
                raise PatchArtifactError("Patch artifact does not exist in the local store.") from exc
            except OSError as exc:
                raise PatchArtifactError("Patch artifact could not be opened safely.") from exc
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise PatchArtifactError("Patch artifact must be a regular non-symlink file.")
            if metadata.st_size < 1 or metadata.st_size > self.max_bytes:
                raise PatchArtifactError("Patch artifact is empty or exceeds the configured size limit.")
            raw = bytearray()
            while len(raw) <= self.max_bytes:
                chunk = os.read(descriptor, min(65536, self.max_bytes + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
            after = os.fstat(descriptor)
            stable = (
                after.st_dev == metadata.st_dev and after.st_ino == metadata.st_ino
                and after.st_size == metadata.st_size
                and after.st_mtime_ns == metadata.st_mtime_ns
                and after.st_ctime_ns == metadata.st_ctime_ns
            )
            if len(raw) != metadata.st_size or len(raw) > self.max_bytes or not stable:
                raise PatchArtifactError("Patch artifact changed while being read or exceeded its size limit.")
        finally:
            if descriptor is not None:
                os.close(descriptor)
            os.close(directory)
        actual = hashlib.sha256(raw).hexdigest()
        if actual != digest:
            raise PatchArtifactError("Patch artifact SHA-256 verification failed.")
        try:
            return bytes(raw).decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise PatchArtifactError("Patch artifact is not valid UTF-8.") from exc

    def validate_result_patch(self, result: Any, envelope: dict) -> dict:
        """Load the result's exact artifact and validate digest, scope, and diff."""
        if not isinstance(result, dict):
            raise PatchArtifactError("Agent result must be an object.")
        envelope_binding = envelope.get("project_binding")
        repository = envelope.get("repository")
        source_revision = repository.get("base_sha") if isinstance(repository, dict) else None
        if not isinstance(source_revision, str):
            raise PatchArtifactError("Agent envelope has no pinned source revision.")
        self.assert_namespace(envelope_binding, source_revision)
        artifact_ref = result.get("patch_ref")
        patch_text = self.load_patch(artifact_ref)
        try:
            return validate_completed_patch(result, envelope, patch_text)
        except PatchPipelineError as exc:
            raise PatchArtifactError(str(exc)) from exc
