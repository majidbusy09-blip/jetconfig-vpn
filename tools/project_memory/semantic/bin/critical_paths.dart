import 'dart:convert';
import 'dart:io';
import 'package:jet_vpn_semantic_memory/critical_path_report.dart';

Future<void> main(List<String> args) async {
  if (args.length != 1 || (args.single != '--write' && args.single != '--check')) {
    stderr.writeln('Usage: dart run bin/critical_paths.dart --write|--check');
    exitCode = 2;
    return;
  }
  final root = Directory.current.parent.parent.parent.absolute;
  final indexFile = File('${root.path}/docs/generated/jet_vpn_resolved_index.json');
  final manifestFile = File('${root.path}/docs/critical_paths.json');
  if (!await indexFile.exists() || !await manifestFile.exists()) {
    stderr.writeln('Missing resolved index or docs/critical_paths.json. Generate the resolved index first.');
    exitCode = 2;
    return;
  }
  final resolvedIndex = jsonDecode(await indexFile.readAsString()) as Map<String, Object?>;
  final manifest = jsonDecode(await manifestFile.readAsString()) as Map<String, Object?>;
  final report = buildCriticalPathReport(resolvedIndex: resolvedIndex, manifest: manifest);
  final rendered = '${const JsonEncoder.withIndent('  ').convert(report)}\n';
  final output = File('${root.path}/docs/generated/jet_vpn_critical_paths.json');

  if (args.single == '--write') {
    await output.parent.create(recursive: true);
    await output.writeAsString(rendered);
    stdout.writeln('Wrote docs/generated/jet_vpn_critical_paths.json');
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
}
