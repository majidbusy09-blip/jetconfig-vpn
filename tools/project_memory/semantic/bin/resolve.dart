import 'dart:io';
import 'package:jet_vpn_semantic_memory/resolved_indexer.dart';

Future<void> main(List<String> args) async {
  if (args.length != 1 || (args.single != '--write' && args.single != '--check')) {
    stderr.writeln('Usage: dart run bin/resolve.dart --write|--check');
    exitCode = 2;
    return;
  }
  final root = Directory.current.parent.parent.parent.absolute;
  final packageConfig = File('${root.path}/.dart_tool/package_config.json');
  if (!await packageConfig.exists()) {
    stderr.writeln('Missing root .dart_tool/package_config.json. Run flutter pub get at repository root first.');
    exitCode = 2;
    return;
  }

  final tracked = await Process.run(
    'git',
    ['ls-files', '-z', '--', 'lib'],
    workingDirectory: root.path,
  );
  if (tracked.exitCode != 0) {
    stderr.writeln('Unable to enumerate tracked lib/ sources: ${tracked.stderr}');
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
    final git = await Process.run(
      'git',
      ['rev-parse', 'HEAD:$relative'],
      workingDirectory: root.path,
    );
    if (git.exitCode != 0) {
      stderr.writeln('Unable to read Git blob SHA for $relative: ${git.stderr}');
      exitCode = 2;
      return;
    }
    absolutePaths.add(file.path);
    blobShas[relative] = (git.stdout as String).trim();
  }

  final index = await buildResolvedIndex(
    sourcePaths: absolutePaths,
    repositoryRoot: root.path,
    sourceGitBlobShas: blobShas,
  );
  final rendered = renderResolvedIndex(index);
  final output = File('${root.path}/docs/generated/jet_vpn_resolved_index.json');
  if (args.single == '--write') {
    await output.parent.create(recursive: true);
    await output.writeAsString(rendered);
    stdout.writeln('Wrote docs/generated/jet_vpn_resolved_index.json');
  } else if (!await output.exists() || await output.readAsString() != rendered) {
    stderr.writeln('Resolved index is missing or stale. Regenerate with --write.');
    exitCode = 1;
    return;
  } else {
    stdout.writeln('Resolved index matches all tracked lib/**/*.dart files.');
  }
  final summary = index['summary'] as Map<String, Object?>;
  final analyzer = index['analyzer'] as Map<String, Object?>;
  stdout.writeln('Files: ${summary['source_file_count']}; declarations: ${summary['declaration_count']}; call sites: ${summary['call_site_count']}.');
  stdout.writeln('Resolved: ${summary['resolved_element_calls']}; unresolved: ${summary['unresolved_element_calls']}; internal edges: ${summary['internal_call_edges']}.');
  stdout.writeln('Analyzer diagnostics: ${analyzer['diagnostic_count']} (errors: ${analyzer['error_count']}).');
}
