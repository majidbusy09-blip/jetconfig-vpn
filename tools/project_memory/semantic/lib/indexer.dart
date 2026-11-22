import 'dart:convert';
import 'dart:io';
import 'package:analyzer/dart/analysis/utilities.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';
import 'package:analyzer/source/line_info.dart';

Map<String, Object?> buildSemanticIndex({required String source, required String sourcePath, required String? gitBlobSha}) {
  final parsed = parseString(content: source, path: sourcePath, throwIfDiagnostics: false);
  if (parsed.errors.isNotEmpty) {
    throw FormatException('Dart AST parsing failed for $sourcePath:\n${parsed.errors.join('\n')}');
  }
  final visitor = _IndexVisitor(parsed.lineInfo);
  parsed.unit.accept(visitor);
  final byName = <String, List<Map<String, Object?>>>{};
  for (final d in visitor.declarations) {
    byName.putIfAbsent(d['name']! as String, () => []).add(d);
  }
  final callSites = visitor.calls.map((call) {
    final candidates = byName[call['target_name']] ?? const <Map<String, Object?>>[];
    return {
      ...call,
      'candidate_declaration_ids': candidates.map((e) => e['id']).toList(),
      'candidate_count': candidates.length,
      'name_match_status': candidates.isEmpty ? 'unresolved_name' : candidates.length == 1 ? 'unique_name_candidate' : 'ambiguous_name_candidates',
    };
  }).toList();
  final edges = callSites.where((e) => e['caller_id'] != null).map((e) => {
    'caller_id': e['caller_id'], 'target_name': e['target_name'],
    'candidate_declaration_ids': e['candidate_declaration_ids'], 'candidate_count': e['candidate_count'],
    'name_match_status': e['name_match_status'], 'line': e['line'], 'invocation_kind': e['invocation_kind'],
  }).toList();
  return {
    'schema_version': 1,
    'generator': 'tools/project_memory/semantic',
    'analysis_mode': 'dart_ast_syntactic_call_graph',
    'source': {'path': sourcePath, 'git_blob_sha': gitBlobSha, 'utf8_bytes': utf8.encode(source).length, 'unicode_code_points': source.runes.length, 'lines': source.split('\n').length},
    'parser': {'package': 'analyzer', 'version': '6.11.0', 'parse_errors': 0},
    'declarations': visitor.declarations, 'call_sites': callSites, 'call_edges': edges,
    'summary': {
      'declaration_count': visitor.declarations.length, 'call_site_count': callSites.length, 'call_edge_count': edges.length,
      'unique_name_candidates': callSites.where((e) => e['name_match_status'] == 'unique_name_candidate').length,
      'ambiguous_name_candidates': callSites.where((e) => e['name_match_status'] == 'ambiguous_name_candidates').length,
      'unresolved_names': callSites.where((e) => e['name_match_status'] == 'unresolved_name').length,
    },
    'limitations': [
      'AST-based syntactic call-site extraction; this is not analyzer element resolution.',
      'Name candidates are not proof of semantic binding; same-name methods may belong to unrelated classes.',
      'Dynamic dispatch, tear-offs, reflection, generated code, callbacks, and runtime reachability are not resolved.',
      'Calls through variables/function-typed values may remain unresolved.',
      'Only lib/main.dart is indexed in this initial stage.',
    ],
  };
}

class _IndexVisitor extends RecursiveAstVisitor<void> {
  _IndexVisitor(this.lineInfo);
  final LineInfo lineInfo;
  final declarations = <Map<String, Object?>>[];
  final calls = <Map<String, Object?>>[];
  final _classNames = <String>[];
  String? _currentCallable;
  int _line(int offset) => lineInfo.getLocation(offset).lineNumber;
  String _id(String kind, String name, int line) =>
      (_classNames.isEmpty ? '' : _classNames.join('.') + '.') + name + '#' + kind + '@' + line.toString();

  void _declare(String kind, String name, AstNode node, void Function() children) {
    final line = _line(node.offset);
    final id = _id(kind, name, line);
    declarations.add({'id': id, 'kind': kind, 'name': name, 'owner': _classNames.isEmpty ? null : _classNames.join('.'), 'line': line, 'offset': node.offset});
    final previous = _currentCallable;
    _currentCallable = id;
    children();
    _currentCallable = previous;
  }
  void _call(String kind, String name, String expression, AstNode node) {
    calls.add({'caller_id': _currentCallable, 'invocation_kind': kind, 'target_name': name, 'target_expression': expression, 'line': _line(node.offset), 'offset': node.offset});
  }

  @override
  void visitClassDeclaration(ClassDeclaration node) {
    _classNames.add(node.name.lexeme); node.visitChildren(this); _classNames.removeLast();
  }
  @override
  void visitMixinDeclaration(MixinDeclaration node) {
    _classNames.add(node.name.lexeme); node.visitChildren(this); _classNames.removeLast();
  }
  @override
  void visitEnumDeclaration(EnumDeclaration node) {
    _classNames.add(node.name.lexeme); node.visitChildren(this); _classNames.removeLast();
  }
  @override
  void visitExtensionDeclaration(ExtensionDeclaration node) {
    _classNames.add(node.name?.lexeme ?? '(unnamed extension)'); node.visitChildren(this); _classNames.removeLast();
  }
  @override
  void visitFunctionDeclaration(FunctionDeclaration node) =>
      _declare('function', node.name.lexeme, node, () => node.visitChildren(this));
  @override
  void visitMethodDeclaration(MethodDeclaration node) =>
      _declare('method', node.name.lexeme, node, () => node.visitChildren(this));
  @override
  void visitConstructorDeclaration(ConstructorDeclaration node) {
    final owner = _classNames.isEmpty ? '(unknown owner)' : _classNames.last;
    _declare('constructor', node.name?.lexeme ?? owner, node, () => node.visitChildren(this));
  }
  @override
  void visitMethodInvocation(MethodInvocation node) {
    _call('method', node.methodName.name, node.target == null ? node.methodName.name : node.target!.toSource() + '.' + node.methodName.name, node);
    super.visitMethodInvocation(node);
  }
  @override
  void visitFunctionExpressionInvocation(FunctionExpressionInvocation node) {
    final expression = node.function.toSource();
    _call('function_expression', expression, expression, node);
    super.visitFunctionExpressionInvocation(node);
  }
  @override
  void visitInstanceCreationExpression(InstanceCreationExpression node) {
    final expression = node.constructorName.toSource();
    _call('constructor', node.constructorName.type.toSource().split('<').first.split('.').last, expression, node);
    super.visitInstanceCreationExpression(node);
  }
}

String renderIndex(Map<String, Object?> index) => '${const JsonEncoder.withIndent('  ').convert(index)}\n';

Future<void> writeOrCheck({required File sourceFile, required File outputFile, required bool write}) async {
  final source = await sourceFile.readAsString();
  final result = await Process.run('git', ['rev-parse', 'HEAD:lib/main.dart']);
  final sha = result.exitCode == 0 ? (result.stdout as String).trim() : null;
  final index = buildSemanticIndex(source: source, sourcePath: 'lib/main.dart', gitBlobSha: sha);
  final rendered = renderIndex(index);
  if (write) {
    await outputFile.parent.create(recursive: true);
    await outputFile.writeAsString(rendered);
    stdout.writeln('Wrote docs/generated/jet_vpn_semantic_index.json');
  } else {
    if (!await outputFile.exists() || await outputFile.readAsString() != rendered) {
      stderr.writeln('Semantic AST index is missing or stale. Regenerate with --write.');
      exitCode = 1; return;
    }
    stdout.writeln('Semantic AST index matches lib/main.dart.');
  }
  final s = index['summary'] as Map<String, Object?>;
  stdout.writeln('Declarations: ${s['declaration_count']}; call sites: ${s['call_site_count']}; syntactic edges: ${s['call_edge_count']}.');
  stdout.writeln('Name candidates: ${s['unique_name_candidates']} unique, ${s['ambiguous_name_candidates']} ambiguous, ${s['unresolved_names']} unresolved.');
}
