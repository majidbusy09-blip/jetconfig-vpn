Map<String, Object?> buildCriticalPathReport({
  required Map<String, Object?> resolvedIndex,
  required Map<String, Object?> manifest,
  Map<String, Object?>? projectBinding,
  String? sourceRevision,
}) {
  if ((projectBinding == null) != (sourceRevision == null)) {
    throw ArgumentError('Project binding and source revision must be supplied together.');
  }
  if (projectBinding != null &&
      (projectBinding['base_sha'] != sourceRevision ||
       sourceRevision is! String ||
       !RegExp(r'^(?:[0-9a-f]{40}|[0-9a-f]{64}) = (resolvedIndex['declarations'] as List).cast<Map<String, Object?>>();
  final callSites = (resolvedIndex['call_sites'] as List).cast<Map<String, Object?>>();
  final declarationsById = <String, Map<String, Object?>>{};
  for (final declaration in declarations) {
    final id = declaration['id'];
    if (id is String) declarationsById[id] = declaration;
  }
  final paths = (manifest['paths'] as List).cast<Map<String, Object?>>();
  final reports = <Map<String, Object?>>[];

  for (final path in paths) {
    final entrypoints = (path['entrypoints'] as List).cast<Map<String, Object?>>();
    final resolvedEntrypoints = <Map<String, Object?>>[];
    final unresolvedEntrypoints = <Map<String, Object?>>[];
    final queue = <String>[];
    final reachableIds = <String>{};

    for (final entrypoint in entrypoints) {
      final matches = declarations.where((declaration) =>
          declaration['source_path'] == entrypoint['source_path'] &&
          declaration['kind'] == entrypoint['kind'] &&
          declaration['owner'] == entrypoint['owner'] &&
          declaration['name'] == entrypoint['name']).toList();
      if (matches.length == 1 && matches.single['id'] is String) {
        final declaration = matches.single;
        final id = declaration['id'] as String;
        resolvedEntrypoints.add({
          ...entrypoint,
          'status': 'resolved',
          'element_id': id,
          'line': declaration['line'],
          'display_name': declaration['display_name'],
        });
        if (reachableIds.add(id)) queue.add(id);
      } else {
        unresolvedEntrypoints.add({
          ...entrypoint,
          'status': matches.isEmpty ? 'missing' : 'ambiguous',
          'match_count': matches.length,
        });
      }
    }

    final reachedCalls = <Map<String, Object?>>[];
    final visitedCallKeys = <String>{};
    while (queue.isNotEmpty) {
      final callerId = queue.removeAt(0);
      for (final call in callSites.where((site) => site['caller_element_id'] == callerId)) {
        final key = '${call['source_path']}#${call['offset']}#${call['caller_element_id']}';
        if (!visitedCallKeys.add(key)) continue;
        final targetId = call['target_element_id'];
        final targetIsInternal = call['target_is_in_repository'] == true;
        if (targetIsInternal && targetId is String &&
            declarationsById.containsKey(targetId) && reachableIds.add(targetId)) {
          queue.add(targetId);
        }
        final caller = declarationsById[callerId];
        final target = targetId is String ? declarationsById[targetId] : null;
        reachedCalls.add({
          'source_path': call['source_path'],
          'line': call['line'],
          'invocation_kind': call['invocation_kind'],
          'caller_element_id': callerId,
          'caller': caller?['display_name'],
          'target_name': call['target_display_name'] ?? call['target_name'],
          'target_element_id': targetId,
          'target_source_path': target?['source_path'],
          'target_line': target?['line'],
          'resolution_status': call['resolution_status'],
          'target_is_in_repository': call['target_is_in_repository'],
          'internal_target_not_indexed': targetIsInternal && target == null,
        });
      }
    }

    final reachableDeclarations = reachableIds
        .map((id) => declarationsById[id]!)
        .map((declaration) => {
              'element_id': declaration['id'],
              'source_path': declaration['source_path'],
              'line': declaration['line'],
              'kind': declaration['kind'],
              'owner': declaration['owner'],
              'name': declaration['name'],
              'display_name': declaration['display_name'],
            })
        .toList()
      ..sort((a, b) {
        final byPath = (a['source_path'] as String).compareTo(b['source_path'] as String);
        if (byPath != 0) return byPath;
        return (a['line'] as int).compareTo(b['line'] as int);
      });

    reports.add({
      'id': path['id'],
      'title': path['title'],
      'description': path['description'],
      'related_native_sources': path['related_native_sources'] ?? const [],
      'entrypoints': resolvedEntrypoints,
      'unresolved_entrypoints': unresolvedEntrypoints,
      'reachable_declarations': reachableDeclarations,
      'reachable_calls': reachedCalls,
      'summary': {
        'configured_entrypoints': entrypoints.length,
        'resolved_entrypoints': resolvedEntrypoints.length,
        'missing_or_ambiguous_entrypoints': unresolvedEntrypoints.length,
        'reachable_declarations': reachableDeclarations.length,
        'reachable_calls': reachedCalls.length,
        'internal_calls': reachedCalls.where((call) => call['target_is_in_repository'] == true).length,
        'external_calls': reachedCalls.where((call) => call['target_is_in_repository'] == false).length,
        'unresolved_calls': reachedCalls.where((call) => call['resolution_status'] == 'unresolved').length,
        'internal_targets_not_indexed': reachedCalls.where((call) => call['internal_target_not_indexed'] == true).length,
      },
    });
  }

  return {
    'schema_version': 1,
    if (projectBinding != null) 'project_binding': projectBinding,
    if (sourceRevision != null) 'source_revision': sourceRevision,
    'generator': 'tools/project_memory/semantic/lib/critical_path_report.dart',
    'analysis_mode': 'static_reachability_from_curated_entrypoints',
    'source_file_count': (resolvedIndex['summary'] as Map<String, Object?>)['source_file_count'],
    'source_files': (resolvedIndex['source'] as Map<String, Object?>)['files'],
    'paths': reports,
    'limitations': [
      'This is a static transitive closure over analyzer-resolved invocation edges, not a runtime execution trace or proof that a path is exercised.',
      'Configured entrypoints are curated anchors and must be revalidated when symbols are renamed or moved.',
      'Callback registration, tear-offs, event wiring, state-field dependencies, reflection, dynamic calls, and native execution are not fully represented.',
      'An internal target without a matching indexed declaration is reported, not silently traversed.',
      'Native Java patch files are not Dart analyzer inputs and are not represented in this call graph.',
    ],
  };
}
).hasMatch(sourceRevision))) {
    throw ArgumentError('Project binding must match a full pinned source revision.');
  }
  final declarations = (resolvedIndex['declarations'] as List).cast<Map<String, Object?>>();
  final callSites = (resolvedIndex['call_sites'] as List).cast<Map<String, Object?>>();
  final declarationsById = <String, Map<String, Object?>>{};
  for (final declaration in declarations) {
    final id = declaration['id'];
    if (id is String) declarationsById[id] = declaration;
  }
  final paths = (manifest['paths'] as List).cast<Map<String, Object?>>();
  final reports = <Map<String, Object?>>[];

  for (final path in paths) {
    final entrypoints = (path['entrypoints'] as List).cast<Map<String, Object?>>();
    final resolvedEntrypoints = <Map<String, Object?>>[];
    final unresolvedEntrypoints = <Map<String, Object?>>[];
    final queue = <String>[];
    final reachableIds = <String>{};

    for (final entrypoint in entrypoints) {
      final matches = declarations.where((declaration) =>
          declaration['source_path'] == entrypoint['source_path'] &&
          declaration['kind'] == entrypoint['kind'] &&
          declaration['owner'] == entrypoint['owner'] &&
          declaration['name'] == entrypoint['name']).toList();
      if (matches.length == 1 && matches.single['id'] is String) {
        final declaration = matches.single;
        final id = declaration['id'] as String;
        resolvedEntrypoints.add({
          ...entrypoint,
          'status': 'resolved',
          'element_id': id,
          'line': declaration['line'],
          'display_name': declaration['display_name'],
        });
        if (reachableIds.add(id)) queue.add(id);
      } else {
        unresolvedEntrypoints.add({
          ...entrypoint,
          'status': matches.isEmpty ? 'missing' : 'ambiguous',
          'match_count': matches.length,
        });
      }
    }

    final reachedCalls = <Map<String, Object?>>[];
    final visitedCallKeys = <String>{};
    while (queue.isNotEmpty) {
      final callerId = queue.removeAt(0);
      for (final call in callSites.where((site) => site['caller_element_id'] == callerId)) {
        final key = '${call['source_path']}#${call['offset']}#${call['caller_element_id']}';
        if (!visitedCallKeys.add(key)) continue;
        final targetId = call['target_element_id'];
        final targetIsInternal = call['target_is_in_repository'] == true;
        if (targetIsInternal && targetId is String &&
            declarationsById.containsKey(targetId) && reachableIds.add(targetId)) {
          queue.add(targetId);
        }
        final caller = declarationsById[callerId];
        final target = targetId is String ? declarationsById[targetId] : null;
        reachedCalls.add({
          'source_path': call['source_path'],
          'line': call['line'],
          'invocation_kind': call['invocation_kind'],
          'caller_element_id': callerId,
          'caller': caller?['display_name'],
          'target_name': call['target_display_name'] ?? call['target_name'],
          'target_element_id': targetId,
          'target_source_path': target?['source_path'],
          'target_line': target?['line'],
          'resolution_status': call['resolution_status'],
          'target_is_in_repository': call['target_is_in_repository'],
          'internal_target_not_indexed': targetIsInternal && target == null,
        });
      }
    }

    final reachableDeclarations = reachableIds
        .map((id) => declarationsById[id]!)
        .map((declaration) => {
              'element_id': declaration['id'],
              'source_path': declaration['source_path'],
              'line': declaration['line'],
              'kind': declaration['kind'],
              'owner': declaration['owner'],
              'name': declaration['name'],
              'display_name': declaration['display_name'],
            })
        .toList()
      ..sort((a, b) {
        final byPath = (a['source_path'] as String).compareTo(b['source_path'] as String);
        if (byPath != 0) return byPath;
        return (a['line'] as int).compareTo(b['line'] as int);
      });

    reports.add({
      'id': path['id'],
      'title': path['title'],
      'description': path['description'],
      'related_native_sources': path['related_native_sources'] ?? const [],
      'entrypoints': resolvedEntrypoints,
      'unresolved_entrypoints': unresolvedEntrypoints,
      'reachable_declarations': reachableDeclarations,
      'reachable_calls': reachedCalls,
      'summary': {
        'configured_entrypoints': entrypoints.length,
        'resolved_entrypoints': resolvedEntrypoints.length,
        'missing_or_ambiguous_entrypoints': unresolvedEntrypoints.length,
        'reachable_declarations': reachableDeclarations.length,
        'reachable_calls': reachedCalls.length,
        'internal_calls': reachedCalls.where((call) => call['target_is_in_repository'] == true).length,
        'external_calls': reachedCalls.where((call) => call['target_is_in_repository'] == false).length,
        'unresolved_calls': reachedCalls.where((call) => call['resolution_status'] == 'unresolved').length,
        'internal_targets_not_indexed': reachedCalls.where((call) => call['internal_target_not_indexed'] == true).length,
      },
    });
  }

  return {
    'schema_version': 1,
    'generator': 'tools/project_memory/semantic/lib/critical_path_report.dart',
    'analysis_mode': 'static_reachability_from_curated_entrypoints',
    'source_file_count': (resolvedIndex['summary'] as Map<String, Object?>)['source_file_count'],
    'source_files': (resolvedIndex['source'] as Map<String, Object?>)['files'],
    'paths': reports,
    'limitations': [
      'This is a static transitive closure over analyzer-resolved invocation edges, not a runtime execution trace or proof that a path is exercised.',
      'Configured entrypoints are curated anchors and must be revalidated when symbols are renamed or moved.',
      'Callback registration, tear-offs, event wiring, state-field dependencies, reflection, dynamic calls, and native execution are not fully represented.',
      'An internal target without a matching indexed declaration is reported, not silently traversed.',
      'Native Java patch files are not Dart analyzer inputs and are not represented in this call graph.',
    ],
  };
}
