import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:jet_vpn/main.dart' show MainVpnScreen;
import 'package:jet_vpn/live_connection_verifier.dart';

void main() {
  group('LiveConnectionVerifier', () {
    test('silent resume uses one short live check', () async {
      final waits = <Duration>[];
      var calls = 0;
      final verifier = LiveConnectionVerifier(
        wait: (duration) async => waits.add(duration),
      );

      final result = await verifier.verify(
        silent: true,
        isCurrent: () => true,
        forceDisconnected: () => false,
        coreConnected: () => true,
        getConnectedServerDelay: () async {
          calls++;
          return 84;
        },
        timeout: const Duration(seconds: 1),
      );

      expect(result.status, LiveConnectionVerificationStatus.verified);
      expect(result.delayMs, 84);
      expect(calls, 1);
      expect(waits, [const Duration(milliseconds: 200)]);
    });

    test('silent ping failure remains a failure while core is up', () async {
      final verifier = LiveConnectionVerifier(
        wait: (_) async {},
      );

      final result = await verifier.verify(
        silent: true,
        isCurrent: () => true,
        forceDisconnected: () => false,
        coreConnected: () => true,
        getConnectedServerDelay: () async => -1,
        timeout: const Duration(seconds: 1),
      );

      expect(result.status, LiveConnectionVerificationStatus.failed);
      expect(result.delayMs, -1);
    });

    test('does not accept a ping if the native core disconnects in flight', () async {
      final ping = Completer<int>();
      final pingStarted = Completer<void>();
      var coreConnected = true;
      final verifier = LiveConnectionVerifier(wait: (_) async {});

      final future = verifier.verify(
        silent: true,
        isCurrent: () => true,
        forceDisconnected: () => false,
        coreConnected: () => coreConnected,
        getConnectedServerDelay: () {
          pingStarted.complete();
          return ping.future;
        },
        timeout: const Duration(seconds: 1),
      );
      await pingStarted.future;
      coreConnected = false;
      ping.complete(40);

      final result = await future;
      expect(result.status, LiveConnectionVerificationStatus.coreDisconnected);
    });

    test('application entrypoint compiles with the extracted verifier', () {
      final Type screenType = MainVpnScreen;
      expect(screenType, MainVpnScreen);
    });

    test('discards an obsolete check after its ping completes', () async {
      final ping = Completer<int>();
      var current = true;
      final verifier = LiveConnectionVerifier(wait: (_) async {});

      final pingStarted = Completer<void>();
      final future = verifier.verify(
        silent: true,
        isCurrent: () => current,
        forceDisconnected: () => false,
        coreConnected: () => true,
        getConnectedServerDelay: () {
          pingStarted.complete();
          return ping.future;
        },
        timeout: const Duration(seconds: 1),
      );
      await pingStarted.future;
      current = false;
      ping.complete(55);

      final result = await future;
      expect(result.status, LiveConnectionVerificationStatus.cancelled);
    });

    test('non-silent connection keeps its two-attempt retry timing', () async {
      final waits = <Duration>[];
      var calls = 0;
      final verifier = LiveConnectionVerifier(
        wait: (duration) async => waits.add(duration),
      );

      final result = await verifier.verify(
        silent: false,
        isCurrent: () => true,
        forceDisconnected: () => false,
        coreConnected: () => true,
        getConnectedServerDelay: () async {
          calls++;
          return calls == 1 ? -1 : 120;
        },
        timeout: const Duration(seconds: 1),
      );

      expect(result.status, LiveConnectionVerificationStatus.verified);
      expect(result.delayMs, 120);
      expect(calls, 2);
      expect(waits, [
        const Duration(milliseconds: 800),
        const Duration(milliseconds: 400),
      ]);
    });

    test('profile switch invalidates a pending verification before ping', () async {
      var current = true;
      var pingCalls = 0;
      final verifier = LiveConnectionVerifier(
        wait: (_) async {
          // Model _activateProfile advancing the verification generation
          // while the verifier is waiting for the native core to settle.
          current = false;
        },
      );

      final result = await verifier.verify(
        silent: true,
        isCurrent: () => current,
        forceDisconnected: () => false,
        coreConnected: () => true,
        getConnectedServerDelay: () async {
          pingCalls++;
          return 25;
        },
        timeout: const Duration(seconds: 1),
      );

      expect(result.status, LiveConnectionVerificationStatus.cancelled);
      expect(pingCalls, 0);
    });

    test('explicit disconnect cancels a non-silent check before ping', () async {
      final verifier = LiveConnectionVerifier(wait: (_) async {});
      var pingCalls = 0;

      final result = await verifier.verify(
        silent: false,
        isCurrent: () => true,
        forceDisconnected: () => true,
        coreConnected: () => true,
        getConnectedServerDelay: () async {
          pingCalls++;
          return 20;
        },
        timeout: const Duration(seconds: 1),
      );

      expect(result.status, LiveConnectionVerificationStatus.cancelled);
      expect(pingCalls, 0);
    });
  });
}
