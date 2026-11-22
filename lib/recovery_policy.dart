/// Pure decision rules for smart VPN recovery scheduling.
///
/// Kept independent from Flutter/plugin state so the admission rules can be
/// covered by fast unit tests without starting the VPN engine.
class SmartRecoveryPolicy {
  SmartRecoveryPolicy._();

  static const Set<String> allowedReasons = {
    'cold_restore',
    'health_delay',
    'network_restored',
    'network_back',
    'verify_fail',
    'status_drop',
    'connect_timeout',
  };

  static bool hasActiveConnectionIntent({
    required bool smartMode,
    required bool userWantsConnected,
    required bool userInitiatedStop,
  }) {
    return smartMode && userWantsConnected && !userInitiatedStop;
  }

  static bool isReasonAllowed(String reason) => allowedReasons.contains(reason);

  static int minimumGapSeconds(String reason) =>
      reason == 'network_back' ? 3 : 12;
}
