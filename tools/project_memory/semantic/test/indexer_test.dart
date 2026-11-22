import 'package:test/test.dart';
import 'package:jet_vpn_semantic_memory/indexer.dart';

void main() {
  test('extracts declarations and syntactic caller-to-callee candidates', () {
    const source = '''
void main() {
  final service = Service();
  service.start();
  helper();
}
void helper() {}
class Service {
  void start() { helper(); }
}
''';
    final index = buildSemanticIndex(source: source, sourcePath: 'fixture.dart', gitBlobSha: null);
    final declarations = index['declarations'] as List;
    final calls = index['call_sites'] as List;
    final edges = index['call_edges'] as List;
    expect(declarations.any((e) => e['name'] == 'main'), isTrue);
    expect(declarations.any((e) => e['name'] == 'start' && e['owner'] == 'Service'), isTrue);
    expect(calls.any((e) => e['invocation_kind'] == 'constructor' && e['target_name'] == 'Service'), isTrue);
    expect(edges.any((e) => (e['caller_id'] as String).startsWith('main#') && e['target_name'] == 'helper'), isTrue);
    expect(edges.any((e) => (e['caller_id'] as String).contains('Service.start#') && e['target_name'] == 'helper'), isTrue);
  });
  test('fails closed on invalid Dart syntax', () {
    expect(() => buildSemanticIndex(source: 'void main( {', sourcePath: 'bad.dart', gitBlobSha: null), throwsFormatException);
  });
  test('marks duplicate-name candidates as ambiguous, not resolved', () {
    const source = 'class A { void run() {} } class B { void run() {} } void caller() { run(); }';
    final index = buildSemanticIndex(source: source, sourcePath: 'fixture.dart', gitBlobSha: null);
    final call = (index['call_sites'] as List).firstWhere((e) => e['target_name'] == 'run');
    expect(call['name_match_status'], 'ambiguous_name_candidates');
    expect(call['candidate_count'], 2);
  });
}
