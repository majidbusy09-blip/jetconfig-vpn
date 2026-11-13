#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
CACHE="${PUB_CACHE:-$HOME/.pub-cache}"
echo "PUB_CACHE=$CACHE"
TARGET=$(find "$CACHE" -path '*flutter_v2ray_client-*/android/src/main/java/dev/amirzr/flutter_v2ray_client/v2ray/core/V2rayCoreManager.java' 2>/dev/null | head -1)
if [ -z "$TARGET" ]; then
  echo "ERROR: flutter_v2ray_client not found. Run flutter pub get first."
  exit 1
fi
cp -f "$ROOT/V2rayCoreManager.java" "$TARGET"
echo "OK Core: $TARGET"
VPN=$(find "$CACHE" -path '*flutter_v2ray_client-*/android/src/main/java/dev/amirzr/flutter_v2ray_client/v2ray/services/V2rayVPNService.java' 2>/dev/null | head -1)
[ -n "$VPN" ] && cp -f "$ROOT/V2rayVPNService.java" "$VPN" && echo "OK VPN: $VPN"
PX=$(find "$CACHE" -path '*flutter_v2ray_client-*/android/src/main/java/dev/amirzr/flutter_v2ray_client/v2ray/services/V2rayProxyOnlyService.java' 2>/dev/null | head -1)
[ -n "$PX" ] && cp -f "$ROOT/V2rayProxyOnlyService.java" "$PX" && echo "OK Proxy: $PX"

ok=1
if ! grep -q 'USER_INITIATED_DISCONNECT' "$TARGET" 2>/dev/null; then
  echo "WARNING: USER_INITIATED_DISCONNECT missing in CoreManager"
  ok=0
fi
if ! grep -q 'USER_INITIATED_DISCONNECT' "$VPN" 2>/dev/null; then
  echo "WARNING: USER_INITIATED_DISCONNECT missing in VPN service"
  ok=0
fi
if ! grep -q 'USER_INITIATED_DISCONNECT' "$PX" 2>/dev/null; then
  echo "WARNING: USER_INITIATED_DISCONNECT missing in ProxyOnly service"
  ok=0
fi
if [ "$ok" = "1" ]; then
  echo "PATCH OK — user-initiated disconnect Extra gated"
else
  echo "PATCH FAILED verification"
  exit 1
fi
