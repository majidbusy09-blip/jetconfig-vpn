import 'dart:io';
import 'package:jet_vpn_semantic_memory/indexer.dart';

Future<void> main(List<String> args) async {
  if (args.length != 1 || (args.single != '--write' && args.single != '--check')) {
    stderr.writeln('Usage: dart run bin/index.dart --write|--check'); exitCode = 2; return;
  }
  final root = Directory.current.parent.parent.parent;
  await writeOrCheck(
    sourceFile: File(root.path + '/lib/main.dart'),
    outputFile: File(root.path + '/docs/generated/jet_vpn_semantic_index.json'),
    write: args.single == '--write',
  );
}
