import 'package:flutter_test/flutter_test.dart';
import 'package:jet_vpn/recovery_policy.dart';

void main() {
  group('SmartRecoveryPolicy', () {
    test('allows every documented recovery reason, including connect timeout', () {
      for (final reason in SmartRecoveryPolicy.allowedReasons) {
        expect(
          SmartRecoveryPolicy.isReasonAllowed(reason),
          isTrue,
          reason: 'Expected $reason to be admitted',
        );
      }
      expect(SmartRecoveryPolicy.isReasonAllowed('connect_timeout'), isTrue);
    });

    test('rejects unknown and empty recovery reasons', () {
      expect(SmartRecoveryPolicy.isReasonAllowed('manual_disconnect'), isFalse);
      expect(SmartRecoveryPolicy.isReasonAllowed(''), isFalse);
    });

    test('requires smart mode and active user connection intent', () {
      expect(
        SmartRecoveryPolicy.hasActiveConnectionIntent(
          smartMode: true,
          userWantsConnected: true,
          userInitiatedStop: false,
        ),
        isTrue,
      );
      expect(
        SmartRecoveryPolicy.hasActiveConnectionIntent(
          smartMode: false,
          userWantsConnected: true,
          userInitiatedStop: false,
        ),
        isFalse,
      );
      expect(
        SmartRecoveryPolicy.hasActiveConnectionIntent(
          smartMode: true,
          userWantsConnected: false,
          userInitiatedStop: false,
        ),
        isFalse,
      );
      expect(
        SmartRecoveryPolicy.hasActiveConnectionIntent(
          smartMode: true,
          userWantsConnected: true,
          userInitiatedStop: true,
        ),
        isFalse,
      );
    });

    test('preserves the special network-back cooldown', () {
      expect(SmartRecoveryPolicy.minimumGapSeconds('network_back'), 3);
      expect(SmartRecoveryPolicy.minimumGapSeconds('connect_timeout'), 12);
      expect(SmartRecoveryPolicy.minimumGapSeconds('health_delay'), 12);
    });
  });
}
