package dev.amirzr.flutter_v2ray_client.v2ray.services;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.util.Log;

import androidx.annotation.Nullable;

import dev.amirzr.flutter_v2ray_client.v2ray.core.V2rayCoreManager;
import dev.amirzr.flutter_v2ray_client.v2ray.interfaces.V2rayServicesListener;
import dev.amirzr.flutter_v2ray_client.v2ray.utils.AppConfigs;
import dev.amirzr.flutter_v2ray_client.v2ray.utils.V2rayConfig;

public class V2rayProxyOnlyService extends Service implements V2rayServicesListener {

    @Override
    public void onCreate() {
        super.onCreate();
        V2rayCoreManager.getInstance().setUpListener(this);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        // Handle null intent case - can happen when service is restarted by system
        if (intent == null) {
            Log.w("V2rayProxyOnlyService", "onStartCommand called with null intent, stopping service");
            this.onDestroy();
            return START_NOT_STICKY;
        }

        AppConfigs.V2RAY_SERVICE_COMMANDS startCommand = (AppConfigs.V2RAY_SERVICE_COMMANDS) intent
                .getSerializableExtra("COMMAND");
        
        // Handle null command case
        if (startCommand == null) {
            Log.w("V2rayProxyOnlyService", "No command found in intent, stopping service");
            this.onDestroy();
            return START_NOT_STICKY;
        }

        if (startCommand.equals(AppConfigs.V2RAY_SERVICE_COMMANDS.START_SERVICE)) {
            V2rayConfig v2rayConfig = (V2rayConfig) intent.getSerializableExtra("V2RAY_CONFIG");
            if (v2rayConfig == null) {
                Log.w("V2rayProxyOnlyService", "V2RAY_CONFIG is null, cannot start service");
                this.onDestroy();
                return START_NOT_STICKY;
            }
            if (V2rayCoreManager.getInstance().isV2rayCoreRunning()) {
                V2rayCoreManager.getInstance().stopCore();
            }
            if (V2rayCoreManager.getInstance().startCore(v2rayConfig)) {
                Log.i("V2rayProxyOnlyService", "onStartCommand success => v2ray core started.");
            } else {
                Log.e("V2rayProxyOnlyService", "Failed to start v2ray core");
                this.onDestroy();
                return START_NOT_STICKY;
            }
        } else if (startCommand.equals(AppConfigs.V2RAY_SERVICE_COMMANDS.STOP_SERVICE)) {
            V2rayCoreManager.getInstance().stopCore();
            AppConfigs.V2RAY_CONFIG = null;
                } else if (startCommand.equals(AppConfigs.V2RAY_SERVICE_COMMANDS.MEASURE_DELAY)) {
            new Thread(() -> {
                try {
                    try {
                        V2rayCoreManager.getInstance().updateNotificationText("در حال بررسی پینگ...");
                    } catch (Exception ignored) {}
                    long delay = V2rayCoreManager.getInstance().getConnectedV2rayServerDelay();
                    String packageName = getPackageName();
                    Intent sendB = new Intent(packageName + ".CONNECTED_V2RAY_SERVER_DELAY");
                    sendB.setPackage(packageName);
                    sendB.putExtra("DELAY", String.valueOf(delay));
                    sendBroadcast(sendB);
                    String text = delay < 0 ? "پینگ ناموفق" : ("پینگ سرور فعلی: " + delay + " ms");
                    try {
                        V2rayCoreManager.getInstance().updateNotificationText(text);
                    } catch (Exception ignored) {}
                } catch (Exception e) {
                    Log.w("V2rayProxyOnlyService", "Failed to measure/update delay", e);
                    try {
                        V2rayCoreManager.getInstance().updateNotificationText("پینگ ناموفق");
                    } catch (Exception ignored) {}
                }
            }, "MEASURE_CONNECTED_V2RAY_SERVER_DELAY").start();

        } else {
            Log.w("V2rayProxyOnlyService", "Unknown command received, stopping service");
            this.onDestroy();
            return START_NOT_STICKY;
        }
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public boolean onProtect(int socket) {
        return true;
    }

    @Override
    public Service getService() {
        return this;
    }

    @Override
    public void startService() {
        // ignore
    }

    @Override
    public void stopService() {
        try {
            stopSelf();
        } catch (Exception e) {
            // ignore
        }
    }
}
