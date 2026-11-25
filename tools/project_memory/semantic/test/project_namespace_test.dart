import 'dart:io';

import 'package:test/test.dart';
import 'package:jet_vpn_semantic_memory/project_namespace.dart';

Map<String, Object?> manifest() => {
      'schema_version': 1,
      'project_id': 'jet-vpn-android',
      'display_name': 'JET VPN Android',
      'repository': {
        'provider': 'github',
        'repository_id': '1349356614',
        'full_name': 'majidbusy09-blip/jetconfig-vpn',
        'url': 'https://github.com/majidbusy09-blip/jetconfig-vpn',
        'default_branch': 'main',
      },
      'lifecycle': 'registered',
      'source_index': {
        'strategy': 'dart_analyzer',
        'input_paths': ['lib'],
      },
    };

void main() {
  const revision = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';

  test('binds output namespace to project, repository, manifest, and source', () {
    final identity = ProjectArtifactIdentity.fromManifest(
      manifest(),
      sourceRevision: revision,
      actualRepositoryFullName: 'majidbusy09-blip/jetconfig-vpn',
    );
    expect(identity.projectId, 'jet-vpn-android');
    expect(identity.repositoryId, '1349356614');
    expect(identity.manifestSha256, hasLength(64));
    expect(identity.namespaceRoot,
        'docs/generated/projects/jet-vpn-android/1349356614/${identity.manifestSha256}/$revision');
    expect(identity.resolvedIndexPath, endsWith('/indexes/resolved_index.json'));
    expect(identity.criticalPathsPath, endsWith('/indexes/critical_paths.json'));
    expect(identity.binding['base_sha'], revision);
  });

  test('canonical manifest digest is deterministic and changes with manifest', () {
    final first = ProjectArtifactIdentity.fromManifest(
      manifest(),
      sourceRevision: revision,
      actualRepositoryFullName: 'majidbusy09-blip/jetconfig-vpn',
    );
    final reordered = <String, Object?>{
      'lifecycle': 'registered',
      'repository': manifest()['repository']!,
      'display_name': 'JET VPN Android',
      'project_id': 'jet-vpn-android',
      'schema_version': 1,
      'source_index': manifest()['source_index']!,
    };
    final second = ProjectArtifactIdentity.fromManifest(
      reordered,
      sourceRevision: revision,
      actualRepositoryFullName: 'majidbusy09-blip/jetconfig-vpn',
    );
    expect(second.manifestSha256, first.manifestSha256);
    final changed = manifest()..['display_name'] = 'Changed';
    final third = ProjectArtifactIdentity.fromManifest(
      changed,
      sourceRevision: revision,
      actualRepositoryFullName: 'majidbusy09-blip/jetconfig-vpn',
    );
    expect(third.manifestSha256, isNot(first.manifestSha256));
  });

  test('workflow artifact names include full identity tuple', () {
    final identity = ProjectArtifactIdentity.fromManifest(
      manifest(),
      sourceRevision: revision,
      actualRepositoryFullName: 'majidbusy09-blip/jetconfig-vpn',
    );
    final name = identity.artifactName('resolved-index');
    expect(name, startsWith('resolved-index-jet-vpn-android-1349356614-'));
    expect(name, contains(identity.manifestSha256));
    expect(name, endsWith(revision));
  });

  test('parses only canonical GitHub origin identities', () {
    expect(
      ProjectArtifactIdentity.repositoryNameFromRemote(
        'https://github.com/owner/repository.git',
      ),
      'owner/repository',
    );
    expect(
      ProjectArtifactIdentity.repositoryNameFromRemote(
        'git@github.com:owner/repository.git',
      ),
      'owner/repository',
    );
    expect(
      ProjectArtifactIdentity.repositoryNameFromRemote(
        'ssh://git@github.com/owner/repository.git',
      ),
      'owner/repository',
    );
    expect(
      () => ProjectArtifactIdentity.repositoryNameFromRemote('https://evil.example/owner/repo'),
      throwsFormatException,
    );
  });

  test('rejects repository drift, malformed identity, and unpinned source', () {
    expect(
      () => ProjectArtifactIdentity.fromManifest(
        manifest(),
        sourceRevision: revision,
        actualRepositoryFullName: 'owner/other',
      ),
      throwsFormatException,
    );
    final badBranch = manifest();
    (badBranch['repository']! as Map<String, Object?>)['default_branch'] = '../main';
    expect(
      () => ProjectArtifactIdentity.fromManifest(
        badBranch,
        sourceRevision: revision,
        actualRepositoryFullName: 'majidbusy09-blip/jetconfig-vpn',
      ),
      throwsFormatException,
    );
    final badId = manifest()..['project_id'] = '../escape';
    expect(
      () => ProjectArtifactIdentity.fromManifest(
        badId,
        sourceRevision: revision,
        actualRepositoryFullName: 'majidbusy09-blip/jetconfig-vpn',
      ),
      throwsFormatException,
    );
    expect(
      () => ProjectArtifactIdentity.fromManifest(
        manifest(),
        sourceRevision: 'main',
        actualRepositoryFullName: 'majidbusy09-blip/jetconfig-vpn',
      ),
      throwsFormatException,
    );
  });
  test('rejects workflow artifact names beyond the platform limit', () {
    final large = manifest();
    large['project_id'] = 'a' + List.filled(62, 'b').join() + 'c';
    final repository = Map<String, Object?>.from(large['repository']! as Map);
    repository['repository_id'] = List.filled(20, '1').join();
    large['repository'] = repository;
    final identity = ProjectArtifactIdentity.fromManifest(
      large,
      sourceRevision: List.filled(64, 'a').join(),
      actualRepositoryFullName: 'majidbusy09-blip/jetconfig-vpn',
    );
    expect(() => identity.artifactName(List.filled(64, 'p').join()), throwsFormatException);
  });

  test('matches bindings canonically and rejects symlinked output parents', () async {
    final identity = ProjectArtifactIdentity.fromManifest(
      manifest(),
      sourceRevision: revision,
      actualRepositoryFullName: 'majidbusy09-blip/jetconfig-vpn',
    );
    expect(identity.matchesBinding(Map<String, Object?>.from(identity.binding)), isTrue);
    expect(identity.matchesBinding({'project_id': 'other'}), isFalse);

    final root = await Directory.systemTemp.createTemp('project-namespace-');
    final outside = await Directory.systemTemp.createTemp('project-namespace-outside-');
    try {
      await Directory('${root.path}/docs/generated').create(recursive: true);
      await Directory('${root.path}/docs/generated/projects').delete();
      await Link('${root.path}/docs/generated/projects').create(outside.path);
      await expectLater(
        identity.ensureOutputParent(root, identity.resolvedIndexPath, createMissing: true),
        throwsFormatException,
      );
    } finally {
      await root.delete(recursive: true);
      await outside.delete(recursive: true);
    }
  });

}
