"""Descriptor-relative local file operations for task metadata and reports."""
from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path


class SafeLocalFileError(ValueError):
    """A local file path or operation is unsafe or inconsistent."""


def _parts(relative_path: str) -> tuple[str, ...]:
    if (not isinstance(relative_path, str) or not relative_path
            or relative_path.startswith("/") or "\\" in relative_path):
        raise SafeLocalFileError("A repository-relative POSIX file path is required.")
    parts = tuple(relative_path.split("/"))
    if any(part in {"", ".", ".."} for part in parts):
        raise SafeLocalFileError("Relative file paths cannot contain empty, dot, or parent segments.")
    return parts


def _open_root(root: str | os.PathLike[str]) -> int:
    if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise SafeLocalFileError("Safe no-follow directory operations are unavailable.")
    if os.open not in getattr(os, "supports_dir_fd", set()):
        raise SafeLocalFileError("Descriptor-relative file operations are unavailable.")
    try:
        resolved = Path(root).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise SafeLocalFileError("File-operation root could not be resolved safely.") from exc
    if not resolved.is_dir():
        raise SafeLocalFileError("File-operation root must be an existing directory.")
    parts = resolved.parts
    if not resolved.is_absolute() or not parts or parts[0] != os.sep:
        raise SafeLocalFileError("File-operation root must resolve to an absolute directory.")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current = None
    try:
        current = os.open(os.sep, flags)
        for segment in parts[1:]:
            child = os.open(segment, flags, dir_fd=current)
            metadata = os.fstat(child)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(child)
                raise SafeLocalFileError("File-operation root contains a non-directory component.")
            os.close(current)
            current = child
        return current
    except OSError as exc:
        if current is not None:
            try:
                os.close(current)
            except OSError:
                pass
        raise SafeLocalFileError("File-operation root contains an unsafe or inaccessible path component.") from exc
    except Exception:
        if current is not None:
            try:
                os.close(current)
            except OSError:
                pass
        raise


def ensure_directory(root: str | os.PathLike[str], relative_directory: str) -> None:
    """Create/open every directory component without following symlinks."""
    parts = _parts(relative_directory)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current = _open_root(root)
    try:
        for segment in parts:
            try:
                os.mkdir(segment, mode=0o700, dir_fd=current)
            except FileExistsError:
                pass
            child = os.open(segment, flags, dir_fd=current)
            metadata = os.fstat(child)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(child)
                raise SafeLocalFileError("Directory path contains a non-directory component.")
            os.close(current)
            current = child
    except OSError as exc:
        raise SafeLocalFileError("Directory path could not be created or opened safely.") from exc
    finally:
        os.close(current)


def _open_parent(root: str | os.PathLike[str], relative_path: str, *, create: bool) -> tuple[int, str]:
    parts = _parts(relative_path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current = _open_root(root)
    try:
        for segment in parts[:-1]:
            if create:
                try:
                    os.mkdir(segment, mode=0o700, dir_fd=current)
                except FileExistsError:
                    pass
            child = os.open(segment, flags, dir_fd=current)
            metadata = os.fstat(child)
            if not stat.S_ISDIR(metadata.st_mode):
                os.close(child)
                raise SafeLocalFileError("File parent path contains a non-directory component.")
            os.close(current)
            current = child
        return current, parts[-1]
    except Exception:
        try:
            os.close(current)
        except OSError:
            pass
        raise


def read_bytes(
    root: str | os.PathLike[str], relative_path: str, *, max_bytes: int = 2_000_000
) -> bytes:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise SafeLocalFileError("Input size limit must be a positive integer.")
    parent = None
    descriptor = None
    try:
        parent, leaf = _open_parent(root, relative_path, create=False)
        descriptor = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise SafeLocalFileError("Input must be a regular non-symlink file.")
        if before.st_size > max_bytes:
            raise SafeLocalFileError("Input exceeds its configured size limit.")
        raw = bytearray()
        while len(raw) <= max_bytes:
            chunk = os.read(descriptor, min(65536, max_bytes + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(descriptor)
        stable = (
            before.st_dev == after.st_dev and before.st_ino == after.st_ino
            and before.st_size == after.st_size
            and before.st_mtime_ns == after.st_mtime_ns
            and before.st_ctime_ns == after.st_ctime_ns
        )
        if len(raw) != before.st_size or len(raw) > max_bytes or not stable:
            raise SafeLocalFileError("Input changed while being read or exceeded its size limit.")
        return bytes(raw)
    except SafeLocalFileError:
        raise
    except OSError as exc:
        raise SafeLocalFileError("Input file is missing, unsafe, or unreadable.") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent is not None:
            os.close(parent)


def atomic_write_bytes(
    root: str | os.PathLike[str], relative_path: str, data: bytes, *,
    replace: bool, create_parents: bool = False,
) -> None:
    """Atomically publish bytes under a descriptor-open parent directory."""
    if not isinstance(data, bytes):
        raise SafeLocalFileError("Atomic file data must be bytes.")
    parent = None
    descriptor = None
    temporary = ".tmp-" + secrets.token_hex(12)
    try:
        parent, leaf = _open_parent(root, relative_path, create=create_parents)
        if replace:
            try:
                existing = os.stat(leaf, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                existing = None
            if existing is not None and not stat.S_ISREG(existing.st_mode):
                raise SafeLocalFileError("Existing output must be a regular non-symlink file.")
        descriptor = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600, dir_fd=parent,
        )
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise SafeLocalFileError("Atomic file write made no progress.")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        if replace:
            os.replace(temporary, leaf, src_dir_fd=parent, dst_dir_fd=parent)
        else:
            os.link(temporary, leaf, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
            os.unlink(temporary, dir_fd=parent)
        os.fsync(parent)
    except SafeLocalFileError:
        raise
    except OSError as exc:
        raise SafeLocalFileError("Atomic file publication failed.") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent is not None:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass
            os.close(parent)
