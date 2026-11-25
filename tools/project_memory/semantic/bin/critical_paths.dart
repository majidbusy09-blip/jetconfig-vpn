import 'dart:convert';
import 'dart:io';

import 'package:jet_vpn_semantic_memory/critical_path_report.dart';
import 'package:jet_vpn_semantic_memory/project_namespace.dart';

Map<String, String> _parseOptions(List<String> args) {
  final result = <String, String>{};
  for (final argument in args) {
    if (argument == '--write' || argument == '--check') {
      if (result.containsKey('mode')) throw const FormatException('Choose exactly one mode.');
      result['mode'] = argument.substring(2);
      continue;
    }
    final separator = argument.indexOf('=');
    if (!argument.startsWith('--') || separator < 3) {
      throw const FormatException('Options must use --name=value syntax.');
    }
    final key = argument.substring(2, separator);
    final value = argument.substring(separator + 1);
    if (value.isEmpty || result.containsKey(key)) {
      throw FormatException('Option --$key is empty or duplicated.');
    }
    if (!{'repository-root', 'project-manifest', 'source-revision', 'critical-paths-manifest'}.contains(key)) {
      throw FormatException('Unsupported option --$key.');
    }
    result[key] = value;
  }
  if (result['mode'] == null) throw const FormatException('Missing --write or --check.');
  if (result.containsKey('source-revision') && !result.containsKey('project-manifest')) {
    throw const FormatException('--source-revision requires --project-manifest.');
  }
  return result;
}

Future<String> _git(Directory root, List<String> arguments) async {
  final result = await Process.run('git', arguments, workingDirectory: root.path);
  if (result.exitCode != 0) {
    throw StateError('Git command failed: ${arguments.join(' ')}: ${result.stderr}');
  }
  return (result.stdout as String).trim();
}

Future<ProjectArtifactIdentity?> _loadIdentity(
  Map<String, String> options,
  Directory root,
) async {
  final manifestPath = options['project-manifest'];
  if (manifestPath == null) return null;
  final revision = options['source-revision'];
  if (revision == null) throw const FormatException('Project indexing requires --source-revision.');
  final file = File(manifestPath);
  if (await FileSystemEntity.type(file.path, followLinks: false) != FileSystemEntityType.file) {
    throw StateError('Project manifest must be a regular non-symlink file.');
  }
  final manifest = jsonDecode(await file.readAsString()) as Map<String, Object?>;
  final actualHead = await _git(root, ['rev-parse', 'HEAD']);
  if (actualHead != revision) {
    throw StateError('Pinned source revision differs from the checked-out repository HEAD.');
  }
  final remote = await _git(root, ['remote', 'get-url', 'origin']);
  final repositoryName = ProjectArtifactIdentity.repositoryNameFromRemote(remote);
  return ProjectArtifactIdentity.fromManifest(
    manifest,
    sourceRevision: revision,
    actualRepositoryFullName: repositoryName,
  );
}

Future<void> main(List<String> args) async {
  try {
    final options = _parseOptions(args);
    final root = Directory(
      options['repository-root'] ?? Directory.current.parent.parent.parent.path,
    ).absolute;
    final identity = await _loadIdentity(options, root);
    final indexPath = identity?.resolvedIndexPath ??
        'docs/generated/jet_vpn_resolved_index.json';
    final indexFile = File('${root.path}/$indexPath');
    final manifestPath = options['critical-paths-manifest'] ??
        '${root.path}/docs/critical_paths.json';
    final suppliedManifest = File(manifestPath);
    final manifestFile = suppliedManifest.isAbsolute
        ? suppliedManifest
        : File('${root.path}/$manifestPath');
    if (!await indexFile.exists() || !await manifestFile.exists()) {
      stderr.writeln('Missing resolved index or critical-path manifest. Generate the resolved index first.');
      exitCode = 2;
      return;
    }
    final resolvedIndex = jsonDecode(await indexFile.readAsString()) as Map<String, Object?>;
    if (identity != null &&
        (resolvedIndex['project_binding'] != identity.binding ||
         resolvedIndex['source_revision'] != identity.sourceRevision)) {
      stderr.writeln('Resolved index belongs to a different project, manifest, or source revision.');
      exitCode = 2;
      return;
    }
    final manifest = jsonDecode(await manifestFile.readAsString()) as Map<String, Object?>;
    final report = buildCriticalPathReport(
      resolvedIndex: resolvedIndex,
      manifest: manifest,
      projectBinding: identity?.binding,
      sourceRevision: identity?.sourceRevision,
    );
    final rendered = '${const JsonEncoder.withIndent('  ').convert(report)}\n';
    final outputPath = identity?.criticalPathsPath ??
        'docs/generated/jet_vpn_critical_paths.json';
    final output = File('${root.path}/$outputPath');

    if (options['mode'] == 'write') {
      await output.parent.create(recursive: true);
      await output.writeAsString(rendered);
      stdout.writeln('Wrote $outputPath');
    } else if (!await output.exists() || await output.readAsString() != rendered) {
      stderr.writeln('Critical-path report is missing or stale. Regenerate with --write.');
      exitCode = 1;
      return;
    } else {
      stdout.writeln('Critical-path report matches the resolved index and manifest.');
    }

    final paths = (report['paths'] as List).cast<Map<String, Object?>>();
    for (final path in paths) {
      final summary = path['summary'] as Map<String, Object?>;
      stdout.writeln(
        "${path['id']}: ${summary['resolved_entrypoints']}/${summary['configured_entrypoints']} entrypoints; "
        "${summary['reachable_declarations']} declarations; ${summary['reachable_calls']} calls; "
        "${summary['unresolved_calls']} unresolved.",
      );
    }
    if (identity != null) {
      stdout.writeln('Project: ${identity.projectId}/${identity.repositoryId}; source: ${identity.sourceRevision}.');
    }
  } on FormatException catch (error) {
    stderr.writeln('BLOCKED: ${error.message}');
    stderr.writeln('Usage: dart run bin/critical_paths.dart --write|--check [--repository-root=PATH --project-manifest=PATH --source-revision=FULL_GIT_SHA --critical-paths-manifest=PATH]');
    exitCode = 2;
  } on Object catch (error) {
    stderr.writeln('BLOCKED: $error');
    exitCode = 2;
  }
}
