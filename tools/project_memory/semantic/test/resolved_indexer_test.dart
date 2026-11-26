import 'dart:convert';
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
      sourcePaths: [file.path],
      repositoryRoot: temp.path,
      sourceGitBlobShas: {'fixture.dart': 'fixture-blob'},
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

  test('classifies the application package URI as repository code', () async {
    await Directory('${temp.path}/lib').create(recursive: true);
    await Directory('${temp.path}/.dart_tool').create(recursive: true);
    await File('${temp.path}/pubspec.yaml').writeAsString('name: fixture_app\n');
    await File('${temp.path}/.dart_tool/package_config.json').writeAsString(jsonEncode({
      'configVersion': 2,
      'packages': [
        {
          'name': 'fixture_app',
          'rootUri': '../',
          'packageUri': 'lib/',
          'languageVersion': '3.5',
        },
      ],
    }));
    final file = File('${temp.path}/lib/fixture.dart');
    await file.writeAsString('class Thing { void run() {} void invoke() { run(); } }');
    final index = await buildResolvedIndex(
      sourcePaths: [file.path],
      repositoryRoot: temp.path,
      sourceGitBlobShas: {'lib/fixture.dart': 'fixture-blob'},
    );
    final call = (index['call_sites'] as List)
        .singleWhere((entry) => entry['target_name'] == 'run');
    expect(call['target_element_source'], 'package:fixture_app/fixture.dart');
    expect(call['target_is_in_repository'], isTrue);
  });

  test('resolves cross-file calls across every supplied source unit', () async {
    await Directory('${temp.path}/lib').create(recursive: true);
    await Directory('${temp.path}/.dart_tool').create(recursive: true);
    await File('${temp.path}/.dart_tool/package_config.json').writeAsString(jsonEncode({
      'configVersion': 2,
      'packages': [
        {
          'name': 'fixture_app',
          'rootUri': '../',
          'packageUri': 'lib/',
          'languageVersion': '3.5',
        },
      ],
    }));
    final service = File('${temp.path}/lib/service.dart');
    final screen = File('${temp.path}/lib/screen.dart');
    await service.writeAsString('class Service { void refresh() {} }');
    await screen.writeAsString(
      "import 'package:fixture_app/service.dart'; void main() { Service().refresh(); }",
    );
    final index = await buildResolvedIndex(
      sourcePaths: [screen.path, service.path],
      repositoryRoot: temp.path,
      sourceGitBlobShas: {
        'lib/service.dart': 'service-blob',
        'lib/screen.dart': 'screen-blob',
      },
    );
    final summary = index['summary'] as Map<String, Object?>;
    expect(summary['source_file_count'], 2);
    expect(summary['internal_call_edges'], greaterThanOrEqualTo(1));
    final call = (index['call_sites'] as List)
        .singleWhere((entry) => entry['target_name'] == 'refresh');
    expect(call['target_is_in_repository'], isTrue);
    expect(call['target_element_source'], 'package:fixture_app/service.dart');
    expect(call['source_path'], 'lib/screen.dart');
    expect(call['target_element_id'], isNotNull);
  });

  test('rejects a tracked Dart source path that is a symlink outside the repository', () async {
    final outside = await Directory.systemTemp.createTemp('resolved-index-outside-');
    try {
      final outsideFile = File('${outside.path}/secret.dart');
      await outsideFile.writeAsString('void secret() {}');
      final link = Link('${temp.path}/lib');
      await link.create(outside.path);
      await expectLater(
        buildResolvedIndex(
          sourcePaths: ['${temp.path}/lib/secret.dart'],
          repositoryRoot: temp.path,
          sourceGitBlobShas: {'lib/secret.dart': 'tracked-link-blob'},
        ),
        throwsArgumentError,
      );
    } finally {
      await outside.delete(recursive: true);
    }
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
  test('pins resolved index output to project manifest and source revision', () async {
    final file = File('${temp.path}/fixture.dart');
    await file.writeAsString('void main() {}');
    const revision = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
    final binding = <String, Object?>{
      'project_id': 'fixture-app',
      'repository_id': '123456',
      'repository_full_name': 'owner/fixture-app',
      'default_branch': 'main',
      'manifest_schema_version': 1,
      'manifest_sha256': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
      'base_sha': revision,
    };
    final index = await buildResolvedIndex(
      sourcePaths: [file.path],
      repositoryRoot: temp.path,
      sourceGitBlobShas: {'fixture.dart': 'fixture-blob'},
      projectBinding: binding,
      sourceRevision: revision,
    );
    expect(index['project_binding'], binding);
    expect(index['source_revision'], revision);
    await expectLater(
      buildResolvedIndex(
        sourcePaths: [file.path],
        repositoryRoot: temp.path,
        sourceGitBlobShas: {'fixture.dart': 'fixture-blob'},
        projectBinding: binding,
        sourceRevision: 'cccccccccccccccccccccccccccccccccccccccc',
      ),
      throwsArgumentError,
    );
  });

  test('records all source roots for manifest-selected multi-root Dart input', () async {
    await Directory('${temp.path}/lib').create(recursive: true);
    await Directory('${temp.path}/packages/shared/lib').create(recursive: true);
    final app = File('${temp.path}/lib/main.dart');
    final shared = File('${temp.path}/packages/shared/lib/shared.dart');
    await app.writeAsString('void main() {}');
    await shared.writeAsString('class Shared {}');
    final index = await buildResolvedIndex(
      sourcePaths: [app.path, shared.path],
      repositoryRoot: temp.path,
      sourceGitBlobShas: {
        'lib/main.dart': 'app-blob',
        'packages/shared/lib/shared.dart': 'shared-blob',
      },
      configuredInputPaths: ['lib', 'packages/shared/lib'],
    );
    final source = index['source'] as Map<String, Object?>;
    expect(source['roots'], ['lib', 'packages/shared/lib']);
    expect(source['input_paths'], ['lib', 'packages/shared/lib']);
    expect(source['file_count'], 2);
  });

}
