import 'package:flutter_test/flutter_test.dart';
import 'package:jet_vpn/live_connection_policy.dart';

void main() {
  group('LiveConnectionPolicy', () {
    test('does not expose connected from native core status alone', () {
      expect(
        LiveConnectionPolicy.isUiConnected(
          coreConnected: true,
          connectionVerified: false,
          forceDisconnected: false,
        ),
        isFalse,
      );
    });

    test('exposes connected only after successful live verification', () {
      expect(
        LiveConnectionPolicy.isUiConnected(
          coreConnected: true,
          connectionVerified: true,
          forceDisconnected: false,
        ),
        isTrue,
      );
    });

    test('rejects stale verification when native core is disconnected', () {
      expect(
        LiveConnectionPolicy.isUiConnected(
          coreConnected: false,
          connectionVerified: true,
          forceDisconnected: false,
        ),
        isFalse,
      );
    });

    test('honors an explicit UI disconnect override', () {
      expect(
        LiveConnectionPolicy.isUiConnected(
          coreConnected: true,
          connectionVerified: true,
          forceDisconnected: true,
        ),
        isFalse,
      );
    });
  });
}
