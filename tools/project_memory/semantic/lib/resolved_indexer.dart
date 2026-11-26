import 'dart:convert';
import 'dart:io';
import 'package:analyzer/dart/analysis/analysis_context_collection.dart';
import 'package:analyzer/dart/analysis/results.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';
import 'package:analyzer/dart/element/element.dart';
import 'package:analyzer/source/line_info.dart';

Future<Map<String, Object?>> buildResolvedIndex({
  required List<String> sourcePaths,
  required String repositoryRoot,
  required Map<String, String> sourceGitBlobShas,
  List<String>? configuredInputPaths,
  Map<String, Object?>? projectBinding,
  String? sourceRevision,
}) async {
  if ((projectBinding == null) != (sourceRevision == null)) {
    throw ArgumentError('Project binding and source revision must be supplied together.');
  }
  if (projectBinding != null && projectBinding['base_sha'] != sourceRevision) {
    throw ArgumentError('Project binding must match the pinned source revision.');
  }
  final absoluteRoot = Directory(repositoryRoot).absolute.path;
  final normalizedPaths = sourcePaths.map((path) => File(path).absolute.path).toSet().toList()
    ..sort((a, b) => _relativePath(absoluteRoot, a).compareTo(_relativePath(absoluteRoot, b)));
  if (normalizedPaths.isEmpty) throw ArgumentError('At least one Dart source file is required.');
  final realRoot = await Directory(absoluteRoot).resolveSymbolicLinks();
  for (final path in normalizedPaths) {
    if (!path.startsWith('${absoluteRoot}/')) throw ArgumentError('Source file is outside the repository root: $path');
    if (!path.endsWith('.dart')) throw ArgumentError('Source file is not Dart: $path');
    final type = await FileSystemEntity.type(path, followLinks: false);
    if (type != FileSystemEntityType.file) {
      throw ArgumentError('Source path must be a regular non-symlink file: $path');
    }
    final resolvedPath = await File(path).resolveSymbolicLinks();
    if (resolvedPath != realRoot &&
        !resolvedPath.startsWith('${realRoot}${Platform.pathSeparator}')) {
      throw ArgumentError('Resolved source file escapes the repository root: $path');
    }
  }

  final pubspec = await File('${absoluteRoot}/pubspec.yaml').readAsString();
  final packageName = RegExp(r'^name:\s*([A-Za-z0-9_]+)', multiLine: true).firstMatch(pubspec)?.group(1);
  if (packageName == null) throw StateError('Unable to read the application package name from pubspec.yaml.');

  final collection = AnalysisContextCollection(includedPaths: [absoluteRoot]);
  try {
    final declarations = <Map<String, Object?>>[];
    final calls = <Map<String, Object?>>[];
    final files = <Map<String, Object?>>[];
    var diagnosticCount = 0;
    var errorCount = 0;

    for (final sourcePath in normalizedPaths) {
      final relative = _relativePath(absoluteRoot, sourcePath);
      final blobSha = sourceGitBlobShas[relative];
      if (blobSha == null || blobSha.isEmpty) throw StateError('Missing Git blob SHA for $relative.');
      final context = collection.contextFor(sourcePath);
      final result = await context.currentSession.getResolvedUnit(sourcePath);
      if (result is! ResolvedUnitResult) {
        throw StateError('Analyzer did not return a resolved unit for $sourcePath (${result.runtimeType}).');
      }
      final sourceText = await File(sourcePath).readAsString();
      final visitor = _ResolvedIndexVisitor(
        repositoryRoot: absoluteRoot,
        repositoryPackageName: packageName,
        sourcePath: relative,
        lineInfo: LineInfo.fromContent(sourceText),
      );
      result.unit.accept(visitor);
      declarations.addAll(visitor.declarations);
      calls.addAll(visitor.calls);
      final errors = result.errors;
      final fileErrors = errors.where((e) => e.errorCode.errorSeverity.name == 'ERROR').length;
      diagnosticCount += errors.length;
      errorCount += fileErrors;
      files.add({
        'path': relative,
        'git_blob_sha': blobSha,
        'utf8_bytes': utf8.encode(sourceText).length,
        'lines': LineSplitter.split(sourceText).length,
        'declaration_count': visitor.declarations.length,
        'call_site_count': visitor.calls.length,
        'diagnostic_count': errors.length,
        'error_count': fileErrors,
      });
    }

    final sourceRoots = normalizedPaths
        .map((path) => _relativePath(absoluteRoot, path).split('/').first)
        .toSet()
        .toList()
      ..sort();
    final resolvedCalls = calls.where((call) => call['target_element_id'] != null).length;
    final callerEdges = calls.where((call) =>
        call['caller_element_id'] != null && call['target_element_id'] != null).toList();
    final internalEdges = callerEdges.where((call) => call['target_is_in_repository'] == true).toList();
    return {
      'schema_version': 2,
      if (projectBinding != null) 'project_binding': projectBinding,
      if (sourceRevision != null) 'source_revision': sourceRevision,
      'generator': 'tools/project_memory/semantic/resolved_indexer.dart',
      'analysis_mode': 'dart_analyzer_resolved_elements_multi_file',
      'source': {
        'root': sourceRoots.length == 1 ? '${sourceRoots.single}/' : null,
        'roots': sourceRoots,
        if (configuredInputPaths != null) 'input_paths': configuredInputPaths,
        'file_count': files.length,
        'files': files,
      },
      'analyzer': {
        'package': 'analyzer',
        'version': '6.11.0',
        'resolved_units': files.length,
        'diagnostic_count': diagnosticCount,
        'error_count': errorCount,
      },
      'declarations': declarations,
      'call_sites': calls,
      'call_edges': callerEdges,
      'internal_call_edges': internalEdges,
      'summary': {
        'source_file_count': files.length,
        'declaration_count': declarations.length,
        'call_site_count': calls.length,
        'resolved_element_calls': resolvedCalls,
        'unresolved_element_calls': calls.length - resolvedCalls,
        'resolved_call_edges': callerEdges.length,
        'internal_call_edges': internalEdges.length,
        'external_targets': calls.where((call) =>
            call['target_element_id'] != null && call['target_is_in_repository'] == false).length,
      },
      'limitations': [
        'All tracked Dart files selected by the configured input paths are analyzed; unselected paths are outside this adapter scope.',
        'Edges represent statically resolved analyzer Elements, not runtime execution or reachability.',
        'Dynamic dispatch is represented by the statically selected target; runtime overrides may differ.',
        'Calls through dynamic values, unresolved imports, reflection, generated code, and native boundaries may remain unresolved.',
        'Callback registration and function tear-offs are not equivalent to direct invocation edges.',
        'Analyzer diagnostics are reported and do not automatically mean every unresolved call is a defect.',
      ],
    };
  } finally {
    collection.dispose();
  }
}

class _ResolvedIndexVisitor extends RecursiveAstVisitor<void> {
  _ResolvedIndexVisitor({
    required this.repositoryRoot,
    required this.repositoryPackageName,
    required this.sourcePath,
    required this.lineInfo,
  });
  final String repositoryRoot;
  final String repositoryPackageName;
  final String sourcePath;
  final LineInfo lineInfo;
  int _line(AstNode node) => lineInfo.getLocation(node.offset).lineNumber;
  final List<Map<String, Object?>> declarations = [];
  final List<Map<String, Object?>> calls = [];
  String? _callerId;

  String _elementId(Element element) {
    final uri = element.source?.uri.toString() ?? 'synthetic:';
    final name = element.name ?? '<unnamed>';
    return '$uri#$name@${element.nameOffset}';
  }

  bool _isRepositoryElement(Element element) {
    final uri = element.source?.uri;
    if (uri == null) return false;
    if (uri.scheme == 'package') return uri.pathSegments.isNotEmpty && uri.pathSegments.first == repositoryPackageName;
    if (uri.scheme != 'file') return false;
    final path = uri.toFilePath();
    return path == repositoryRoot || path.startsWith('${repositoryRoot}/');
  }

  String _displayName(Element element) {
    final owner = element.enclosingElement?.name;
    final name = element.name ?? '';
    if (owner == null || owner.isEmpty) return name.isEmpty ? '<unnamed>' : name;
    return name.isEmpty ? owner : '$owner.$name';
  }

  void _recordDeclaration(String kind, String name, Element? element, AstNode node, void Function() visitChildren) {
    final previous = _callerId;
    final id = element == null ? null : _elementId(element);
    declarations.add({
      'id': id,
      'kind': kind,
      'name': name,
      'owner': element?.enclosingElement?.name,
      'display_name': element == null ? name : _displayName(element),
      'source_path': sourcePath,
      'line': _line(node),
      'offset': node.offset,
      'element_resolved': element != null,
      'element_source': element?.source?.uri.toString(),
    });
    if (id != null) _callerId = id;
    visitChildren();
    _callerId = previous;
  }

  void _recordCall(String kind, String expression, ExecutableElement? target, AstNode node) {
    calls.add({
      'caller_element_id': _callerId,
      'invocation_kind': kind,
      'target_expression': expression,
      'target_name': target?.name,
      'target_display_name': target == null ? null : _displayName(target),
      'target_element_id': target == null ? null : _elementId(target),
      'target_element_kind': target?.runtimeType.toString(),
      'target_element_source': target?.source?.uri.toString(),
      'target_is_in_repository': target == null ? null : _isRepositoryElement(target),
      'source_path': sourcePath,
      'line': _line(node),
      'offset': node.offset,
      'resolution_status': target == null ? 'unresolved' : 'resolved_element',
    });
  }

  @override
  void visitFunctionDeclaration(FunctionDeclaration node) =>
      _recordDeclaration('function', node.name.lexeme, node.declaredElement, node, () => node.visitChildren(this));
  @override
  void visitMethodDeclaration(MethodDeclaration node) =>
      _recordDeclaration('method', node.name.lexeme, node.declaredElement, node, () => node.visitChildren(this));
  @override
  void visitConstructorDeclaration(ConstructorDeclaration node) {
    final name = node.name?.lexeme ?? node.returnType.toSource();
    _recordDeclaration('constructor', name, node.declaredElement, node, () => node.visitChildren(this));
  }
  @override
  void visitFunctionExpression(FunctionExpression node) {
    if (node.parent is FunctionDeclaration) {
      super.visitFunctionExpression(node);
      return;
    }
    _recordDeclaration('closure', '<closure>', node.declaredElement, node, () => node.visitChildren(this));
  }
  @override
  void visitMethodInvocation(MethodInvocation node) {
    final element = node.methodName.staticElement;
    _recordCall('method', node.toSource(), element is ExecutableElement ? element : null, node);
    super.visitMethodInvocation(node);
  }
  @override
  void visitFunctionExpressionInvocation(FunctionExpressionInvocation node) {
    _recordCall('function_expression', node.function.toSource(), node.staticElement, node);
    super.visitFunctionExpressionInvocation(node);
  }
  @override
  void visitInstanceCreationExpression(InstanceCreationExpression node) {
    _recordCall('constructor', node.constructorName.toSource(), node.constructorName.staticElement, node);
    super.visitInstanceCreationExpression(node);
  }
  @override
  void visitSuperConstructorInvocation(SuperConstructorInvocation node) {
    _recordCall('super_constructor', node.toSource(), node.staticElement, node);
    super.visitSuperConstructorInvocation(node);
  }
  @override
  void visitRedirectingConstructorInvocation(RedirectingConstructorInvocation node) {
    _recordCall('redirecting_constructor', node.toSource(), node.staticElement, node);
    super.visitRedirectingConstructorInvocation(node);
  }
}

String _relativePath(String root, String path) =>
    path.startsWith('${root}/') ? path.substring(root.length + 1) : path;
String renderResolvedIndex(Map<String, Object?> index) =>
    '${const JsonEncoder.withIndent('  ').convert(index)}\n';
