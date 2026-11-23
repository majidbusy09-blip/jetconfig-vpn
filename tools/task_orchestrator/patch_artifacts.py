"""Local content-addressed patch artifact storage and validation.

Artifacts are stored only in an explicitly supplied local directory. This
module does not fetch from remote services, apply patches, or execute code.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path
from typing import Any

from .patch_pipeline import PatchPipelineError, validate_completed_patch

_ARTIFACT_RE = re.compile(r"^artifact:sha256:([0-9a-f]{64})$")
_MAX_ARTIFACT_BYTES = 2_000_000


class PatchArtifactError(ValueError):
    """A patch artifact is missing, unsafe, oversized, or corrupt."""


class LocalPatchArtifactStore:
    """Store immutable UTF-8 patches by SHA-256 in a caller-owned directory."""

    def __init__(self, root: str | os.PathLike[str], *, max_bytes: int = _MAX_ARTIFACT_BYTES):
        supplied = Path(root)
        if supplied.is_symlink() or not supplied.is_dir():
            raise PatchArtifactError("Artifact root must be an existing regular directory, not a symlink.")
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 1 <= max_bytes <= _MAX_ARTIFACT_BYTES:
            raise PatchArtifactError("Artifact size limit must be between 1 byte and 2 MB.")
        self.root = supplied.resolve(strict=True)
        self.max_bytes = max_bytes

    def _path_for_ref(self, artifact_ref: str) -> tuple[str, Path]:
        if not isinstance(artifact_ref, str):
            raise PatchArtifactError("Artifact reference must be text.")
        match = _ARTIFACT_RE.fullmatch(artifact_ref)
        if not match:
            raise PatchArtifactError("Artifact reference must be artifact:sha256:<64 lowercase hex characters>.")
        digest = match.group(1)
        return digest, self.root / (digest + ".patch")

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
        _, target = self._path_for_ref(artifact_ref)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(target, flags, 0o600)
        except FileExistsError:
            # Content-addressed collisions must contain exactly the same bytes.
            existing = self.load_patch(artifact_ref)
            if existing != patch_text:
                raise PatchArtifactError("Existing artifact at this digest does not match its reference.")
            return artifact_ref
        except OSError as exc:
            raise PatchArtifactError("Could not create the patch artifact safely.") from exc
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            try:
                target.unlink()
            except OSError:
                pass
            raise
        return artifact_ref

    def load_patch(self, artifact_ref: str) -> str:
        """Read a regular non-symlink artifact and verify its exact digest."""
        digest, target = self._path_for_ref(artifact_ref)
        try:
            metadata = target.lstat()
        except FileNotFoundError as exc:
            raise PatchArtifactError("Patch artifact does not exist in the local store.") from exc
        except OSError as exc:
            raise PatchArtifactError("Patch artifact metadata could not be read.") from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise PatchArtifactError("Patch artifact must be a regular non-symlink file.")
        if metadata.st_size < 1 or metadata.st_size > self.max_bytes:
            raise PatchArtifactError("Patch artifact is empty or exceeds the configured size limit.")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(target, flags)
        except OSError as exc:
            raise PatchArtifactError("Patch artifact could not be opened safely.") from exc
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode) or opened.st_size != metadata.st_size:
                raise PatchArtifactError("Patch artifact changed while it was being opened.")
            with os.fdopen(descriptor, "rb") as stream:
                raw = stream.read(self.max_bytes + 1)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise
        if len(raw) != metadata.st_size or len(raw) > self.max_bytes:
            raise PatchArtifactError("Patch artifact size changed or exceeded the configured limit.")
        actual = hashlib.sha256(raw).hexdigest()
        if actual != digest:
            raise PatchArtifactError("Patch artifact SHA-256 verification failed.")
        try:
            return raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise PatchArtifactError("Patch artifact is not valid UTF-8.") from exc

    def validate_result_patch(self, result: Any, envelope: dict) -> dict:
        """Load the result's exact artifact and validate digest, scope, and diff."""
        if not isinstance(result, dict):
            raise PatchArtifactError("Agent result must be an object.")
        artifact_ref = result.get("patch_ref")
        patch_text = self.load_patch(artifact_ref)
        try:
            return validate_completed_patch(result, envelope, patch_text)
        except PatchPipelineError as exc:
            raise PatchArtifactError(str(exc)) from exc
