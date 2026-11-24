"""Pure, fail-closed validation primitives for the JET AI project registry.

This module validates declarative data only. It performs no I/O, network access,
subprocess execution, persistence, GitHub mutation, or project-code execution.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import urlsplit


class ProjectRegistryError(ValueError):
    """A project manifest or registry binding failed closed validation."""


_SCHEMA_KEYWORDS = {
    "$ref", "$defs", "$schema", "$id", "title", "description", "examples",
    "type", "properties", "required", "additionalProperties", "enum", "const",
    "minLength", "maxLength", "pattern", "format", "items", "minItems",
    "maxItems", "uniqueItems", "minimum", "maximum", "allOf", "if", "then",
}
_ANNOTATIONS = {"$schema", "$id", "title", "description", "examples"}
_SUPPORTED_TYPES = {"object", "array", "string", "integer", "number", "boolean", "null"}
_SCHEMA_ID = "urn:jet-ai:schema:project-manifest:v1"
_PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")
_REPOSITORY_ID_RE = re.compile(r"^[0-9]{1,20}$")


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ProjectRegistryError("Value cannot be represented as canonical JSON.") from exc


def manifest_digest(manifest: dict[str, Any]) -> str:
    """Return a deterministic SHA-256 digest of the complete manifest."""
    if not isinstance(manifest, dict):
        raise ProjectRegistryError("Project manifest must be an object.")
    return hashlib.sha256(_canonical_json(manifest)).hexdigest()


def loads_unique_json(raw: str) -> Any:
    """Parse JSON while rejecting duplicate object keys."""
    if not isinstance(raw, str):
        raise ProjectRegistryError("JSON input must be text.")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ProjectRegistryError("JSON contains a duplicate object key.")
            result[key] = value
        return result

    try:
        return json.loads(raw, object_pairs_hook=unique_object, parse_constant=lambda _: (_ for _ in ()).throw(
            ProjectRegistryError("JSON contains a non-finite numeric constant.")
        ))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ProjectRegistryError("JSON input is malformed.") from exc


def _resolve_local_ref(root: dict[str, Any], ref: Any) -> dict[str, Any]:
    if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
        raise ProjectRegistryError("Only local #/$defs references are supported.")
    parts = ref[2:].split("/")
    current: Any = root
    for raw_part in parts:
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise ProjectRegistryError("Schema contains an unresolved local reference.")
        current = current[part]
    if not isinstance(current, dict):
        raise ProjectRegistryError("Schema reference must resolve to an object.")
    return current


def _check_schema_node(node: Any, root: dict[str, Any], active_refs: set[str]) -> None:
    if not isinstance(node, dict):
        raise ProjectRegistryError("Every schema node must be an object.")
    unknown = set(node) - _SCHEMA_KEYWORDS
    if unknown:
        raise ProjectRegistryError("Schema uses unsupported keyword(s): " + ", ".join(sorted(unknown)))
    if "$ref" in node:
        ref = node["$ref"]
        if ref in active_refs:
            raise ProjectRegistryError("Recursive schema references are not supported.")
        target = _resolve_local_ref(root, ref)
        _check_schema_node(target, root, active_refs | {ref})
    if "type" in node:
        value = node["type"]
        if not isinstance(value, str) or value not in _SUPPORTED_TYPES:
            raise ProjectRegistryError("Schema declares an unsupported type.")
    if "required" in node:
        required = node["required"]
        if not isinstance(required, list) or any(not isinstance(item, str) for item in required) or len(required) != len(set(required)):
            raise ProjectRegistryError("Schema required must be a unique array of strings.")
    if "additionalProperties" in node and not isinstance(node["additionalProperties"], (bool, dict)):
        raise ProjectRegistryError("Schema additionalProperties must be a boolean or schema object.")
    if "enum" in node and (not isinstance(node["enum"], list) or not node["enum"]):
        raise ProjectRegistryError("Schema enum must be a non-empty array.")
    if "pattern" in node:
        if not isinstance(node["pattern"], str):
            raise ProjectRegistryError("Schema pattern must be text.")
        try:
            re.compile(node["pattern"])
        except re.error as exc:
            raise ProjectRegistryError("Schema contains an invalid regular expression.") from exc
    if "format" in node and node["format"] != "uri":
        raise ProjectRegistryError("Only the URI format is supported.")
    for key in ("minLength", "maxLength", "minItems", "maxItems"):
        if key in node and (isinstance(node[key], bool) or not isinstance(node[key], int) or node[key] < 0):
            raise ProjectRegistryError(f"Schema {key} must be a non-negative integer.")
    for key in ("minimum", "maximum"):
        if key in node and (isinstance(node[key], bool) or not isinstance(node[key], (int, float))):
            raise ProjectRegistryError(f"Schema {key} must be numeric.")
    if "uniqueItems" in node and not isinstance(node["uniqueItems"], bool):
        raise ProjectRegistryError("Schema uniqueItems must be boolean.")
    if "items" in node and not isinstance(node["items"], dict):
        raise ProjectRegistryError("Only object-valued items schemas are supported.")
    for key in ("properties", "$defs"):
        value = node.get(key)
        if value is not None:
            if not isinstance(value, dict):
                raise ProjectRegistryError(f"Schema {key} must be an object.")
            for child in value.values():
                _check_schema_node(child, root, active_refs)
    if "items" in node and isinstance(node["items"], dict):
        _check_schema_node(node["items"], root, active_refs)
    if "additionalProperties" in node and isinstance(node["additionalProperties"], dict):
        _check_schema_node(node["additionalProperties"], root, active_refs)
    for key in ("allOf",):
        if key in node:
            if not isinstance(node[key], list) or not node[key]:
                raise ProjectRegistryError(f"Schema {key} must be a non-empty array.")
            for child in node[key]:
                _check_schema_node(child, root, active_refs)
    for key in ("if", "then"):
        if key in node:
            _check_schema_node(node[key], root, active_refs)


def validate_schema_definition(schema: dict[str, Any]) -> None:
    """Validate the supported schema subset and reject remote/unknown features."""
    if not isinstance(schema, dict):
        raise ProjectRegistryError("Project manifest schema must be an object.")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ProjectRegistryError("Unsupported JSON Schema dialect.")
    if schema.get("$id") != _SCHEMA_ID:
        raise ProjectRegistryError("Unexpected project manifest schema identity.")
    _check_schema_node(schema, schema, set())
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ProjectRegistryError("Project manifest schema must be a closed root object.")


def _is_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _validate_instance(value: Any, node: dict[str, Any], root: dict[str, Any],
                       path: str, active_refs: set[str] | None = None) -> None:
    active_refs = active_refs or set()
    if "$ref" in node:
        ref = node["$ref"]
        if ref in active_refs:
            raise ProjectRegistryError(f"{path}: recursive schema reference.")
        _validate_instance(value, _resolve_local_ref(root, ref), root, path, active_refs | {ref})

    expected = node.get("type")
    if expected is not None and not _is_type(value, expected):
        raise ProjectRegistryError(f"{path}: expected {expected}.")

    if "const" in node and value != node["const"]:
        raise ProjectRegistryError(f"{path}: value does not match the required constant.")
    if "enum" in node and value not in node["enum"]:
        raise ProjectRegistryError(f"{path}: value is not in the allowed enumeration.")

    if isinstance(value, dict):
        required = node.get("required", [])
        if not isinstance(required, list) or any(not isinstance(k, str) for k in required):
            raise ProjectRegistryError("Schema required must be an array of strings.")
        missing = set(required) - value.keys()
        if missing:
            raise ProjectRegistryError(f"{path}: missing required field(s): " + ", ".join(sorted(missing)))
        properties = node.get("properties", {})
        if not isinstance(properties, dict):
            raise ProjectRegistryError("Schema properties must be an object.")
        for key, item in value.items():
            if key in properties:
                _validate_instance(item, properties[key], root, f"{path}.{key}", active_refs)
            elif node.get("additionalProperties") is False:
                raise ProjectRegistryError(f"{path}: unknown field {key!r}.")
            elif isinstance(node.get("additionalProperties"), dict):
                _validate_instance(item, node["additionalProperties"], root, f"{path}.{key}", active_refs)

    if isinstance(value, list):
        if "minItems" in node and len(value) < node["minItems"]:
            raise ProjectRegistryError(f"{path}: array has too few items.")
        if "maxItems" in node and len(value) > node["maxItems"]:
            raise ProjectRegistryError(f"{path}: array has too many items.")
        if node.get("uniqueItems") is True:
            encoded = [_canonical_json(item) for item in value]
            if len(encoded) != len(set(encoded)):
                raise ProjectRegistryError(f"{path}: array items must be unique.")
        item_schema = node.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_instance(item, item_schema, root, f"{path}[{index}]", active_refs)

    if isinstance(value, str):
        if "minLength" in node and len(value) < node["minLength"]:
            raise ProjectRegistryError(f"{path}: string is too short.")
        if "maxLength" in node and len(value) > node["maxLength"]:
            raise ProjectRegistryError(f"{path}: string is too long.")
        if "pattern" in node and re.search(node["pattern"], value) is None:
            raise ProjectRegistryError(f"{path}: string does not match its required pattern.")
        if node.get("format") == "uri":
            parsed = urlsplit(value)
            if not parsed.scheme or not parsed.netloc or any(ch.isspace() for ch in value):
                raise ProjectRegistryError(f"{path}: value is not a valid absolute URI.")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in node and value < node["minimum"]:
            raise ProjectRegistryError(f"{path}: number is below the minimum.")
        if "maximum" in node and value > node["maximum"]:
            raise ProjectRegistryError(f"{path}: number exceeds the maximum.")

    for sub_schema in node.get("allOf", []):
        _validate_instance(value, sub_schema, root, path, active_refs)
    if "if" in node:
        try:
            _validate_instance(value, node["if"], root, path, active_refs)
            condition_matches = True
        except ProjectRegistryError:
            condition_matches = False
        if condition_matches and "then" in node:
            _validate_instance(value, node["then"], root, path, active_refs)


def validate_manifest_schema(manifest: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Validate one manifest against the checked-in schema subset."""
    validate_schema_definition(schema)
    _validate_instance(manifest, schema, schema, "$")
    return manifest


def validate_repository_binding(manifest: dict[str, Any], repository_metadata: dict[str, Any]) -> None:
    """Compare manifest identity with a trusted, already-fetched GitHub repository object."""
    if not isinstance(repository_metadata, dict):
        raise ProjectRegistryError("Trusted GitHub repository metadata is required.")
    repo = manifest.get("repository") if isinstance(manifest, dict) else None
    if not isinstance(repo, dict):
        raise ProjectRegistryError("Manifest repository binding is missing.")
    metadata_id = repository_metadata.get("id")
    if isinstance(metadata_id, bool) or not isinstance(metadata_id, (int, str)):
        raise ProjectRegistryError("GitHub repository metadata has no valid immutable numeric ID.")
    metadata_id = str(metadata_id)
    if not _REPOSITORY_ID_RE.fullmatch(metadata_id):
        raise ProjectRegistryError("GitHub repository metadata ID is malformed.")
    expected = {
        "repository_id": metadata_id,
        "full_name": repository_metadata.get("full_name"),
        "url": repository_metadata.get("html_url"),
        "default_branch": repository_metadata.get("default_branch"),
    }
    for key, actual in expected.items():
        if not isinstance(actual, str) or not actual:
            raise ProjectRegistryError(f"Trusted GitHub metadata is missing {key}.")
        if repo.get(key) != actual:
            raise ProjectRegistryError(f"Manifest repository {key} does not match trusted GitHub metadata.")
    parsed = urlsplit(expected["url"])
    if parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.path.rstrip("/") != "/" + expected["full_name"] or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ProjectRegistryError("Trusted GitHub repository URL is not canonical.")


def validate_registry_uniqueness(manifest: dict[str, Any],
                                 existing_manifests: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> None:
    """Reject reuse of project IDs or immutable repository IDs, even for retired records."""
    if not isinstance(existing_manifests, (list, tuple)):
        raise ProjectRegistryError("Existing registry records must be a list or tuple.")
    project_id = manifest.get("project_id")
    repo = manifest.get("repository", {})
    repository_id = repo.get("repository_id") if isinstance(repo, dict) else None
    if not isinstance(project_id, str) or not _PROJECT_ID_RE.fullmatch(project_id):
        raise ProjectRegistryError("Candidate project_id is invalid.")
    if not isinstance(repository_id, str) or not _REPOSITORY_ID_RE.fullmatch(repository_id):
        raise ProjectRegistryError("Candidate immutable repository_id is invalid.")
    for existing in existing_manifests:
        if not isinstance(existing, dict) or not isinstance(existing.get("repository"), dict):
            raise ProjectRegistryError("Existing registry contains a malformed record; refusing registration.")
        existing_project_id = existing.get("project_id")
        existing_repository_id = existing["repository"].get("repository_id")
        if not isinstance(existing_project_id, str) or not _PROJECT_ID_RE.fullmatch(existing_project_id):
            raise ProjectRegistryError("Existing registry contains an invalid project_id; refusing registration.")
        if not isinstance(existing_repository_id, str) or not _REPOSITORY_ID_RE.fullmatch(existing_repository_id):
            raise ProjectRegistryError("Existing registry contains an invalid repository_id; refusing registration.")
        if existing_project_id == project_id:
            raise ProjectRegistryError("project_id is already reserved in the registry.")
        if existing_repository_id == repository_id:
            raise ProjectRegistryError("repository_id is already bound in the registry.")


def validate_runner_profiles(manifest: dict[str, Any], available_profiles: set[str] | frozenset[str]) -> None:
    """Ensure required profiles are declared supported and have fixed runners."""
    if not isinstance(available_profiles, (set, frozenset)) or any(
        not isinstance(item, str) or not item for item in available_profiles
    ):
        raise ProjectRegistryError("Implemented verification profiles must be an explicit string set.")
    verification = manifest.get("verification")
    if not isinstance(verification, dict):
        raise ProjectRegistryError("Manifest verification declaration is missing.")
    required = verification.get("required_profiles")
    supported = verification.get("supported_profiles")
    if not isinstance(required, list) or not isinstance(supported, list):
        raise ProjectRegistryError("Manifest verification profile lists are malformed.")
    if not set(required).issubset(set(supported)):
        raise ProjectRegistryError("Every required profile must also be declared as supported by the project.")
    unavailable = set(required) - set(available_profiles)
    if unavailable:
        raise ProjectRegistryError(
            "Required verification runner(s) are not implemented: " + ", ".join(sorted(unavailable))
        )


def ensure_implementation_eligible(manifest: dict[str, Any]) -> None:
    """Only explicitly active projects may receive new implementation tasks."""
    if not isinstance(manifest, dict) or manifest.get("lifecycle") != "active":
        raise ProjectRegistryError("Project lifecycle is not active; implementation tasks are blocked.")


def validate_project_manifest(
    manifest: dict[str, Any],
    *,
    schema: dict[str, Any],
    repository_metadata: dict[str, Any],
    existing_manifests: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    available_profiles: set[str] | frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """Validate schema, live repository binding, uniqueness, and runner readiness."""
    validate_manifest_schema(manifest, schema)
    validate_repository_binding(manifest, repository_metadata)
    validate_registry_uniqueness(manifest, existing_manifests)
    validate_runner_profiles(manifest, available_profiles)
    return {
        "project_id": manifest["project_id"],
        "repository_id": manifest["repository"]["repository_id"],
        "manifest_sha256": manifest_digest(manifest),
        "lifecycle": manifest["lifecycle"],
        "implementation_eligible": manifest["lifecycle"] == "active",
    }
