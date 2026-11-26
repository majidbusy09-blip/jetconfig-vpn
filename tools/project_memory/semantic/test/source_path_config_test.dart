import 'package:test/test.dart';
import 'package:jet_vpn_semantic_memory/source_path_config.dart';

void main() {
  test('accepts distinct manifest-selected repository source roots', () {
    expect(
      validateDartInputPaths(['packages/shared/lib', 'lib']),
      ['lib', 'packages/shared/lib'],
    );
  });

  test('rejects empty, duplicate, absolute, traversal, hidden and pathspec input', () {
    for (final value in <Object?>[
      null,
      [],
      ['lib', 'lib'],
      ['/lib'],
      ['../outside'],
      ['lib/../outside'],
      ['.github'],
      ['lib/*'],
      ['lib:(glob)'],
      [r'lib\src'],
    ]) {
      expect(() => validateDartInputPaths(value), throwsFormatException);
    }
  });
}
