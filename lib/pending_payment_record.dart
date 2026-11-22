import 'dart:convert';

/// A locally persisted invoice token bound to the account that created it.
///
/// This record intentionally does not contain account passwords or payment
/// credentials. The backend remains responsible for enforcing ownership.
class PendingPaymentRecord {
  static const String storageKey = 'pending_payment_json';
  static const String legacyStorageKey = 'pending_pay_token';
  static const String pendingStatus = 'pending';

  final String token;
  final String ownerUsername;
  final int createdAtMs;
  final String status;

  const PendingPaymentRecord({
    required this.token,
    required this.ownerUsername,
    required this.createdAtMs,
    this.status = pendingStatus,
  });

  bool belongsTo(String username) =>
      ownerUsername == username.trim() && ownerUsername.isNotEmpty;

  Map<String, Object> toJson() => {
        'token': token,
        'owner_username': ownerUsername,
        'created_at_ms': createdAtMs,
        'status': status,
      };

  String encode() => jsonEncode(toJson());

  static PendingPaymentRecord? decode(String raw) {
    try {
      final value = jsonDecode(raw);
      if (value is! Map) return null;
      final token = value['token'];
      final owner = value['owner_username'];
      final createdAt = value['created_at_ms'];
      final status = value['status'];
      if (token is! String || token.length < 16) return null;
      if (owner is! String || owner.trim().isEmpty) return null;
      if (createdAt is! int || createdAt <= 0) return null;
      if (status != pendingStatus) return null;
      return PendingPaymentRecord(
        token: token,
        ownerUsername: owner.trim(),
        createdAtMs: createdAt,
        status: pendingStatus,
      );
    } catch (_) {
      return null;
    }
  }
}

