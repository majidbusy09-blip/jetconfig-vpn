import 'dart:convert';
import 'dart:io';

import 'package:jet_vpn_semantic_memory/project_namespace.dart';
import 'package:jet_vpn_semantic_memory/resolved_indexer.dart';

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
    if (!{'repository-root', 'project-manifest', 'source-revision'}.contains(key)) {
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
  final suppliedManifest = File(manifestPath);
  final manifestFile = suppliedManifest.isAbsolute
      ? suppliedManifest
      : File('${root.path}/$manifestPath');
  if (await FileSystemEntity.type(manifestFile.path, followLinks: false) !=
      FileSystemEntityType.file) {
    throw StateError('Project manifest must be a regular non-symlink file.');
  }
  final manifest = jsonDecode(await manifestFile.readAsString()) as Map<String, Object?>;
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
    final packageConfig = File('${root.path}/.dart_tool/package_config.json');
    if (!await packageConfig.exists()) {
      stderr.writeln('Missing root .dart_tool/package_config.json. Run flutter pub get at repository root first.');
      exitCode = 2;
      return;
    }
    final identity = await _loadIdentity(options, root);

    final tracked = await Process.run(
      'git',
      ['ls-files', '-z', '--', 'lib'],
      workingDirectory: root.path,
    );
    if (tracked.exitCode != 0) {
      stderr.writeln('Unable to enumerate tracked Dart sources: ${tracked.stderr}');
      exitCode = 2;
      return;
    }
    final sourcePaths = (tracked.stdout as String)
        .split('\u0000')
        .where((path) => path.endsWith('.dart'))
        .toList()
      ..sort();
    if (sourcePaths.isEmpty) {
      stderr.writeln('No tracked Dart source files found under lib/.');
      exitCode = 2;
      return;
    }

    final absolutePaths = <String>[];
    final blobShas = <String, String>{};
    for (final relative in sourcePaths) {
      final file = File('${root.path}/$relative');
      if (!await file.exists()) {
        stderr.writeln('Tracked source file is missing from the working tree: $relative');
        exitCode = 2;
        return;
      }
      final blobSha = await _git(root, ['rev-parse', 'HEAD:$relative']);
      absolutePaths.add(file.path);
      blobShas[relative] = blobSha;
    }

    final index = await buildResolvedIndex(
      sourcePaths: absolutePaths,
      repositoryRoot: root.path,
      sourceGitBlobShas: blobShas,
      projectBinding: identity?.binding,
      sourceRevision: identity?.sourceRevision,
    );
    final rendered = renderResolvedIndex(index);
    final outputPath = identity?.resolvedIndexPath ??
        'docs/generated/jet_vpn_resolved_index.json';
    final output = File('${root.path}/$outputPath');
    if (identity != null) {
      await identity.ensureOutputParent(root, outputPath, createMissing: options['mode'] == 'write');
    }
    if (options['mode'] == 'write') {
      if (identity == null) await output.parent.create(recursive: true);
      await output.writeAsString(rendered);
      stdout.writeln('Wrote $outputPath');
    } else if (!await output.exists() || await output.readAsString() != rendered) {
      stderr.writeln('Resolved index is missing or stale. Regenerate with --write.');
      exitCode = 1;
      return;
    } else {
      stdout.writeln('Resolved index matches the tracked Dart sources and project identity.');
    }
    final summary = index['summary'] as Map<String, Object?>;
    final analyzer = index['analyzer'] as Map<String, Object?>;
    stdout.writeln('Files: ${summary['source_file_count']}; declarations: ${summary['declaration_count']}; call sites: ${summary['call_site_count']}.');
    stdout.writeln('Resolved: ${summary['resolved_element_calls']}; unresolved: ${summary['unresolved_element_calls']}; internal edges: ${summary['internal_call_edges']}.');
    stdout.writeln('Analyzer diagnostics: ${analyzer['diagnostic_count']} (errors: ${analyzer['error_count']}).');
    if (identity != null) {
      stdout.writeln('Project: ${identity.projectId}/${identity.repositoryId}; source: ${identity.sourceRevision}.');
    }
  } on FormatException catch (error) {
    stderr.writeln('BLOCKED: ${error.message}');
    stderr.writeln('Usage: dart run bin/resolve.dart --write|--check [--repository-root=PATH --project-manifest=PATH --source-revision=FULL_GIT_SHA]');
    exitCode = 2;
  } on Object catch (error) {
    stderr.writeln('BLOCKED: $error');
    exitCode = 2;
  }
}
