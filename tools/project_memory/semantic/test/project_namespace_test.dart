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
  const revision = 'a' * 40;

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
}
