import 'dart:io';
import 'package:test/test.dart';
import 'package:jet_vpn_semantic_memory/resolved_indexer.dart';

void main() {
  late Directory temp;

  setUp(() async {
    temp = await Directory.systemTemp.createTemp('jet-vpn-semantic-test-');
    await File('${temp.path}/pubspec.yaml').writeAsString('name: fixture_app\n');
  });

  tearDown(() async {
    if (await temp.exists()) await temp.delete(recursive: true);
  });

  Future<Map<String, Object?>> analyze(String source) async {
    final file = File('${temp.path}/fixture.dart');
    await file.writeAsString(source);
    return buildResolvedIndex(
      sourcePath: file.path,
      repositoryRoot: temp.path,
      sourceGitBlobSha: 'fixture-blob',
    );
  }

  test('resolves same-named methods to distinct declaration Elements', () async {
    const source = '''
class Alpha {
  void run() {}
  void invoke() { run(); }
}
class Beta {
  void run() {}
  void invoke() { run(); }
}
''';
    final index = await analyze(source);
    final declarations = index['declarations'] as List;
    final calls = (index['call_sites'] as List)
        .where((call) => call['target_name'] == 'run')
        .toList();

    expect(declarations.where((d) => d['name'] == 'run').length, 2);
    expect(calls.length, 2);
    expect(calls.every((call) => call['resolution_status'] == 'resolved_element'), isTrue);
    expect(calls[0]['target_element_id'], isNot(calls[1]['target_element_id']));
    expect(calls.map((call) => call['target_display_name']).toSet(),
        containsAll(['Alpha.run', 'Beta.run']));
  });

  test('resolves constructor and top-level function invocation', () async {
    const source = '''
class Service {
  Service();
  void start() {}
}
void helper() {}
void main() {
  final service = Service();
  service.start();
  helper();
}
''';
    final index = await analyze(source);
    final calls = index['call_sites'] as List;
    expect(calls.any((call) =>
        call['invocation_kind'] == 'constructor' &&
        call['target_element_id'] != null &&
        call['target_expression'].toString().contains('Service')), isTrue);
    expect(calls.any((call) =>
        call['invocation_kind'] == 'method' &&
        call['target_name'] == 'start' &&
        call['resolution_status'] == 'resolved_element'), isTrue);
    expect(calls.any((call) =>
        call['target_name'] == 'helper' &&
        call['resolution_status'] == 'resolved_element'), isTrue);
  });

  test('reports dynamic invocation as unresolved instead of guessing', () async {
    const source = '''
void invoke(dynamic callback) {
  callback();
}
''';
    final index = await analyze(source);
    final call = (index['call_sites'] as List).single;
    expect(call['resolution_status'], 'unresolved');
    expect(call['target_element_id'], isNull);
  });
}
