/// Validate project-manifest input paths before passing them to Git pathspecs.
List<String> validateDartInputPaths(Object? value) {
  if (value is! List || value.isEmpty || value.length > 200) {
    throw const FormatException('source_index.input_paths must be a non-empty array of at most 200 repository-relative paths.');
  }
  final paths = <String>[];
  final seen = <String>{};
  for (final item in value) {
    if (item is! String || item.isEmpty || item.startsWith('/') ||
        item.contains(r'\') || item.contains('\u0000')) {
      throw const FormatException('Every Dart input path must be a safe relative POSIX path.');
    }
    final segments = item.split('/');
    if (segments.any((segment) =>
        segment.isEmpty || segment == '.' || segment == '..' ||
        segment.startsWith('.') ||
        !RegExp(r'^[A-Za-z0-9_-][A-Za-z0-9._-]*$').hasMatch(segment))) {
      throw const FormatException('Dart input path contains an unsafe or unsupported segment.');
    }
    if (!seen.add(item)) {
      throw const FormatException('Dart input paths must be unique.');
    }
    paths.add(item);
  }
  return paths..sort();
}
