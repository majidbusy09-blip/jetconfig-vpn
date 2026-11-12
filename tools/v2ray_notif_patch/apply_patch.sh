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
if grep -q 'flutter.v2ray_user_stop' "$VPN" 2>/dev/null; then
  echo "PATCH OK — user_stop flag present"
else
  echo "WARNING: user_stop flag missing in VPN service"
  exit 1
fi
