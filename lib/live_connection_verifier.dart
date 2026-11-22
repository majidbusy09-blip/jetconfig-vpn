/// Result of the asynchronous live tunnel check.
enum LiveConnectionVerificationStatus {
  verified,
  failed,
  coreDisconnected,
  cancelled,
}

class LiveConnectionVerificationResult {
  const LiveConnectionVerificationResult(this.status, {this.delayMs = -1});

  final LiveConnectionVerificationStatus status;
  final int delayMs;
}

/// Owns the asynchronous settle/ping/retry sequence, while the UI owns state
/// changes and recovery decisions. All external effects are injected so the
/// sequence can be exercised without starting the native VPN plugin.
class LiveConnectionVerifier {
  LiveConnectionVerifier({
    Future<void> Function(Duration duration)? wait,
  }) : _wait = wait ?? _defaultWait;

  final Future<void> Function(Duration duration) _wait;

  static Future<void> _defaultWait(Duration duration) =>
      Future<void>.delayed(duration);

  Future<LiveConnectionVerificationResult> verify({
    required bool silent,
    required bool Function() isCurrent,
    required bool Function() forceDisconnected,
    required bool Function() coreConnected,
    required Future<int> Function() getConnectedServerDelay,
    required Duration timeout,
  }) async {
    await _wait(Duration(milliseconds: silent ? 200 : 800));
    if (!isCurrent() || (!silent && forceDisconnected())) {
      return const LiveConnectionVerificationResult(
        LiveConnectionVerificationStatus.cancelled,
      );
    }

    var delay = -1;
    final attempts = silent ? 1 : 2;
    for (var attempt = 0; attempt < attempts; attempt++) {
      if (!isCurrent() || (!silent && forceDisconnected())) {
        return const LiveConnectionVerificationResult(
          LiveConnectionVerificationStatus.cancelled,
        );
      }
      try {
        delay = await getConnectedServerDelay().timeout(timeout);
      } catch (_) {
        delay = -1;
      }
      if (delay >= 0 && delay <= 15000) break;
      if (!silent && attempt + 1 < attempts) {
        await _wait(const Duration(milliseconds: 400));
      }
    }

    if (!isCurrent() || (!silent && forceDisconnected())) {
      return const LiveConnectionVerificationResult(
        LiveConnectionVerificationStatus.cancelled,
      );
    }
    if (!coreConnected()) {
      return const LiveConnectionVerificationResult(
        LiveConnectionVerificationStatus.coreDisconnected,
      );
    }
    if (delay >= 0 && delay <= 15000) {
      return LiveConnectionVerificationResult(
        LiveConnectionVerificationStatus.verified,
        delayMs: delay,
      );
    }
    return LiveConnectionVerificationResult(
      LiveConnectionVerificationStatus.failed,
      delayMs: delay,
    );
  }
}
