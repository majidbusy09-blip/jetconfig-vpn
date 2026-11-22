import 'dart:io';
import 'package:jet_vpn_semantic_memory/resolved_indexer.dart';

Future<void> main(List<String> args) async {
  if (args.length != 1 || (args.single != '--write' && args.single != '--check')) {
    stderr.writeln('Usage: dart run bin/resolve.dart --write|--check');
    exitCode = 2;
    return;
  }
  final root = Directory.current.parent.parent.parent.absolute;
  final source = File('${root.path}/lib/main.dart');
  final output = File('${root.path}/docs/generated/jet_vpn_resolved_index.json');
  final packageConfig = File('${root.path}/.dart_tool/package_config.json');
  if (!await packageConfig.exists()) {
    stderr.writeln('Missing root .dart_tool/package_config.json. Run flutter pub get at repository root first.');
    exitCode = 2;
    return;
  }
  final git = await Process.run('git', ['rev-parse', 'HEAD:lib/main.dart'], workingDirectory: root.path);
  if (git.exitCode != 0) {
    stderr.writeln('Unable to read lib/main.dart Git blob SHA: ${git.stderr}');
    exitCode = 2;
    return;
  }
  final index = await buildResolvedIndex(
    sourcePath: source.path,
    repositoryRoot: root.path,
    sourceGitBlobSha: (git.stdout as String).trim(),
  );
  final rendered = renderResolvedIndex(index);
  if (args.single == '--write') {
    await output.parent.create(recursive: true);
    await output.writeAsString(rendered);
    stdout.writeln('Wrote docs/generated/jet_vpn_resolved_index.json');
  } else if (!await output.exists() || await output.readAsString() != rendered) {
    stderr.writeln('Resolved index is missing or stale. Regenerate with --write.');
    exitCode = 1;
    return;
  } else {
    stdout.writeln('Resolved index matches lib/main.dart.');
  }
  final summary = index['summary'] as Map<String, Object?>;
  final analyzer = index['analyzer'] as Map<String, Object?>;
  stdout.writeln('Declarations: ${summary['declaration_count']}; call sites: ${summary['call_site_count']}.');
  stdout.writeln('Resolved calls: ${summary['resolved_element_calls']}; unresolved: ${summary['unresolved_element_calls']}; internal edges: ${summary['resolved_call_edges']}.');
  stdout.writeln('Analyzer diagnostics: ${analyzer['diagnostic_count']} (errors: ${analyzer['error_count']}).');
}
