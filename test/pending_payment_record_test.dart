import 'package:flutter_test/flutter_test.dart';
import 'package:jet_vpn/pending_payment_record.dart';

void main() {
  group('PendingPaymentRecord', () {
    const record = PendingPaymentRecord(
      token: '0123456789abcdef',
      ownerUsername: 'account-a',
      createdAtMs: 1795344000000,
    );

    test('round-trips owner, token, creation time and pending status', () {
      final decoded = PendingPaymentRecord.decode(record.encode());

      expect(decoded, isNotNull);
      expect(decoded!.token, record.token);
      expect(decoded.ownerUsername, record.ownerUsername);
      expect(decoded.createdAtMs, record.createdAtMs);
      expect(decoded.status, PendingPaymentRecord.pendingStatus);
    });

    test('accepts only the exact originating account', () {
      expect(record.belongsTo('account-a'), isTrue);
      expect(record.belongsTo(' account-a '), isTrue);
      expect(record.belongsTo('account-b'), isFalse);
      expect(record.belongsTo(''), isFalse);
    });

    test('rejects malformed JSON and missing owner', () {
      expect(PendingPaymentRecord.decode('{bad json'), isNull);
      expect(
        PendingPaymentRecord.decode(
          '{"token":"0123456789abcdef","created_at_ms":1795344000000,"status":"pending"}',
        ),
        isNull,
      );
    });

    test('rejects short token, invalid timestamp and unknown status', () {
      expect(
        PendingPaymentRecord.decode(
          '{"token":"short","owner_username":"account-a","created_at_ms":1795344000000,"status":"pending"}',
        ),
        isNull,
      );
      expect(
        PendingPaymentRecord.decode(
          '{"token":"0123456789abcdef","owner_username":"account-a","created_at_ms":0,"status":"pending"}',
        ),
        isNull,
      );
      expect(
        PendingPaymentRecord.decode(
          '{"token":"0123456789abcdef","owner_username":"account-a","created_at_ms":1795344000000,"status":"approved"}',
        ),
        isNull,
      );
    });
  });
}
