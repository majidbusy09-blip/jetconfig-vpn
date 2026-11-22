/// The native core state is not proof that traffic is passing through the tunnel.
class LiveConnectionPolicy {
  LiveConnectionPolicy._();

  static bool isUiConnected({
    required bool coreConnected,
    required bool connectionVerified,
    required bool forceDisconnected,
  }) {
    return coreConnected && connectionVerified && !forceDisconnected;
  }
}
