import 'package:test/test.dart';
import 'package:jet_vpn_semantic_memory/critical_path_report.dart';

void main() {
  test('walks internal resolved edges and reports external and unresolved calls', () {
    final index = <String, Object?>{
      'summary': {'source_file_count': 2},
      'source': {
        'files': [
          {'path': 'lib/a.dart', 'git_blob_sha': 'a'},
          {'path': 'lib/b.dart', 'git_blob_sha': 'b'},
        ],
      },
      'declarations': [
        {
          'id': 'package:fixture/a.dart#start@1',
          'kind': 'method',
          'owner': 'Controller',
          'name': 'start',
          'display_name': 'Controller.start',
          'source_path': 'lib/a.dart',
          'line': 10,
        },
        {
          'id': 'package:fixture/b.dart#refresh@2',
          'kind': 'method',
          'owner': 'Service',
          'name': 'refresh',
          'display_name': 'Service.refresh',
          'source_path': 'lib/b.dart',
          'line': 20,
        },
      ],
      'call_sites': [
        {
          'caller_element_id': 'package:fixture/a.dart#start@1',
          'target_element_id': 'package:fixture/b.dart#refresh@2',
          'target_display_name': 'Service.refresh',
          'target_is_in_repository': true,
          'resolution_status': 'resolved_element',
          'source_path': 'lib/a.dart',
          'line': 11,
          'offset': 100,
          'invocation_kind': 'method',
        },
        {
          'caller_element_id': 'package:fixture/b.dart#refresh@2',
          'target_element_id': 'package:flutter/widgets.dart#notifyListeners@3',
          'target_display_name': 'ChangeNotifier.notifyListeners',
          'target_is_in_repository': false,
          'resolution_status': 'resolved_element',
          'source_path': 'lib/b.dart',
          'line': 21,
          'offset': 200,
          'invocation_kind': 'method',
        },
        {
          'caller_element_id': 'package:fixture/b.dart#refresh@2',
          'target_element_id': null,
          'target_display_name': null,
          'target_is_in_repository': null,
          'resolution_status': 'unresolved',
          'source_path': 'lib/b.dart',
          'line': 22,
          'offset': 220,
          'invocation_kind': 'function_expression',
        },
      ],
    };
    final manifest = {
      'paths': [
        {
          'id': 'fixture',
          'title': 'Fixture',
          'description': 'Test path',
          'entrypoints': [
            {
              'source_path': 'lib/a.dart',
              'kind': 'method',
              'owner': 'Controller',
              'name': 'start',
            },
          ],
        },
      ],
    };

    final report = buildCriticalPathReport(resolvedIndex: index, manifest: manifest);
    final path = (report['paths'] as List).single as Map<String, Object?>;
    final summary = path['summary'] as Map<String, Object?>;
    expect(summary['resolved_entrypoints'], 1);
    expect(summary['reachable_declarations'], 2);
    expect(summary['internal_calls'], 1);
    expect(summary['external_calls'], 1);
    expect(summary['unresolved_calls'], 1);
  });

  test('fails closed when a configured entrypoint is ambiguous', () {
    final declaration = {
      'id': 'package:fixture/a.dart#run@1',
      'kind': 'method',
      'owner': 'Controller',
      'name': 'run',
      'display_name': 'Controller.run',
      'source_path': 'lib/a.dart',
      'line': 10,
    };
    final index = <String, Object?>{
      'summary': {'source_file_count': 1},
      'source': {'files': []},
      'declarations': [declaration, {...declaration, 'id': 'package:fixture/a.dart#run@2'}],
      'call_sites': [],
    };
    final manifest = {
      'paths': [
        {
          'id': 'ambiguous',
          'title': 'Ambiguous',
          'description': 'Test',
          'entrypoints': [
            {
              'source_path': 'lib/a.dart',
              'kind': 'method',
              'owner': 'Controller',
              'name': 'run',
            },
          ],
        },
      ],
    };
    final report = buildCriticalPathReport(resolvedIndex: index, manifest: manifest);
    final path = (report['paths'] as List).single as Map<String, Object?>;
    final summary = path['summary'] as Map<String, Object?>;
    expect(summary['resolved_entrypoints'], 0);
    expect(summary['missing_or_ambiguous_entrypoints'], 1);
    expect((path['unresolved_entrypoints'] as List).single['status'], 'ambiguous');
  });
  test('pins critical-path report to project identity and source revision', () {
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
    final report = buildCriticalPathReport(
      resolvedIndex: {
        'summary': {'source_file_count': 0},
        'source': {'files': []},
        'declarations': [],
        'call_sites': [],
      },
      manifest: {'paths': []},
      projectBinding: binding,
      sourceRevision: revision,
    );
    expect(report['project_binding'], binding);
    expect(report['source_revision'], revision);
    expect(
      () => buildCriticalPathReport(
        resolvedIndex: {
          'summary': {'source_file_count': 0},
          'source': {'files': []},
          'declarations': [],
          'call_sites': [],
        },
        manifest: {'paths': []},
        projectBinding: binding,
        sourceRevision: 'cccccccccccccccccccccccccccccccccccccccc',
      ),
      throwsArgumentError,
    );
  });

}
