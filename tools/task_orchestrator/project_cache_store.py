"""Project-scoped, content-verified local cache for deterministic context packages.

The cache is an optimization only. Security-sensitive handoff verification must
continue rebuilding context from the pinned Git tree without trusting this cache.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from pathlib import Path
from typing import Any

try:
    from .context_builder import build_context
    from .project_artifact_namespace import (
        ProjectArtifactNamespaceError,
        cache_key,
        cache_relative_path,
        ensure_namespace_directory,
        namespace_segments,
    )
except ImportError:
    from context_builder import build_context
    from project_artifact_namespace import (
        ProjectArtifactNamespaceError,
        cache_key,
        cache_relative_path,
        ensure_namespace_directory,
        namespace_segments,
    )

_MAX_CACHE_BYTES = 1_000_000
_CACHE_SCHEMA = 1


class ProjectCacheError(ValueError):
    """A project cache entry is unsafe, corrupt, or bound to another identity."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _package_digest(package: dict[str, Any]) -> str:
    material = dict(package)
    material.pop("context_sha256", None)
    return hashlib.sha256(_canonical(material)).hexdigest()


class ProjectScopedCacheStore:
    """Immutable cache entries isolated by project, repository, manifest and source SHA."""

    def __init__(self, root: str | os.PathLike[str], *, max_bytes: int = _MAX_CACHE_BYTES):
        supplied = Path(root)
        if supplied.is_symlink():
            raise ProjectCacheError("Cache root must not be a symlink.")
        try:
            supplied.mkdir(parents=True, exist_ok=True)
            if supplied.is_symlink() or not supplied.is_dir():
                raise ProjectCacheError("Cache root must be a regular directory.")
            self.root = supplied.resolve(strict=True)
        except OSError as exc:
            raise ProjectCacheError("Cache root could not be prepared safely.") from exc
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 1024 <= max_bytes <= _MAX_CACHE_BYTES:
            raise ProjectCacheError("Cache size limit must be between 1 KB and 1 MB.")
        self.max_bytes = max_bytes

    def _open_namespace(self, binding: dict[str, Any], source_revision: str) -> int:
        try:
            # Reuse the namespace validator/creator, then reopen every component
            # relative to an already-open descriptor to avoid path-based races.
            ensure_namespace_directory(
                self.root, "cache", project_binding=binding, source_revision=source_revision
            )
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            if os.open not in getattr(os, "supports_dir_fd", set()):
                raise ProjectCacheError("Descriptor-relative directory access is unavailable.")
            current = os.open(self.root, flags)
            try:
                for segment in ("projects",) + namespace_segments(binding, source_revision) + ("cache",):
                    try:
                        os.mkdir(segment, mode=0o700, dir_fd=current)
                    except FileExistsError:
                        pass
                    child = os.open(segment, flags, dir_fd=current)
                    os.close(current)
                    current = child
                return current
            except Exception:
                os.close(current)
                raise
        except (OSError, ProjectArtifactNamespaceError) as exc:
            if isinstance(exc, ProjectCacheError):
                raise
            raise ProjectCacheError("Project cache namespace is invalid or unsafe.") from exc

    @staticmethod
    def _filename(key: str) -> str:
        return hashlib.sha256(key.encode("ascii")).hexdigest() + ".json"

    def get(
        self, cache_name: str, *, project_binding: dict[str, Any],
        source_revision: str, input_sha256: str,
    ) -> dict[str, Any] | None:
        try:
            key = cache_key(cache_name, project_binding=project_binding, source_revision=source_revision)
            relative = cache_relative_path(cache_name, project_binding=project_binding, source_revision=source_revision)
            directory = self._open_namespace(project_binding, source_revision)
        except ProjectArtifactNamespaceError as exc:
            raise ProjectCacheError("Cache identity is invalid.") from exc
        try:
            try:
                descriptor = os.open(self._filename(key), os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
            except FileNotFoundError:
                return None
            except OSError as exc:
                raise ProjectCacheError("Cache entry could not be opened safely.") from exc
            try:
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode) or not 1 <= metadata.st_size <= self.max_bytes:
                    raise ProjectCacheError("Cache entry is not a bounded regular file.")
                chunks = []
                remaining = self.max_bytes + 1
                while remaining:
                    chunk = os.read(descriptor, min(65536, remaining))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                raw = b"".join(chunks)
                if len(raw) != metadata.st_size or len(raw) > self.max_bytes:
                    raise ProjectCacheError("Cache entry size changed while reading.")
            finally:
                os.close(descriptor)
            try:
                record = json.loads(raw.decode("utf-8", errors="strict"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ProjectCacheError("Cache entry is not valid UTF-8 JSON.") from exc
            if not isinstance(record, dict) or record.get("schema") != _CACHE_SCHEMA:
                raise ProjectCacheError("Cache entry schema is invalid.")
            if (record.get("cache_key") != key or record.get("cache_path") != relative
                    or record.get("project_binding") != project_binding
                    or record.get("source_revision") != source_revision
                    or record.get("input_sha256") != input_sha256):
                raise ProjectCacheError("Cache entry identity or input fingerprint does not match.")
            package = record.get("package")
            if not isinstance(package, dict) or record.get("package_sha256") != hashlib.sha256(_canonical(package)).hexdigest():
                raise ProjectCacheError("Cached context package digest does not match.")
            if (package.get("project_binding") != project_binding
                    or package.get("source_revision") != source_revision
                    or package.get("context_sha256") != _package_digest(package)):
                raise ProjectCacheError("Cached context package provenance is invalid.")
            return package
        finally:
            os.close(directory)

    def put(
        self, cache_name: str, package: dict[str, Any], *, project_binding: dict[str, Any],
        source_revision: str, input_sha256: str,
    ) -> None:
        if (not isinstance(package, dict) or package.get("project_binding") != project_binding
                or package.get("source_revision") != source_revision
                or package.get("context_sha256") != _package_digest(package)):
            raise ProjectCacheError("Only a valid context package for this exact project/source can be cached.")
        try:
            key = cache_key(cache_name, project_binding=project_binding, source_revision=source_revision)
            relative = cache_relative_path(cache_name, project_binding=project_binding, source_revision=source_revision)
            directory = self._open_namespace(project_binding, source_revision)
        except ProjectArtifactNamespaceError as exc:
            raise ProjectCacheError("Cache identity is invalid.") from exc
        record = {
            "schema": _CACHE_SCHEMA, "cache_key": key, "cache_path": relative,
            "project_binding": project_binding, "source_revision": source_revision,
            "input_sha256": input_sha256,
            "package_sha256": hashlib.sha256(_canonical(package)).hexdigest(),
            "package": package,
        }
        encoded = _canonical(record)
        if len(encoded) > self.max_bytes:
            os.close(directory)
            raise ProjectCacheError("Context package exceeds the cache entry size limit.")
        temporary = ".tmp-" + secrets.token_hex(12)
        filename = self._filename(key)
        descriptor = None
        try:
            descriptor = os.open(
                temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600, dir_fd=directory,
            )
            view = memoryview(encoded)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise ProjectCacheError("Cache write made no progress.")
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            # Hard-link publication is atomic and refuses to replace an existing
            # immutable cache entry. The temporary name is removed afterwards.
            os.link(temporary, filename, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
            os.fsync(directory)
        except FileExistsError:
            existing = self.get(
                cache_name, project_binding=project_binding,
                source_revision=source_revision, input_sha256=input_sha256,
            )
            if existing != package:
                raise ProjectCacheError("An immutable cache key already contains different content.")
        except OSError as exc:
            raise ProjectCacheError("Cache entry could not be published atomically.") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass
            os.close(directory)


def build_context_cached(
    *, cache_root: str | os.PathLike[str] | None = None, **kwargs: Any
) -> dict[str, Any]:
    """Build project context through a local cache; legacy/unbound builds bypass it.

    Cache failures degrade to a direct pinned-tree build. The handoff command
    deliberately calls build_context (not this function) for independent revalidation.
    """
    binding = kwargs.get("project_binding")
    if binding is None:
        return build_context(**kwargs)
    source_revision = kwargs.get("source_revision")
    if not isinstance(source_revision, str):
        return build_context(**kwargs)
    inputs = {
        "cache_format": "context-v1",
        "task_id": kwargs.get("task_id"),
        "source_revision": source_revision,
        "required_paths": kwargs.get("required_paths"),
        "source_paths": kwargs.get("source_paths"),
        "allowed_patterns": kwargs.get("allowed_patterns"),
        "excluded_patterns": kwargs.get("excluded_patterns"),
        "project_binding": binding,
        "memory_manifest_version": kwargs.get("memory_manifest_version"),
        "memory_manifest_max_total_bytes": kwargs.get("memory_manifest_max_total_bytes"),
    }
    input_sha256 = hashlib.sha256(_canonical(inputs)).hexdigest()
    cache_name = "context-v1-" + input_sha256
    root = cache_root or os.environ.get("JET_AI_CACHE_DIR") or (Path.home() / ".cache" / "jet-ai")
    try:
        store = ProjectScopedCacheStore(root)
        cached = store.get(
            cache_name, project_binding=binding, source_revision=source_revision,
            input_sha256=input_sha256,
        )
        if cached is not None:
            return cached
    except ProjectCacheError:
        store = None
    package = build_context(**kwargs)
    if store is not None:
        try:
            store.put(
                cache_name, package, project_binding=binding,
                source_revision=source_revision, input_sha256=input_sha256,
            )
        except ProjectCacheError:
            pass
    return package
