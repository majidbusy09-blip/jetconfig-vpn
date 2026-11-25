import 'dart:convert';

import 'package:crypto/crypto.dart';

/// Trusted identity for generated artifacts belonging to one repository revision.
class ProjectArtifactIdentity {
  ProjectArtifactIdentity._({
    required this.projectId,
    required this.repositoryId,
    required this.repositoryFullName,
    required this.defaultBranch,
    required this.manifestSchemaVersion,
    required this.manifestSha256,
    required this.sourceRevision,
  });

  final String projectId;
  final String repositoryId;
  final String repositoryFullName;
  final String defaultBranch;
  final int manifestSchemaVersion;
  final String manifestSha256;
  final String sourceRevision;

  static final RegExp _projectId = RegExp(r'^[a-z][a-z0-9-]*[a-z0-9]$');
  static final RegExp _repositoryId = RegExp(r'^[0-9]{1,20}$');
  static final RegExp _repositoryName =
      RegExp(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$');
  static final RegExp _gitSha = RegExp(r'^(?:[0-9a-f]{40}|[0-9a-f]{64})$');
  static final RegExp _artifactPrefix =
      RegExp(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$');

  factory ProjectArtifactIdentity.fromManifest(
    Map<String, Object?> manifest, {
    required String sourceRevision,
    required String actualRepositoryFullName,
  }) {
    if (!_gitSha.hasMatch(sourceRevision)) {
      throw const FormatException('Pinned source revision must be a full lowercase Git SHA.');
    }
    final projectId = manifest['project_id'];
    final schemaVersion = manifest['schema_version'];
    final repository = manifest['repository'];
    if (projectId is! String || !_projectId.hasMatch(projectId)) {
      throw const FormatException('Manifest project_id is malformed.');
    }
    if (schemaVersion is! int || schemaVersion < 1) {
      throw const FormatException('Manifest schema_version must be a positive integer.');
    }
    if (repository is! Map<String, Object?>) {
      throw const FormatException('Manifest repository object is missing.');
    }
    final repositoryId = repository['repository_id'];
    final fullName = repository['full_name'];
    final defaultBranch = repository['default_branch'];
    if (repositoryId is! String || !_repositoryId.hasMatch(repositoryId)) {
      throw const FormatException('Manifest repository_id must be an immutable numeric ID.');
    }
    if (fullName is! String || !_repositoryName.hasMatch(fullName)) {
      throw const FormatException('Manifest repository full_name is malformed.');
    }
    if (fullName != actualRepositoryFullName) {
      throw const FormatException('Manifest repository identity differs from the checked-out origin.');
    }
    if (defaultBranch is! String || defaultBranch.isEmpty || defaultBranch.length > 255) {
      throw const FormatException('Manifest default_branch is missing or malformed.');
    }
    final digest = sha256.convert(
      utf8.encode(jsonEncode(_canonicalize(manifest))),
    ).toString();
    return ProjectArtifactIdentity._(
      projectId: projectId,
      repositoryId: repositoryId,
      repositoryFullName: fullName,
      defaultBranch: defaultBranch,
      manifestSchemaVersion: schemaVersion,
      manifestSha256: digest,
      sourceRevision: sourceRevision,
    );
  }

  Map<String, Object?> get binding => {
        'project_id': projectId,
        'repository_id': repositoryId,
        'repository_full_name': repositoryFullName,
        'default_branch': defaultBranch,
        'manifest_schema_version': manifestSchemaVersion,
        'manifest_sha256': manifestSha256,
        'base_sha': sourceRevision,
      };

  String get namespaceRoot => [
        'docs',
        'generated',
        'projects',
        projectId,
        repositoryId,
        manifestSha256,
        sourceRevision,
      ].join('/');

  String get resolvedIndexPath => '$namespaceRoot/indexes/resolved_index.json';
  String get criticalPathsPath => '$namespaceRoot/indexes/critical_paths.json';
  String get semanticIndexPath => '$namespaceRoot/indexes/semantic_index.json';

  String artifactName(String prefix) {
    if (!_artifactPrefix.hasMatch(prefix)) {
      throw const FormatException('Workflow artifact prefix is invalid.');
    }
    return [
      prefix,
      projectId,
      repositoryId,
      manifestSha256,
      sourceRevision,
    ].join('-');
  }

  static String repositoryNameFromRemote(String remote) {
    if (remote.isEmpty || remote.contains(String.fromCharCode(92))) {
      throw const FormatException('Git remote is empty or malformed.');
    }
    String path;
    if (remote.startsWith('https://') || remote.startsWith('ssh://')) {
      final uri = Uri.tryParse(remote);
      if (uri == null || uri.host.toLowerCase() != 'github.com') {
        throw const FormatException('Git remote must point to github.com.');
      }
      path = uri.path.replaceFirst(RegExp(r'^/'), '');
    } else {
      final match = RegExp(r'^(?:git@github\.com:)([^\s]+)$').firstMatch(remote);
      if (match == null) {
        throw const FormatException('Git remote is not a supported GitHub URL.');
      }
      path = match.group(1)!;
    }
    if (path.endsWith('.git')) path = path.substring(0, path.length - 4);
    if (!_repositoryName.hasMatch(path)) {
      throw const FormatException('Git remote does not identify owner/repository.');
    }
    return path;
  }

  static Object? _canonicalize(Object? value) {
    if (value is Map) {
      final keys = value.keys.cast<String>().toList()..sort();
      return <String, Object?>{
        for (final key in keys) key: _canonicalize(value[key]),
      };
    }
    if (value is List) return value.map(_canonicalize).toList();
    return value;
  }
}
