import 'dart:convert';
import 'dart:io';

import 'package:test/test.dart';

Future<String> _git(Directory root, List<String> args) async {
  final result = await Process.run('git', args, workingDirectory: root.path);
  if (result.exitCode != 0) {
    throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
  }
  return (result.stdout as String).trim();
}

void main() {
  test('resolve CLI indexes every tracked Dart path declared by the project manifest', () async {
    final root = await Directory.systemTemp.createTemp('manifest-driven-resolve-');
    try {
      await _git(root, ['init', '-b', 'main']);
      await _git(root, ['config', 'user.name', 'JET AI Test']);
      await _git(root, ['config', 'user.email', 'jet-ai-test@example.invalid']);
      await _git(root, ['remote', 'add', 'origin', 'https://github.com/owner/fixture-app.git']);

      await Directory('${root.path}/lib').create(recursive: true);
      await Directory('${root.path}/packages/shared/lib').create(recursive: true);
      await Directory('${root.path}/.dart_tool').create(recursive: true);
      await Directory('${root.path}/docs').create(recursive: true);

      await File('${root.path}/pubspec.yaml').writeAsString('name: fixture_app\n');
      await File('${root.path}/.dart_tool/package_config.json').writeAsString(jsonEncode({
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
      await File('${root.path}/lib/main.dart').writeAsString('void main() {}');
      await File('${root.path}/packages/shared/lib/shared.dart').writeAsString('class Shared {}');

      final manifest = {
        'schema_version': 1,
        'project_id': 'fixture-app',
        'repository': {
          'repository_id': '123456',
          'full_name': 'owner/fixture-app',
          'default_branch': 'main',
        },
        'source_index': {
          'strategy': 'dart_analyzer',
          'input_paths': ['packages/shared/lib', 'lib'],
        },
      };
      final manifestFile = File('${root.path}/docs/project-manifest.json');
      await manifestFile.writeAsString(jsonEncode(manifest));

      await _git(root, ['add', '.']);
      await _git(root, ['commit', '-m', 'fixture']);
      final revision = await _git(root, ['rev-parse', 'HEAD']);

      final result = await Process.run(
        Platform.resolvedExecutable,
        [
          'run',
          'bin/resolve.dart',
          '--write',
          '--repository-root=${root.path}',
          '--project-manifest=${manifestFile.path}',
          '--source-revision=$revision',
        ],
        workingDirectory: Directory.current.path,
      );
      expect(
        result.exitCode,
        0,
        reason: '${result.stdout}\n${result.stderr}',
      );

      final generated = await root
          .list(recursive: true)
          .where((entry) => entry is File && entry.path.endsWith('/resolved_index.json'))
          .toList();
      expect(generated.length, 1);
      final index = jsonDecode(await (generated.single as File).readAsString())
          as Map<String, dynamic>;
      expect(index['source_revision'], revision);
      final source = index['source'] as Map<String, dynamic>;
      expect(source['input_paths'], ['lib', 'packages/shared/lib']);
      expect(source['roots'], ['lib', 'packages/shared/lib']);
      final files = (source['files'] as List)
          .map((entry) => (entry as Map<String, dynamic>)['path'])
          .toList();
      expect(files, ['lib/main.dart', 'packages/shared/lib/shared.dart']);
    } finally {
      await root.delete(recursive: true);
    }
  });
}
