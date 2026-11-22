import 'dart:convert';
import 'dart:io';
import 'package:analyzer/dart/analysis/analysis_context_collection.dart';
import 'package:analyzer/dart/analysis/results.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';
import 'package:analyzer/dart/element/element.dart';
import 'package:analyzer/source/line_info.dart';

/// Builds call sites using analyzer-resolved Elements, not name matching.
Future<Map<String, Object?>> buildResolvedIndex({
  required String sourcePath,
  required String repositoryRoot,
  required String sourceGitBlobSha,
}) async {
  final absoluteSource = File(sourcePath).absolute.path;
  final absoluteRoot = Directory(repositoryRoot).absolute.path;
  final collection = AnalysisContextCollection(includedPaths: [absoluteSource]);
  try {
    final context = collection.contextFor(absoluteSource);
    final result = await context.currentSession.getResolvedUnit(absoluteSource);
    if (result is! ResolvedUnitResult) {
      throw StateError('Analyzer did not return a resolved unit for $absoluteSource (${result.runtimeType}).');
    }
    final sourceText = await File(absoluteSource).readAsString();
    final visitor = _ResolvedIndexVisitor(
      repositoryRoot: absoluteRoot,
      lineInfo: LineInfo.fromContent(sourceText),
    );
    result.unit.accept(visitor);
    final resolved = visitor.calls.where((call) => call['target_element_id'] != null).length;
    final unresolved = visitor.calls.length - resolved;
    final errors = result.errors;
    return {
      'schema_version': 1,
      'generator': 'tools/project_memory/semantic/resolved_indexer.dart',
      'analysis_mode': 'dart_analyzer_resolved_elements',
      'source': {
        'path': _relativePath(absoluteRoot, absoluteSource),
        'git_blob_sha': sourceGitBlobSha,
        'utf8_bytes': utf8.encode(sourceText).length,
        'lines': LineSplitter.split(sourceText).length,
      },
      'analyzer': {
        'package': 'analyzer',
        'version': '6.11.0',
        'resolved_unit': true,
        'diagnostic_count': errors.length,
        'error_count': errors.where((e) => e.errorCode.errorSeverity.name == 'ERROR').length,
      },
      'declarations': visitor.declarations,
      'call_sites': visitor.calls,
      'call_edges': visitor.calls.where((call) => call['caller_element_id'] != null).toList(),
      'summary': {
        'declaration_count': visitor.declarations.length,
        'call_site_count': visitor.calls.length,
        'resolved_element_calls': resolved,
        'unresolved_element_calls': unresolved,
        'resolved_call_edges': visitor.calls.where((call) =>
          call['caller_element_id'] != null && call['target_element_id'] != null).length,
        'external_targets': visitor.calls.where((call) =>
          call['target_element_id'] != null && call['target_is_in_repository'] == false).length,
      },
      'limitations': [
        'Edges represent statically resolved analyzer Elements, not runtime execution or reachability.',
        'Dynamic dispatch is represented by the statically selected target; runtime overrides may differ.',
        'Calls through dynamic values, unresolved imports, reflection, generated code, and native boundaries may remain unresolved.',
        'Only the requested source unit is traversed; declarations in other project files are not indexed yet.',
        'Analyzer diagnostics are reported and do not automatically mean every unresolved call is a defect.',
      ],
    };
  } finally {
    collection.dispose();
  }
}

class _ResolvedIndexVisitor extends RecursiveAstVisitor<void> {
  _ResolvedIndexVisitor({required this.repositoryRoot, required this.lineInfo});
  final String repositoryRoot;
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
    if (uri == null || uri.scheme != 'file') return false;
    final path = uri.toFilePath();
    return path == repositoryRoot || path.startsWith('$repositoryRoot/');
  }

  String _displayName(Element element) {
    final owner = element.enclosingElement?.name;
    return owner == null || owner.isEmpty ? (element.name ?? '<unnamed>') : '$owner.${element.name}';
  }

  void _recordDeclaration(String kind, String name, Element? element, AstNode node,
      void Function() visitChildren) {
    final previous = _callerId;
    final id = element == null ? null : _elementId(element);
    declarations.add({
      'id': id,
      'kind': kind,
      'name': name,
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
      'line': _line(node),
      'offset': node.offset,
      'resolution_status': target == null ? 'unresolved' : 'resolved_element',
    });
  }

  @override
  void visitFunctionDeclaration(FunctionDeclaration node) =>
      _recordDeclaration('function', node.name.lexeme, node.declaredElement, node,
          () => node.visitChildren(this));

  @override
  void visitMethodDeclaration(MethodDeclaration node) =>
      _recordDeclaration('method', node.name.lexeme, node.declaredElement, node,
          () => node.visitChildren(this));

  @override
  void visitConstructorDeclaration(ConstructorDeclaration node) {
    final name = node.name?.lexeme ?? node.returnType.toSource();
    _recordDeclaration('constructor', name, node.declaredElement, node,
        () => node.visitChildren(this));
  }

  @override
  void visitFunctionExpression(FunctionExpression node) {
    if (node.parent is FunctionDeclaration) {
      super.visitFunctionExpression(node);
      return;
    }
    _recordDeclaration('closure', '<closure>', node.declaredElement, node,
        () => node.visitChildren(this));
  }

  @override
  void visitMethodInvocation(MethodInvocation node) {
    _recordCall('method', node.toSource(), node.methodName.staticElement is ExecutableElement ? node.methodName.staticElement as ExecutableElement : null, node);
    super.visitMethodInvocation(node);
  }

  @override
  void visitFunctionExpressionInvocation(FunctionExpressionInvocation node) {
    _recordCall('function_expression', node.function.toSource(), node.staticElement, node);
    super.visitFunctionExpressionInvocation(node);
  }

  @override
  void visitInstanceCreationExpression(InstanceCreationExpression node) {
    _recordCall('constructor', node.constructorName.toSource(),
        node.constructorName.staticElement, node);
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
    path.startsWith('$root/') ? path.substring(root.length + 1) : path;

String renderResolvedIndex(Map<String, Object?> index) =>
    '${const JsonEncoder.withIndent('  ').convert(index)}\n';
