import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_v2ray_client/flutter_v2ray.dart';
import 'package:url_launcher/url_launcher.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const JetConfigApp());
}

// مشخصات نسخه (نمایش داخل اپ) — با هر ریلیز دستی بالا ببر
const String appVersion = 'v1.8.1';
const int appVersionCode = 23;
/// کانال بسته‌بندی: با --dart-define=APK_CHANNEL=arm64|universal|arm32 در بیلد ست می‌شود
const String apkChannel = String.fromEnvironment('APK_CHANNEL', defaultValue: 'arm64');
const String appUpdateMetaUrl = 'https://majid6064.ir/app_version.json';
const String appLogoUrl = 'https://majid6064.ir/logo.png';
const String telegramBotUrl = 'https://t.me/JetConfig1bot';
const String telegramChannelUrl = 'https://t.me/jetconfig11';

// لیست پکیج‌های معاف از تونل
const List<String> iranianAndBrowserPackages = [
  'com.android.chrome',
  'org.mozilla.firefox',
  'com.sec.android.app.sbrowser',
  'com.opera.browser',
  'com.opera.mini.native',
  'com.brave.browser',
  'com.microsoft.emmx',
  'app.nobitex',
  'ir.nobitex',
  'ir.nobitex.market',
  'ir.wallex.app',
  'ir.tabdeal.app',
  'com.ramzinex.app',
  'ir.bitpin',
  'com.abantether',
  'com.asanpardakht',
  'com.asanpardakht.app',
  'ir.asanpardakht',
  'com.ap.app',
  'ir.mizan.hamrahcard',
  'com.mizan.hamrahcard',
  'com.bpm.sekeh',
  'com.sadadpsp.eva',
  'ir.sep.qpay',
  'ir.pec.cpay',
  'com.pec.top',
  'ir.parsianbank.top',
  'com.tara.app',
  'com.digikala.digipay',
  'ir.digipay.app',
  'com.snapppay.app',
  'ir.bmi.bam.nativeweb',
  'ir.melli.bam',
  'ir.bmi.bam',
  'ir.bmi.baam',
  'com.bmi.omad',
  'ir.bmi.token',
  'com.sadadpsp.bmi',
  'ir.bankmaskan.mobilebank',
  'ir.bankmaskan.rayanmehr',
  'ir.bankmaskan.hamrah',
  'com.maskan.mobilebank',
  'ir.bankmaskan.android',
  'com.tosan.maskan',
  'ir.bankmellat.mobile',
  'com.mellat.mobile',
  'ir.bankmellat.android',
  'com.tosan.mellat',
  'ir.tejaratbank.tata.mobile.android.tejarat',
  'ir.tejaratbank.mobilebank',
  'com.tejarat.mbank',
  'com.saderat.mb',
  'ir.bsi.mobilebank',
  'ir.bsi.sapp',
  'com.tosan.saderat',
  'ir.mresalat.app',
  'ir.resalat.mbank',
  'ir.rqbank',
  'ir.qmb.hamrah',
  'ir.rqb.app',
  'com.samanpr.blu',
  'ir.blubank',
  'ir.sb24.mobilbank',
  'com.saman.mobile',
  'ir.banksepah.mobilebank',
  'ir.omidbank.app',
  'com.tosan.sepah',
  'ir.bpi.mobilebank',
  'com.pasargad.mobile',
  'ir.parsianbank.mobilebank',
  'ir.agribank.mobile',
  'ir.bankrefah.mobilebank',
  'ir.citybank.mobilebank',
  'ir.day24.mobilebank',
  'ir.sina.mobile',
  'ir.ayandeh.hamrah',
  'ir.postbank.mobile',
  'ir.ttbank.mobilebank',
  'cab.snapp.passenger',
  'com.snapp.passenger',
  'cab.snapp.driver',
  'ir.tapsi.cab',
  'com.digikala.mobile',
  'ir.divar',
  'ir.sheypoor.mobile',
  'org.neshan.maps',
  'ir.balad.navigation',
  'com.torob',
  'ir.basalam.app',
  'ir.alibaba.travel',
  'ir.mtnirancell.myirancell',
  'ir.mci.ecareapp',
  'ir.rightel.ecare',
  'ir.eitaa.messenger',
  'ir.rubika.app',
  'ir.resaneh.rubika',
  'ir.ble.messenger',
  'ir.gov.my',
  'ir.police.my',
];

class ServerModel {
  final String name;
  final String host;
  final int port;
  final String protocol;
  final String config;
  int ping;

  ServerModel({
    required this.name,
    required this.host,
    required this.port,
    required this.protocol,
    required this.config,
    this.ping = -1,
  });

  factory ServerModel.fromJson(Map<String, dynamic> json) {
    return ServerModel(
      name: json['name'] ?? 'سرور هوشمند',
      host: json['host'] ?? '',
      port: int.tryParse('${json['port']}') ?? 443,
      protocol: json['protocol'] ?? 'VPN',
      config: json['config'] ?? '',
    );
  }
}

class JetConfigApp extends StatelessWidget {
  const JetConfigApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'JET VPN',
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0A0E1A),
        fontFamily: 'Tahoma',
      ),
      home: const MainVpnScreen(),
    );
  }
}

class MainVpnScreen extends StatefulWidget {
  const MainVpnScreen({super.key});

  @override
  State<MainVpnScreen> createState() => _MainVpnScreenState();
}

class _MainVpnScreenState extends State<MainVpnScreen> with TickerProviderStateMixin {
  late final V2ray flutterV2ray = V2ray(
    onStatusChanged: (status) {
      if (!mounted) return;
      final prev = (_lastV2rayState ?? '').toUpperCase().trim();
      _lastV2rayState = status.state;

      setState(() {
        v2rayStatus = status;

        if (_statusMeansDisconnected(status.state)) {
          activePing = -1;
          isConnecting = false;
          _connectionVerified = false;
          _uiForceDisconnected = true;
        }

        // CONNECTED خام هسته ≠ اتصال واقعی؛ تا verify نشود سبز نشو
        // isConnecting را اینجا false نکن — بعد از _verifyLiveConnection
      });

      if (_statusMeansConnected(status.state) &&
          prev != 'CONNECTED' &&
          !_uiForceDisconnected) {
        // تأیید واقعی مسیر پروکسی (مثل Happ / v2rayNG)
        _verifyLiveConnection();
      } else if (_statusMeansDisconnected(status.state) && prev == 'CONNECTED') {
        _fetchCurrentIp(force: true);
      }
    },
  );

  V2RayStatus v2rayStatus = V2RayStatus();
  final TextEditingController _userController = TextEditingController();
  final TextEditingController _passController = TextEditingController();

  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  late AnimationController _rotateController;

  bool isLoading = false;
  bool isConnecting = false;
  bool isPingingAll = false;
  bool isRefreshingServers = false;
  bool onlyFilteredApps = true;
  bool _obscurePassword = true;
  // تنظیمات کاربر
  bool autoRefreshOnStart = true; // بروزرسانی اشتراک هنگام باز شدن
  /// جلوگیری از تکرار دیالوگ انقضا در یک نشست
  bool _subAlertShownThisSession = false;
  bool autoPingOnStart = false; // پینگ خودکار هنگام باز شدن
  bool preferLastServer = true; // نگه داشتن آخرین سرور انتخاب‌شده
  int activePing = -1;
  String currentIpAddress = '...';
  String? _lastV2rayState;
  DateTime? _lastIpFetchAt;
  bool _ipFetchInFlight = false;
  /// بعد از stop، تا رسیدن status قطع از هسته، UI را فوری قطع نشان بده
  bool _uiForceDisconnected = false;
  /// فقط بعد از تأیید واقعی (getConnectedServerDelay) دکمه سبز می‌شود
  bool _connectionVerified = false;
  int _verifyGen = 0; // برای باطل کردن verifyهای قدیمی

  Map<String, dynamic>? userData;
  String? savedUser;
  String? savedPass;
  List<ServerModel> serverList = [];
  int selectedServerIndex = 0;

  @override
  void initState() {
    super.initState();
    _initCore();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 0.96, end: 1.07).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _rotateController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat();

    _loadSavedPreferences();
    _fetchCurrentIp();
    // بررسی نامحسوس نسخه (فقط اگر ادمین enabled کرده باشد)
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) _checkAppUpdate(silent: true);
    });
  }

  Future<void> _initCore() async {
    await flutterV2ray.initialize(
      notificationIconResourceType: 'mipmap',
      notificationIconResourceName: 'ic_launcher',
    );
  }

  /// آماده‌سازی کانفیگ برای هسته: JSON خام پاسارگاد یا لینک vless://
  String _prepareConfigForCore(String raw) {
    final s = raw.trim();
    if (s.isEmpty) return s;

    // کانفیگ کامل Xray JSON (ساب جدید پاسارگاد)
    if (s.startsWith('{')) {
      try {
        final decoded = jsonDecode(s);
        if (decoded is Map) {
          // اطمینان از اینکه encryption جدید دست‌نخورده می‌ماند
          return jsonEncode(decoded);
        }
      } catch (_) {
        return s;
      }
      return s;
    }

    // لینک اشتراکی کلاسیک
    if (s.startsWith('vless://') ||
        s.startsWith('vmess://') ||
        s.startsWith('trojan://') ||
        s.startsWith('ss://')) {
      try {
        final parsedUrl = V2ray.parseFromURL(s);
        return parsedUrl.getFullConfiguration();
      } catch (_) {
        return s;
      }
    }

    return s;
  }

  bool _statusMeansConnected(String? state) {
    final st = (state ?? '').toUpperCase().trim();
    return st == 'CONNECTED';
  }

  bool _statusMeansDisconnected(String? state) {
    final st = (state ?? '').toUpperCase().trim();
    if (st.isEmpty) return false;
    return st.contains('DISCONNECT') ||
        st == 'IDLE' ||
        st == 'NONE' ||
        st == 'STOPPED' ||
        st == 'NO_PROCESS';
  }

  /// وضعیت واقعی دکمه/UI — هسته CONNECTED + تأیید تأخیر واقعی
  bool get _isVpnConnected {
    if (_uiForceDisconnected) return false;
    if (!_connectionVerified) return false;
    return _statusMeansConnected(v2rayStatus.state);
  }

  /// بعد از CONNECTED هسته: آیا اینترنت از داخل تونل واقعاً جواب می‌دهد؟
  Future<void> _verifyLiveConnection() async {
    final gen = ++_verifyGen;
    if (mounted) {
      setState(() {
        isConnecting = true; // اسپینر تا تأیید
        _connectionVerified = false;
      });
    }

    // کمی صبر تا تونل پایدار شود
    await Future.delayed(const Duration(milliseconds: 800));
    if (!mounted || gen != _verifyGen || _uiForceDisconnected) return;

    int delay = -1;
    for (var attempt = 0; attempt < 2; attempt++) {
      if (!mounted || gen != _verifyGen || _uiForceDisconnected) return;
      try {
        delay = await flutterV2ray
            .getConnectedServerDelay()
            .timeout(const Duration(milliseconds: 4500));
      } catch (_) {
        delay = -1;
      }
      if (delay >= 0 && delay <= 15000) break;
      await Future.delayed(const Duration(milliseconds: 400));
    }

    if (!mounted || gen != _verifyGen) return;

    if (_uiForceDisconnected || !_statusMeansConnected(v2rayStatus.state)) {
      if (mounted) {
        setState(() {
          isConnecting = false;
          _connectionVerified = false;
        });
      }
      return;
    }

    if (delay >= 0 && delay <= 15000) {
      if (mounted) {
        setState(() {
          _connectionVerified = true;
          isConnecting = false;
          activePing = delay;
        });
      }
      _fetchCurrentIp(force: true);
      return;
    }

    // اتصال واقعی برقرار نشد — مثل Happ: برگرد به قطع
    debugPrint('verifyLiveConnection failed delay=$delay');
    try {
      await flutterV2ray.stopV2Ray();
    } catch (_) {}
    if (!mounted || gen != _verifyGen) return;
    setState(() {
      _uiForceDisconnected = true;
      _connectionVerified = false;
      isConnecting = false;
      activePing = -1;
    });
    _showToast('اتصال برقرار نشد — سرور قطع یا ناموجود است');
    _fetchCurrentIp(force: true);
  }

  /// IP عمومی:
  /// - قبل از اتصال: IP واقعی اینترنت
  /// - بعد از اتصال: IP خروجی سرور
  /// - با عوض شدن سرور: دوباره گرفته می‌شود
  /// - روی تیک‌های مکرر status (ترافیک) گرفته نمی‌شود تا چشمک نزند
  Future<void> _fetchCurrentIp({bool force = false}) async {
    if (_ipFetchInFlight) return;
    final now = DateTime.now();
    // فقط درخواست‌های غیرضروری را محدود کن؛ force همیشه اجرا می‌شود
    if (!force &&
        _lastIpFetchAt != null &&
        now.difference(_lastIpFetchAt!).inSeconds < 8) {
      return;
    }
    _ipFetchInFlight = true;
    try {
      final res = await http
          .get(Uri.parse('https://api.ipify.org'))
          .timeout(const Duration(seconds: 6));
      if (res.statusCode == 200 && mounted) {
        final ip = res.body.trim();
        if (ip.isNotEmpty) {
          if (ip != currentIpAddress) {
            setState(() => currentIpAddress = ip);
          } else if (currentIpAddress == '...' || currentIpAddress == '---') {
            setState(() => currentIpAddress = ip);
          }
          _lastIpFetchAt = DateTime.now();
        }
      }
    } catch (_) {
      if (mounted && (currentIpAddress == '...' || currentIpAddress == '---')) {
        setState(() => currentIpAddress = '---');
      }
    } finally {
      _ipFetchInFlight = false;
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _rotateController.dispose();
    _userController.dispose();
    _passController.dispose();
    super.dispose();
  }

  String _formatBytes(dynamic bytesInput) {
    int bytes = 0;
    if (bytesInput is int) {
      bytes = bytesInput;
    } else if (bytesInput is String) {
      bytes = int.tryParse(bytesInput) ?? 0;
    }
    if (bytes <= 0) return '0 KB';
    const suffixes = ['B', 'KB', 'MB', 'GB', 'TB'];
    int i = (math.log(bytes) / math.log(1024)).floor();
    if (i >= suffixes.length) i = suffixes.length - 1;
    if (i == 0) return '$bytes B';
    double size = bytes / math.pow(1024, i);
    return '${size.toStringAsFixed(size < 10 ? 1 : 0)} ${suffixes[i]}';
  }

  String _getDisplayRemaining() {
    if (userData == null) return 'نامحدود';
    final total = userData!['total_gb'];
    final remaining = userData!['remaining_gb'];
    if (total == null || total == 0 || total == 0.0 || total == '0') {
      return 'نامحدود';
    }
    return '${remaining ?? 0} GB';
  }

  /// دکمه «تمدید در ربات» فقط وقتی حجم/زمان رو به اتمام است
  /// حجم ≤۲۰٪ مانده یا صفر | زمان ≤۳ روز / ساعت / دقیقه / منقضی
  bool _shouldShowRenewInBot() {
    if (userData == null) return false;

    final totalRaw = userData!['total_gb'];
    final remRaw = userData!['remaining_gb'];
    final total = totalRaw is num ? totalRaw.toDouble() : double.tryParse('$totalRaw');
    final rem = remRaw is num ? remRaw.toDouble() : double.tryParse('$remRaw');
    if (total != null && total > 0) {
      final left = rem ?? 0.0;
      if (left <= 0 || (left / total) <= 0.20) return true;
    }

    final expire = userData!['expire_days'];
    if (expire == null) return false;
    final expireStr = '$expire'.trim();
    if (expireStr.isEmpty ||
        expireStr == 'null' ||
        expireStr.contains('نامحدود') ||
        expireStr.contains('VIP') ||
        expireStr.contains('Unlimited')) {
      return false;
    }
    if (expireStr.contains('منقضی') || expireStr.contains('پایان')) return true;
    if (expireStr.contains('ساعت') || expireStr.contains('دقیقه')) return true;
    if (expireStr.contains('روز')) {
      final d = int.tryParse(expireStr.replaceAll(RegExp(r'[^0-9]'), ''));
      if (d != null && d <= 3) return true;
      return false;
    }
    final intVal = int.tryParse(expireStr.replaceAll(RegExp(r'[^0-9\-]'), ''));
    if (intVal != null && intVal >= 0 && intVal <= 3) return true;
    return false;
  }


  bool _isTestUsername([Map? data]) {
    final d = data ?? userData;
    if (d == null) return false;
    final u = '${d['username'] ?? savedUser ?? ''}'.toLowerCase();
    return u.startsWith('test_') || u.contains('_test') || (d['is_test'] == true);
  }

  /// انقضای کامل: حجم صفر (وقتی سقف حجم دارد) یا زمان منقضی
  bool _isSubscriptionExpired([Map? data]) {
    final d = data ?? userData;
    if (d == null) return false;

    final totalRaw = d['total_gb'];
    final remRaw = d['remaining_gb'];
    final total = totalRaw is num ? totalRaw.toDouble() : double.tryParse('$totalRaw');
    final rem = remRaw is num ? remRaw.toDouble() : double.tryParse('$remRaw');
    if (total != null && total > 0) {
      final left = rem ?? 0.0;
      if (left <= 0.001) return true;
    }

    final status = '${d['status'] ?? d['panel_status'] ?? ''}'.toLowerCase();
    if (status.contains('expired') || status.contains('disabled') || status == 'limited') {
      // limited اغلب یعنی اتمام حجم
      if (status == 'limited' || status.contains('expired')) return true;
    }

    final expire = d['expire_days'];
    if (expire == null) return false;
    final expireStr = '$expire'.trim();
    if (expireStr.isEmpty ||
        expireStr == 'null' ||
        expireStr.contains('نامحدود') ||
        expireStr.contains('VIP') ||
        expireStr.contains('Unlimited')) {
      return false;
    }
    if (expireStr.contains('منقضی') || expireStr.contains('پایان')) return true;
    if (expireStr.contains('روز')) {
      final dNum = int.tryParse(expireStr.replaceAll(RegExp(r'[^0-9\-]'), ''));
      if (dNum != null && dNum <= 0) return true;
    }
    final intVal = int.tryParse(expireStr.replaceAll(RegExp(r'[^0-9\-]'), ''));
    if (intVal != null && intVal < 0) return true;
    if (intVal != null && intVal == 0 && !expireStr.contains('ساعت') && !expireStr.contains('دقیقه')) {
      return true;
    }
    return false;
  }

  /// نزدیک اتمام (هنوز منقضی کامل نیست)
  bool _isSubscriptionNearEnd([Map? data]) {
    final d = data ?? userData;
    if (d == null) return false;
    if (_isSubscriptionExpired(d)) return false;

    final totalRaw = d['total_gb'];
    final remRaw = d['remaining_gb'];
    final total = totalRaw is num ? totalRaw.toDouble() : double.tryParse('$totalRaw');
    final rem = remRaw is num ? remRaw.toDouble() : double.tryParse('$remRaw');
    if (total != null && total > 0) {
      final left = rem ?? 0.0;
      if (left > 0 && (left / total) <= 0.20) return true;
    }

    final expire = d['expire_days'];
    if (expire == null) return false;
    final expireStr = '$expire'.trim();
    if (expireStr.isEmpty ||
        expireStr == 'null' ||
        expireStr.contains('نامحدود') ||
        expireStr.contains('VIP') ||
        expireStr.contains('Unlimited')) {
      return false;
    }
    if (expireStr.contains('ساعت') || expireStr.contains('دقیقه')) return true;
    if (expireStr.contains('روز')) {
      final dNum = int.tryParse(expireStr.replaceAll(RegExp(r'[^0-9]'), ''));
      if (dNum != null && dNum > 0 && dNum <= 3) return true;
    }
    final intVal = int.tryParse(expireStr.replaceAll(RegExp(r'[^0-9\-]'), ''));
    if (intVal != null && intVal > 0 && intVal <= 3) return true;
    return false;
  }

  Future<void> _maybeShowSubscriptionAlert(Map data, {bool fromManualRefresh = false}) async {
    if (!mounted) return;
    final expired = _isSubscriptionExpired(data);
    final near = !expired && _isSubscriptionNearEnd(data);
    if (!expired && !near) return;

    final prefs = await SharedPreferences.getInstance();
    final uname = '${data['username'] ?? savedUser ?? ''}';
    final today = DateTime.now().toIso8601String().substring(0, 10);

    if (expired) {
      if (_subAlertShownThisSession && !fromManualRefresh) return;
      final last = prefs.getString('sub_alert_expired_$uname') ?? '';
      // حداکثر یک‌بار در روز مگر رفرش دستی
      if (last == today && !fromManualRefresh) return;
      await prefs.setString('sub_alert_expired_$uname', today);
      _subAlertShownThisSession = true;
      await _showSubscriptionDialog(expired: true, data: data);
      return;
    }

    // هشدار نزدیک اتمام — حداکثر یک‌بار در روز
    final lastW = prefs.getString('sub_alert_warn_$uname') ?? '';
    if (lastW == today && !fromManualRefresh) return;
    await prefs.setString('sub_alert_warn_$uname', today);
    await _showSubscriptionDialog(expired: false, data: data);
  }

  Future<void> _showSubscriptionDialog({required bool expired, required Map data}) async {
    if (!mounted) return;
    final isTest = _isTestUsername(data);
    final rem = _getDisplayRemaining();
    final exp = _getDisplayExpire();

    final title = expired
        ? (isTest ? 'اشتراک تست تمام شد' : 'اشتراک به پایان رسید')
        : 'اخطار: اشتراک رو به اتمام';

    String body;
    if (expired) {
      if (isTest) {
        body =
            'دورهٔ تست تموم شده.\n\nاگر از سرعت و کیفیت راضی بودی، با خرید اشتراک جدید بدون وقفه ادامه بده.';
      } else {
        body =
            'حجم یا اعتبار زمانی این اکانت تمام شده و اتصال پایدار نخواهد بود.\n\n'
            'باقیمانده: $rem\nاعتبار: $exp\n\n'
            'از ربات تمدید کن یا بستهٔ جدید بخر تا دوباره وصل شی.';
      }
    } else {
      body =
          'اشتراک‌ت به‌زودی تموم می‌شه — بهتره قبل از قطع شدن تمدید کنی.\n\n'
          'باقیمانده: $rem\nاعتبار: $exp';
    }

    final primaryLabel = isTest ? 'خرید در ربات' : (expired ? 'تمدید / خرید در ربات' : 'تمدید در ربات');

    await showDialog<void>(
      context: context,
      barrierDismissible: true,
      builder: (ctx) {
        return Directionality(
          textDirection: TextDirection.rtl,
          child: AlertDialog(
            backgroundColor: const Color(0xFF131B2E),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: Row(
              children: [
                Icon(
                  expired ? Icons.warning_amber_rounded : Icons.info_outline_rounded,
                  color: expired ? const Color(0xFFFF5252) : Colors.amberAccent,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                ),
              ],
            ),
            content: Text(
              body,
              style: const TextStyle(color: Colors.white70, height: 1.45, fontSize: 13.5),
            ),
            actionsAlignment: MainAxisAlignment.spaceBetween,
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('بعداً', style: TextStyle(color: Colors.grey)),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: expired ? const Color(0xFFFF5252) : const Color(0xFF00E5FF),
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                onPressed: () {
                  Navigator.of(ctx).pop();
                  _openTelegram(telegramBotUrl);
                },
                child: Text(primaryLabel),
              ),
            ],
          ),
        );
      },
    );
  }


  String _getDisplayTotal() {
    if (userData == null) return 'نامحدود';
    final total = userData!['total_gb'];
    if (total == null || total == 0 || total == 0.0 || total == '0') {
      return 'نامحدود';
    }
    return '$total GB';
  }

  String _getDisplayExpire() {
    if (userData == null) return 'نامحدود';
    final total = userData!['total_gb'];
    final expire = userData!['expire_days'];
    final expireStr = '$expire'.trim();

    if (expire == null ||
        expireStr == 'null' ||
        expireStr.isEmpty ||
        expireStr.contains('نامحدود') ||
        expireStr.contains('VIP') ||
        expireStr.contains('Unlimited') ||
        ((total == 0 || total == null) && (expireStr == '0' || expireStr == '0 روز' || expireStr == 'منقضی شده'))) {
      return 'نامحدود';
    }

    // متن API را خراب نکن: «۲۴ ساعت مانده» نباید بشود «۲۴ روز»
    if (expireStr.contains('ساعت')) {
      final h = int.tryParse(expireStr.replaceAll(RegExp(r'[^0-9]'), ''));
      if (h != null && h > 0) return '$h ساعت';
      return expireStr;
    }
    if (expireStr.contains('دقیقه')) {
      final m = int.tryParse(expireStr.replaceAll(RegExp(r'[^0-9]'), ''));
      if (m != null && m > 0) return '$m دقیقه';
      return expireStr;
    }
    if (expireStr.contains('منقضی') || expireStr.contains('پایان')) {
      return expireStr.contains('حجم') ? 'پایان حجم' : 'منقضی شده';
    }
    if (expireStr.contains('روز')) {
      final d = int.tryParse(expireStr.replaceAll(RegExp(r'[^0-9]'), ''));
      if (d != null) {
        if (d <= 0 && (total == 0 || total == null)) return 'نامحدود';
        if (d <= 0) return 'منقضی شده';
        return '$d روز';
      }
      return expireStr;
    }

    // عدد خالص از API
    final intVal = int.tryParse(expireStr.replaceAll(RegExp(r'[^0-9\-]'), ''));
    if (intVal != null) {
      if (intVal <= 0 && (total == 0 || total == null)) return 'نامحدود';
      if (intVal <= 0) return 'منقضی شده';
      return '$intVal روز';
    }

    return expireStr;
  }

  void _showToast(String msg, {bool isError = true}) {
    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Row(
        textDirection: TextDirection.rtl,
        children: [
          Icon(
            isError ? Icons.error_outline_rounded : Icons.check_circle_outline_rounded,
            color: isError ? const Color(0xFFFF5252) : const Color(0xFF00FFA3),
            size: 20,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              msg,
              textDirection: TextDirection.rtl,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
      behavior: SnackBarBehavior.floating,
      backgroundColor: const Color(0xFF1E293B),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: isError ? const Color(0xFFFF5252).withOpacity(0.6) : const Color(0xFF00E5FF).withOpacity(0.6),
          width: 1.3,
        ),
      ),
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      duration: const Duration(seconds: 3),
    ));
  }

  Future<void> _loadSavedPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    final user = prefs.getString('saved_username');
    final pass = prefs.getString('saved_password') ?? '';
    final savedTunnelMode = prefs.getBool('only_filtered_apps') ?? true;
    final prefAutoRefresh = prefs.getBool('pref_auto_refresh_on_start') ?? true;
    final prefAutoPing = prefs.getBool('pref_auto_ping_on_start') ?? false;
    final prefKeepServer = prefs.getBool('pref_prefer_last_server') ?? true;

    Map<String, dynamic>? cachedUser;
    List<ServerModel> cachedServers = [];
    final cachedUserRaw = prefs.getString('cached_user_json');
    final cachedServersRaw = prefs.getString('cached_servers_json');
    final cachedForUser = prefs.getString('cached_for_username');
    if (user != null &&
        cachedForUser == user &&
        cachedUserRaw != null &&
        cachedUserRaw.isNotEmpty) {
      try {
        final decoded = json.decode(cachedUserRaw);
        if (decoded is Map<String, dynamic> && decoded['ok'] == true) {
          cachedUser = decoded;
        }
      } catch (_) {}
    }
    if (user != null &&
        cachedForUser == user &&
        cachedServersRaw != null &&
        cachedServersRaw.isNotEmpty) {
      try {
        final list = json.decode(cachedServersRaw);
        if (list is List) {
          cachedServers = list
              .whereType<Map>()
              .map((e) => ServerModel.fromJson(Map<String, dynamic>.from(e)))
              .toList();
        }
      } catch (_) {}
    }

    if (mounted) {
      setState(() {
        onlyFilteredApps = savedTunnelMode;
        autoRefreshOnStart = prefAutoRefresh;
        autoPingOnStart = prefAutoPing;
        preferLastServer = prefKeepServer;
        if (user != null && user.isNotEmpty && pass.isNotEmpty) {
          savedUser = user;
          savedPass = pass;
          _userController.text = user;
          _passController.text = pass;
        }
        if (cachedUser != null) {
          userData = cachedUser;
          if (cachedServers.isNotEmpty) {
            serverList = cachedServers;
            selectedServerIndex = _indexOfSavedServerFromPrefs(cachedServers, prefs);
          }
        }
      });
    }

    if (user != null && user.isNotEmpty && pass.isNotEmpty) {
      final hasCache = cachedUser != null && cachedServers.isNotEmpty;
      // بروزرسانی خودکار فقط اگر تنظیم روشن باشد یا کش نداشته باشیم
      if (prefAutoRefresh || !hasCache) {
        _fetchUserData(
          user,
          pass,
          silentBackground: hasCache,
          doPingOnLoad: prefAutoPing,
        );
      } else if (prefAutoPing && hasCache && cachedServers.isNotEmpty) {
        // فقط پینگ بدون فراخوانی API
        _pingAllServers(allowFallbackSwitch: false);
      }
    }
  }

  Future<void> _savePrefBool(String key, bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(key, value);
  }

  /// شناسه پایدار سرور
  /// مهم: UUID برای همه سرورهای یک اکانت یکی است؛ نباید مبنا باشد.
  /// مبنا: host:port (و در صورت نیاز تکهٔ یکتای کانفیگ)
  String _stableServerId(ServerModel s) {
    final host = s.host.trim().toLowerCase();
    if (host.isNotEmpty) {
      return '$host:${s.port}';
    }
    final c = s.config.trim();
    // host را از لینک دربیاور
    final hostInLink = RegExp(
      r'(?:vless|trojan|ss)://[^@]+@([^:/?#]+)',
      caseSensitive: false,
    ).firstMatch(c);
    if (hostInLink != null && (hostInLink.group(1)?.isNotEmpty ?? false)) {
      final h = hostInLink.group(1)!.toLowerCase();
      final portM = RegExp(r'@[^:/?#]+:(\d+)').firstMatch(c);
      final pt = portM != null ? portM.group(1) : '${s.port}';
      return '$h:$pt';
    }
    return s.name.trim().toLowerCase();
  }

  Future<void> _saveSelectedServer(ServerModel s, {int? index}) async {
    final prefs = await SharedPreferences.getInstance();
    final id = _stableServerId(s);
    await prefs.setString('last_server_id', id);
    await prefs.setString('last_server_config', s.config);
    await prefs.setString('last_server_name', s.name);
    await prefs.setString('last_server_host', s.host);
    await prefs.setInt('last_server_port', s.port);
    final i = index ?? serverList.indexOf(s);
    if (i >= 0) await prefs.setInt('last_server_index', i);
  }

  int _indexOfSavedServerFromPrefs(List<ServerModel> list, SharedPreferences prefs) {
    if (list.isEmpty) return 0;
    final id = prefs.getString('last_server_id') ?? '';
    final cfg = prefs.getString('last_server_config') ?? '';
    final name = prefs.getString('last_server_name') ?? '';
    final host = prefs.getString('last_server_host') ?? '';
    final port = prefs.getInt('last_server_port') ?? 0;

    if (id.isNotEmpty) {
      final byId = list.indexWhere((s) => _stableServerId(s) == id);
      if (byId >= 0) return byId;
    }
    if (cfg.isNotEmpty) {
      final byCfg = list.indexWhere((s) => s.config == cfg);
      if (byCfg >= 0) return byCfg;
    }
    if (host.isNotEmpty) {
      final byHostPort = list.indexWhere((s) => s.host == host && (port == 0 || s.port == port));
      if (byHostPort >= 0) return byHostPort;
      final byHost = list.indexWhere((s) => s.host == host);
      if (byHost >= 0) return byHost;
      final byCfgHost = list.indexWhere((s) => s.config.contains(host));
      if (byCfgHost >= 0) return byCfgHost;
    }
    if (name.isNotEmpty) {
      final byName = list.indexWhere((s) => s.name == name);
      if (byName >= 0) return byName;
    }
    // پیدا نشد: ایندکس قبلی را فقط اگر در محدوده باشد نگه دار
    final prev = selectedServerIndex;
    if (prev >= 0 && prev < list.length) return prev;
    return 0;
  }

  Future<void> _saveTunnelMode(bool val) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('only_filtered_apps', val);
    if (mounted) {
      setState(() {
        onlyFilteredApps = val;
      });
    }

    if (_isVpnConnected) {
      _showToast('در حال تغییر حالت شبکه...', isError: false);
      await _toggleConnect();
      await Future.delayed(const Duration(milliseconds: 300));
      await _toggleConnect();
    }
  }

  Future<void> _openTelegram(String url) async {
    // نکته: روی اندروید ۱۱+ اغلب canLaunchUrl برای t.me اشتباهی false می‌دهد
    // و باعث خطای «امکان باز کردن تلگرام وجود ندارد» می‌شود — مستقیم launch می‌کنیم.
    try {
      final uri = Uri.parse(url);
      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (ok) return;
      final ok2 = await launchUrl(uri, mode: LaunchMode.platformDefault);
      if (ok2) return;
      _showToast('امکان باز کردن تلگرام وجود ندارد');
    } catch (_) {
      try {
        final uri = Uri.parse(url);
        await launchUrl(uri, mode: LaunchMode.platformDefault);
      } catch (__) {
        _showToast('خطا در باز کردن لینک');
      }
    }
  }

  Future<void> _fetchUserData(
    String username,
    String password, {
    bool isManualRefresh = false,
    bool silentBackground = false,
    bool doPingOnLoad = false,
  }) async {
    if (mounted) {
      setState(() {
        if (silentBackground) {
          isRefreshingServers = true;
        } else {
          isLoading = true;
        }
      });
    }
    try {
      final uri = Uri.parse(
        'https://majid6064.ir/api.php?username=${Uri.encodeComponent(username)}&password=${Uri.encodeComponent(password)}',
      );
      final res = await http.get(uri).timeout(const Duration(seconds: 12));
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        if (data['ok'] == true) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('saved_username', username);
          await prefs.setString('saved_password', password);

          final List<dynamic> rawServers = data['servers'] ?? [];
          final parsed = rawServers.map((s) => ServerModel.fromJson(s)).toList();
          final restoreIdx = _indexOfSavedServerFromPrefs(parsed, prefs);

          try {
            await prefs.setString('cached_user_json', json.encode(data));
            await prefs.setString('cached_servers_json', json.encode(rawServers));
            await prefs.setString('cached_for_username', username);
          } catch (_) {}

          if (mounted) {
            setState(() {
              userData = data;
              savedUser = username;
              savedPass = password;
              serverList = parsed;
              selectedServerIndex =
                  parsed.isEmpty ? 0 : restoreIdx.clamp(0, parsed.length - 1);
            });
          }

          if (parsed.isNotEmpty) {
            final idx = restoreIdx.clamp(0, parsed.length - 1);
            await _saveSelectedServer(parsed[idx], index: idx);
          }

          if (isManualRefresh) {
            _showToast('سرورها بروزرسانی شدند', isError: false);
          }

          // پیام انقضا / اخطار نزدیک اتمام (ورود یا بروزرسانی)
          try {
            await _maybeShowSubscriptionAlert(
              Map<String, dynamic>.from(data as Map),
              fromManualRefresh: isManualRefresh,
            );
          } catch (_) {}

          if (parsed.isNotEmpty) {
            // پینگ: دستی، یا اگر کاربر در تنظیمات روشن کرده باشد
            final shouldPing = isManualRefresh || doPingOnLoad || (!silentBackground && autoPingOnStart);
            if (shouldPing) {
              await _pingAllServers(
                allowFallbackSwitch: isManualRefresh && !preferLastServer,
              );
            } else if (preferLastServer) {
              await _preferLastServerOrFallback(allowFallbackSwitch: false);
            }
          }
        } else {
          if (!silentBackground) {
            _showToast(data['msg'] ?? 'نام کاربری یا رمز عبور اشتباه است');
          }
        }
      }
    } catch (e) {
      if (!silentBackground) {
        _showToast('خطا در اتصال به سرور');
      }
    } finally {
      if (mounted) {
        setState(() {
          isLoading = false;
          isRefreshingServers = false;
        });
      }
    }
  }

  /// پینگ خام TCP — فقط باز بودن پورت (سریع؛ ممکن است روی CDN سبز دروغین باشد)
  Future<int> _testTcpPing(String host, int port) async {
    if (host.isEmpty) return -2;
    final sw = Stopwatch()..start();
    try {
      final socket = await Socket.connect(
        host,
        port,
        timeout: const Duration(milliseconds: 1400),
      );
      socket.destroy();
      sw.stop();
      return sw.elapsedMilliseconds;
    } catch (_) {
      return -2;
    }
  }

  /// پینگ واقعی از هسته Xray (مثل Happ via-proxy / v2rayNG real delay)
  /// fail یا تایم‌اوت → -2 (ناموجود)
  Future<int> _testRealDelay(ServerModel s) async {
    try {
      final cfg = _prepareConfigForCore(s.config);
      if (cfg.isEmpty) return -2;
      final delay = await flutterV2ray
          .getServerDelay(
            config: cfg,
            url: 'https://www.gstatic.com/generate_204',
          )
          .timeout(const Duration(milliseconds: 4200));
      // هسته گاهی مقدار منفی یا خیلی بزرگ برای fail برمی‌گرداند
      if (delay < 0 || delay > 12000) return -2;
      return delay;
    } catch (_) {
      return -2;
    }
  }

  /// اجرای همزمان با سقف concurrency (سریع‌تر از یکی‌یکی)
  Future<void> _mapConcurrent<T>(
    List<T> items,
    int concurrency,
    Future<void> Function(T item) fn,
  ) async {
    if (items.isEmpty) return;
    final n = concurrency < 1 ? 1 : concurrency;
    var i = 0;
    Future<void> worker() async {
      while (true) {
        final idx = i++;
        if (idx >= items.length) break;
        await fn(items[idx]);
      }
    }

    await Future.wait(List.generate(n.clamp(1, items.length), (_) => worker()));
  }

  void _sortServersByPing({bool keepSelection = true}) {
    if (serverList.isEmpty) return;
    final selected = (keepSelection && selectedServerIndex >= 0 && selectedServerIndex < serverList.length)
        ? serverList[selectedServerIndex]
        : null;

    serverList.sort((a, b) {
      if (a.ping > 0 && b.ping > 0) return a.ping.compareTo(b.ping);
      if (a.ping > 0) return -1;
      if (b.ping > 0) return 1;
      if (a.ping == -1 && b.ping == -2) return -1;
      if (a.ping == -2 && b.ping == -1) return 1;
      return 0;
    });

    if (selected != null) {
      final newIdx = serverList.indexOf(selected);
      if (newIdx != -1) {
        selectedServerIndex = newIdx;
      }
      // اگر پیدا نشد ایندکس را عوض نکن به «بهترین پینگ» — بعداً _preferLastServerOrFallback تصمیم می‌گیرد
    }
  }

  /// روی آخرین سرور بمان.
  /// اگر [allowFallbackSwitch] true باشد و آخرین سرور تایم‌اوت بدهد، کم‌پینگ‌ترین زنده انتخاب می‌شود.
  Future<void> _preferLastServerOrFallback({bool allowFallbackSwitch = true}) async {
    if (serverList.isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    var idx = _indexOfSavedServerFromPrefs(serverList, prefs);
    if (idx < 0 || idx >= serverList.length) {
      idx = selectedServerIndex.clamp(0, serverList.length - 1);
    }

    final preferred = serverList[idx];
    // همیشه ترجیح با آخرین سرور؛ مگر صریحاً مجاز به تعویض باشیم و تایم‌اوت باشد
    if (!allowFallbackSwitch || preferred.ping != -2) {
      if (mounted) {
        setState(() => selectedServerIndex = idx);
      }
      await _saveSelectedServer(preferred, index: idx);
      return;
    }

    int bestIdx = -1;
    int bestPing = 1 << 30;
    for (int i = 0; i < serverList.length; i++) {
      final p = serverList[i].ping;
      if (p > 0 && p < bestPing) {
        bestPing = p;
        bestIdx = i;
      }
    }
    if (bestIdx >= 0) {
      if (mounted) {
        setState(() => selectedServerIndex = bestIdx);
      }
      await _saveSelectedServer(serverList[bestIdx], index: bestIdx);
    } else {
      if (mounted) {
        setState(() => selectedServerIndex = idx);
      }
      await _saveSelectedServer(preferred, index: idx);
    }
  }

  Future<void> _pingAllServers({bool allowFallbackSwitch = true}) async {
    if (serverList.isEmpty || isPingingAll) return;
    setState(() => isPingingAll = true);

    // مرحله ۱: TCP موازی سریع — قطع‌های واضح فوراً قرمز/ناموجود
    await Future.wait(serverList.map((s) async {
      final p = await _testTcpPing(s.host, s.port);
      if (mounted) {
        setState(() => s.ping = p);
      }
    }));

    if (!mounted) return;

    // مرحله ۲: فقط روی سرورهایی که TCP سبز شدند، real-delay از هسته
    // (CDN/فرانت سبز دروغین را فیلتر می‌کند — مثل Happ)
    final candidates = serverList.where((s) => s.ping > 0).toList();
    if (candidates.isNotEmpty) {
      await _mapConcurrent(candidates, 4, (s) async {
        final real = await _testRealDelay(s);
        if (mounted) {
          setState(() => s.ping = real);
        }
      });
    }

    if (mounted) {
      setState(() => _sortServersByPing(keepSelection: true));
      await _preferLastServerOrFallback(allowFallbackSwitch: allowFallbackSwitch);
      if (mounted) setState(() => isPingingAll = false);
    }
  }

  Future<void> _checkActivePing() async {
    try {
      final delay = await flutterV2ray.getConnectedServerDelay();
      if (mounted) {
        setState(() {
          activePing = delay;
        });
      }
    } catch (_) {}
  }

  Future<void> _toggleConnect() async {
    // اگر UI وصل است یا هسته هنوز CONNECTED / در حال اتصال است → قطع کن
    final coreStillUp = _statusMeansConnected(v2rayStatus.state);
    if (_isVpnConnected || coreStillUp || isConnecting) {
      _verifyGen++; // باطل کردن verify در جریان
      if (mounted) {
        setState(() {
          _uiForceDisconnected = true;
          _connectionVerified = false;
          activePing = -1;
          isConnecting = false;
        });
      }
      try {
        await flutterV2ray.stopV2Ray();
      } catch (e) {
        debugPrint('stopV2Ray error: $e');
      }
      try {
        await Future.delayed(const Duration(milliseconds: 200));
        await flutterV2ray.stopV2Ray();
      } catch (_) {}
      if (mounted) {
        setState(() {
          _uiForceDisconnected = true;
          _connectionVerified = false;
          activePing = -1;
          isConnecting = false;
        });
      }
      _fetchCurrentIp(force: true);
      return;
    }

    if (serverList.isEmpty) {
      _showToast('هیچ سروری در لیست وجود ندارد');
      return;
    }

    final target = serverList[selectedServerIndex];
    // هشدار نرم اگر پینگ ناموجود است (اجباری مسدود نمی‌کنیم)
    if (target.ping == -2) {
      _showToast('این سرور ناموجود است — در حال تلاش…');
    }

    setState(() {
      isConnecting = true;
      _uiForceDisconnected = false;
      _connectionVerified = false;
    });

    try {
      final bool permissionGranted = await flutterV2ray.requestPermission();
      if (!permissionGranted) {
        _showToast('مجوز اتصال VPN تایید نشد');
        if (mounted) {
          setState(() {
            isConnecting = false;
            _connectionVerified = false;
          });
        }
        return;
      }

      final configString = _prepareConfigForCore(target.config);

      if (configString.isEmpty) {
        _showToast('کانفیگ سرور خالی است — بروزرسانی کن');
        if (mounted) {
          setState(() {
            isConnecting = false;
            _connectionVerified = false;
          });
        }
        return;
      }

      await flutterV2ray.startV2Ray(
        remark: target.name,
        config: configString,
        blockedApps: onlyFilteredApps ? iranianAndBrowserPackages : null,
        proxyOnly: false,
        notificationDisconnectButtonName: 'قطع اتصال',
      );
      await _saveSelectedServer(target);
      // تأیید واقعی در onStatusChanged → _verifyLiveConnection
      // اگر هسته اصلاً CONNECTED نداد، بعد از چند ثانیه قطع کن
      Future.delayed(const Duration(seconds: 8), () {
        if (!mounted) return;
        if (isConnecting && !_connectionVerified && !_uiForceDisconnected) {
          _verifyGen++;
          flutterV2ray.stopV2Ray().catchError((_) {});
          setState(() {
            isConnecting = false;
            _connectionVerified = false;
            _uiForceDisconnected = true;
          });
          _showToast('زمان اتصال تمام شد — سرور دیگری را امتحان کن');
        }
      });
    } catch (e) {
      debugPrint('startV2Ray error: $e');
      _showToast('خطا در اتصال — هسته یا کانفیگ');
      try {
        await flutterV2ray.stopV2Ray();
      } catch (_) {}
      if (mounted) {
        setState(() {
          isConnecting = false;
          _connectionVerified = false;
          _uiForceDisconnected = true;
        });
      }
    }
  }

  void _openServerPicker() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF131B2E),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Directionality(
              textDirection: TextDirection.rtl,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('سرورهای هوشمند', style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: Colors.white)),
                        Row(
                          children: [
                            TextButton.icon(
                              onPressed: () {
                                _sortServersByPing();
                                setSheetState(() {});
                              },
                              icon: const Icon(Icons.flash_on_rounded, size: 16, color: Colors.amberAccent),
                              label: const Text('مرتب‌سازی پینگ', style: TextStyle(color: Colors.amberAccent, fontSize: 11.5, fontWeight: FontWeight.bold)),
                            ),
                            TextButton.icon(
                              onPressed: isPingingAll
                                  ? null
                                  : () async {
                                      await _pingAllServers();
                                      setSheetState(() {});
                                    },
                              icon: isPingingAll
                                  ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.cyanAccent))
                                  : const Icon(Icons.refresh, size: 16, color: Colors.cyanAccent),
                              label: const Text('تست مجدد', style: TextStyle(color: Colors.cyanAccent, fontSize: 11.5)),
                            ),
                          ],
                        ),
                      ],
                    ),
                    const Divider(color: Colors.white10),
                    Expanded(
                      child: ListView.separated(
                        itemCount: serverList.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (ctx, i) {
                          final s = serverList[i];
                          final isSel = i == selectedServerIndex;

                          Color pingColor = Colors.grey;
                          String pingText = '---';
                          if (s.ping > 0) {
                            if (s.ping <= 800) {
                              pingColor = const Color(0xFF00FFA3);
                            } else {
                              pingColor = Colors.orangeAccent;
                            }
                            pingText = '${s.ping} ms';
                          } else if (s.ping == -2) {
                            // مثل Happ: سرور در دسترس نیست / قطع
                            pingColor = Colors.redAccent;
                            pingText = 'ناموجود';
                          }

                          return InkWell(
                            onTap: () {
                              setState(() {
                                selectedServerIndex = i;
                              });
                              _saveSelectedServer(serverList[i]);
                              Navigator.pop(ctx);
                              if (_isVpnConnected) {
                                _toggleConnect().then((_) => _toggleConnect());
                              }
                            },
                            borderRadius: BorderRadius.circular(16),
                            child: Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: isSel ? const Color(0xFF00E5FF).withOpacity(0.12) : const Color(0xFF0A0E1A),
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(
                                  color: isSel ? const Color(0xFF00E5FF) : Colors.white.withOpacity(0.05),
                                  width: 1.5,
                                ),
                              ),
                              child: Row(
                                children: [
                                  Icon(Icons.dns_rounded, size: 20, color: isSel ? const Color(0xFF00E5FF) : Colors.grey),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(s.name, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: isSel ? const Color(0xFF00E5FF) : Colors.white)),
                                        Text('${s.protocol} | پورت ${s.port}', style: const TextStyle(fontSize: 10.5, color: Colors.grey)),
                                      ],
                                    ),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                    decoration: BoxDecoration(
                                      color: pingColor.withOpacity(0.15),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Text(pingText, style: TextStyle(color: pingColor, fontSize: 11, fontWeight: FontWeight.bold)),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildNeonIpPill() {
    final isConnected = _isVpnConnected;
    final glowColor = isConnected ? const Color(0xFF00FFA3) : const Color(0xFF00E5FF);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFF131B2E),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: glowColor.withOpacity(0.4), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: glowColor.withOpacity(isConnected ? 0.25 : 0.12),
            blurRadius: 10,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isConnected ? Icons.shield_rounded : Icons.location_on_rounded,
            size: 14,
            color: glowColor,
          ),
          const SizedBox(width: 6),
          Text(
            currentIpAddress,
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 11.5,
              letterSpacing: 0.9,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTunnelModeSwitch() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: const Color(0xFF131B2E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Row(
        children: [
          Expanded(
            child: GestureDetector(
              onTap: () => _saveTunnelMode(false),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(vertical: 9),
                decoration: BoxDecoration(
                  color: !onlyFilteredApps ? const Color(0xFF00E5FF).withOpacity(0.2) : Colors.transparent,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: !onlyFilteredApps ? const Color(0xFF00E5FF) : Colors.transparent,
                    width: 1.2,
                  ),
                ),
                child: Center(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.public, size: 15, color: !onlyFilteredApps ? const Color(0xFF00E5FF) : Colors.grey),
                      const SizedBox(width: 5),
                      Text(
                        'تونل کل گوشی',
                        style: TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.bold,
                          color: !onlyFilteredApps ? Colors.white : Colors.grey,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 4),
          Expanded(
            child: GestureDetector(
              onTap: () => _saveTunnelMode(true),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(vertical: 9),
                decoration: BoxDecoration(
                  color: onlyFilteredApps ? const Color(0xFF00FFA3).withOpacity(0.2) : Colors.transparent,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: onlyFilteredApps ? const Color(0xFF00FFA3) : Colors.transparent,
                    width: 1.2,
                  ),
                ),
                child: Center(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.flash_on, size: 15, color: onlyFilteredApps ? const Color(0xFF00FFA3) : Colors.grey),
                      const SizedBox(width: 5),
                      Text(
                        'فقط برنامه‌های فیلترشده',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: onlyFilteredApps ? Colors.white : Colors.grey,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTrafficCard() {
    final isConnected = _isVpnConnected;
    final downloadBytes = isConnected ? v2rayStatus.download : 0;
    final uploadBytes = isConnected ? v2rayStatus.upload : 0;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF131B2E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Row(
              children: [
                const Icon(Icons.arrow_downward_rounded, size: 18, color: Color(0xFF00FFA3)),
                const SizedBox(width: 8),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('دانلود', style: TextStyle(fontSize: 10, color: Colors.grey)),
                    Text(
                      _formatBytes(downloadBytes),
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Container(width: 1, height: 26, color: Colors.white10),
          const SizedBox(width: 14),
          Expanded(
            child: Row(
              children: [
                const Icon(Icons.arrow_upward_rounded, size: 18, color: Color(0xFF00E5FF)),
                const SizedBox(width: 8),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('آپلود', style: TextStyle(fontSize: 10, color: Colors.grey)),
                    Text(
                      _formatBytes(uploadBytes),
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _build3DAnimatedButton() {
    final isConnected = _isVpnConnected;

    return GestureDetector(
      onTap: isConnecting ? null : _toggleConnect,
      child: AnimatedBuilder(
        animation: Listenable.merge([_pulseAnimation, _rotateController]),
        builder: (context, child) {
          final scale = isConnected ? _pulseAnimation.value : 1.0;
          final primaryColor = isConnected ? const Color(0xFF00FFA3) : const Color(0xFF00D2FF);

          return Transform.scale(
            scale: scale,
            child: SizedBox(
              width: 165,
              height: 165,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  if (isConnected || isConnecting)
                    Transform.rotate(
                      angle: _rotateController.value * 2 * math.pi,
                      child: Container(
                        width: 160,
                        height: 160,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: primaryColor.withOpacity(0.35),
                            width: 2,
                          ),
                          gradient: SweepGradient(
                            colors: [
                              Colors.transparent,
                              primaryColor.withOpacity(0.4),
                              Colors.transparent,
                            ],
                          ),
                        ),
                      ),
                    ),
                  Container(
                    width: 135,
                    height: 135,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: primaryColor.withOpacity(isConnected ? 0.5 : 0.25),
                          blurRadius: isConnected ? 35 : 20,
                          spreadRadius: isConnected ? 6 : 1,
                        ),
                      ],
                    ),
                  ),
                  Container(
                    width: 125,
                    height: 125,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          Colors.white.withOpacity(0.2),
                          const Color(0xFF1E293B),
                          Colors.black.withOpacity(0.8),
                        ],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.6),
                          offset: const Offset(0, 8),
                          blurRadius: 12,
                        )
                      ],
                    ),
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: isConnected
                            ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                            : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.white.withOpacity(0.35),
                          offset: const Offset(-2, -2),
                          blurRadius: 5,
                        ),
                        BoxShadow(
                          color: Colors.black.withOpacity(0.5),
                          offset: const Offset(3, 4),
                          blurRadius: 8,
                        ),
                      ],
                    ),
                    child: Center(
                      child: isConnecting
                          ? const SizedBox(
                              width: 34,
                              height: 34,
                              child: CircularProgressIndicator(
                                strokeWidth: 3.2,
                                color: Colors.white,
                              ),
                            )
                          : Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.power_settings_new_rounded,
                                  size: 40,
                                  color: isConnected ? Colors.black87 : Colors.white,
                                  shadows: [
                                    Shadow(
                                      color: Colors.black.withOpacity(0.3),
                                      offset: const Offset(0, 2),
                                      blurRadius: 4,
                                    )
                                  ],
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  isConnected ? 'PROTECTED' : 'READY',
                                  style: TextStyle(
                                    fontSize: 8,
                                    letterSpacing: 1.2,
                                    fontWeight: FontWeight.w900,
                                    color: isConnected ? Colors.black87 : Colors.white70,
                                  ),
                                ),
                              ],
                            ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        appBar: AppBar(
          title: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(
                  appLogoUrl,
                  width: 28,
                  height: 28,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => const Icon(Icons.rocket_launch_rounded, color: Color(0xFF00E5FF)),
                ),
              ),
              const SizedBox(width: 8),
              const Text('JET VPN', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16.5)),
            ],
          ),
          centerTitle: true,
          backgroundColor: Colors.transparent,
          elevation: 0,
          leading: IconButton(
            icon: const Icon(Icons.send_rounded, color: Color(0xFF00E5FF), size: 19),
            tooltip: 'کانال تلگرام',
            onPressed: () => _openTelegram(telegramChannelUrl),
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.settings_rounded, color: Color(0xFF00E5FF), size: 21),
              tooltip: 'تنظیمات',
              onPressed: _openSettings,
            ),
            if (savedUser != null)
              IconButton(
                icon: isRefreshingServers
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF00E5FF)),
                      )
                    : const Icon(Icons.sync_rounded, color: Color(0xFF00E5FF), size: 21),
                tooltip: 'بروزرسانی سرورها',
                onPressed: isRefreshingServers
                    ? null
                    : () => _fetchUserData(savedUser!, savedPass ?? '', isManualRefresh: true),
              ),
            if (savedUser != null)
              IconButton(
                icon: const Icon(Icons.logout_rounded, color: Colors.redAccent, size: 19),
                tooltip: 'خروج از حساب',
                onPressed: () async {
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.remove('saved_username');
                  await prefs.remove('saved_password');
                  await prefs.remove('last_server_id');
                  await prefs.remove('last_server_config');
                  await prefs.remove('last_server_name');
                  await prefs.remove('last_server_host');
                  await prefs.remove('last_server_port');
                  await prefs.remove('cached_user_json');
                  await prefs.remove('cached_servers_json');
                  await prefs.remove('cached_for_username');
                  if (_isVpnConnected) {
                    await flutterV2ray.stopV2Ray();
                  }
                  if (mounted) {
                    setState(() {
                      savedUser = null;
                      savedPass = null;
                      userData = null;
                      serverList.clear();
                      selectedServerIndex = 0;
                    });
                  }
                },
              )
          ],
        ),
        body: isLoading
            ? const Center(child: CircularProgressIndicator(color: Color(0xFF00E5FF)))
            : (savedUser == null || userData == null)
                ? _buildLoginView()
                : _buildDashboardView(),
      ),
    );
  }


  /// بررسی بروزرسانی از سرور (کنترل با app_version.json → enabled)
  Future<void> _checkAppUpdate({bool silent = false}) async {
    try {
      final res = await http
          .get(Uri.parse(appUpdateMetaUrl))
          .timeout(const Duration(seconds: 12));
      if (res.statusCode != 200) {
        if (!silent && mounted) _showToast('بررسی بروزرسانی ناموفق بود');
        return;
      }
      final data = json.decode(utf8.decode(res.bodyBytes));
      if (data is! Map) {
        if (!silent && mounted) _showToast('پاسخ سرور نامعتبر است');
        return;
      }
      final enabled = data['enabled'] == true;
      if (!enabled) {
        if (!silent && mounted) {
          _showToast('نسخه فعلی به‌روز است');
        }
        return;
      }
      final remoteCode = int.tryParse('${data['version_code'] ?? 0}') ?? 0;
      final minCode = int.tryParse('${data['min_version_code'] ?? 0}') ?? 0;
      final force = data['force'] == true || (minCode > 0 && appVersionCode < minCode);
      if (remoteCode <= appVersionCode && !force) {
        if (!silent && mounted) {
          _showToast('نسخه فعلی به‌روز است ($appVersion)');
        }
        return;
      }
      if (!mounted) return;
      final urls = (data['urls'] is Map)
          ? Map<String, dynamic>.from(data['urls'] as Map)
          : <String, dynamic>{};
      String channel = apkChannel;
      // اگر کانال در JSON نبود، فال‌بک منطقی
      String? apkUrl = urls[channel]?.toString();
      if (apkUrl == null || apkUrl.isEmpty) {
        if (channel == 'arm64') {
          apkUrl = urls['universal']?.toString() ?? urls['arm32']?.toString();
        } else if (channel == 'arm32') {
          apkUrl = urls['universal']?.toString() ?? urls['arm64']?.toString();
        } else {
          apkUrl = urls['universal']?.toString() ?? urls['arm64']?.toString();
        }
      }
      if (apkUrl == null || apkUrl.isEmpty) {
        if (!silent && mounted) _showToast('لینک دانلود نسخه جدید موجود نیست');
        return;
      }
      final title = (data['title'] ?? 'نسخه جدید آماده است').toString();
      final changelog = (data['changelog'] ?? '').toString();
      final remoteVer = (data['version'] ?? '').toString();
      final protectNote = (data['play_protect_note'] ??
              'اگر پیام منبع ناشناس یا برنامه مضر آمد، روی «جزئیات بیشتر» و سپس «نصب در هر حال» بزن. این برای نصب خارج از گوگل‌پلی طبیعی است.')
          .toString();
      await _showUpdateDialog(
        title: title,
        remoteVer: remoteVer,
        changelog: changelog,
        protectNote: protectNote,
        apkUrl: apkUrl,
        force: force,
      );
    } catch (e) {
      if (!silent && mounted) {
        _showToast('خطا در بررسی بروزرسانی');
      }
    }
  }

  Future<void> _showUpdateDialog({
    required String title,
    required String remoteVer,
    required String changelog,
    required String protectNote,
    required String apkUrl,
    required bool force,
  }) async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      barrierDismissible: !force,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1A2332),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Text(
            title,
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
          ),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'نسخه فعلی: $appVersion  →  جدید: v$remoteVer',
                  style: const TextStyle(color: Color(0xFF00E5FF), fontSize: 13),
                ),
                const SizedBox(height: 6),
                Text(
                  'بسته این نصب: $apkChannel',
                  style: const TextStyle(color: Colors.white54, fontSize: 11),
                ),
                if (changelog.trim().isNotEmpty) ...[
                  const SizedBox(height: 12),
                  const Text('تغییرات:', style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 13)),
                  const SizedBox(height: 4),
                  Text(changelog, style: const TextStyle(color: Colors.white60, fontSize: 12.5, height: 1.4)),
                ],
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.orange.withOpacity(0.35)),
                  ),
                  child: Text(
                    protectNote,
                    style: const TextStyle(color: Color(0xFFFFCC80), fontSize: 11.5, height: 1.45),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            if (!force)
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('بعداً', style: TextStyle(color: Colors.white54)),
              ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF00C853),
                foregroundColor: Colors.white,
              ),
              onPressed: () async {
                Navigator.pop(ctx);
                await _startApkDownload(apkUrl);
              },
              child: const Text('دانلود و نصب'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _startApkDownload(String apkUrl) async {
    if (!mounted) return;
    _showToast('در حال آماده‌سازی دانلود…');
    try {
      final uri = Uri.parse(apkUrl);
      // دانلود از طریق مرورگر/مدیریت دانلود سیستم — پایدارترین روش روی اندروید
      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!ok && mounted) {
        _showToast('باز کردن لینک دانلود ممکن نشد');
        return;
      }
      if (mounted) {
        await showDialog<void>(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF1A2332),
            title: const Text('دانلود شروع شد', style: TextStyle(color: Colors.white, fontSize: 15)),
            content: const Text(
              'پس از اتمام دانلود، روی اعلان یا فایل APK بزن و نصب را تأیید کن.\n\n'
              'اگر Play Protect هشدار داد:\n'
              '• جزئیات بیشتر\n'
              '• نصب در هر حال\n\n'
              'فایل باید از همان کانال/گیت‌هاب رسمی باشد.',
              style: TextStyle(color: Colors.white70, fontSize: 13, height: 1.45),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('متوجه شدم', style: TextStyle(color: Color(0xFF00E5FF))),
              ),
            ],
          ),
        );
      }
    } catch (_) {
      if (mounted) _showToast('خطا در شروع دانلود');
    }
  }

  void _openSettings() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF131B2E),
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheet) {
            final currentName = serverList.isNotEmpty &&
                    selectedServerIndex >= 0 &&
                    selectedServerIndex < serverList.length
                ? serverList[selectedServerIndex].name
                : 'هنوز انتخاب نشده';

            Widget switchTile({
              required String title,
              required String subtitle,
              required bool value,
              required ValueChanged<bool> onChanged,
            }) {
              return SwitchListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 8),
                activeColor: const Color(0xFF00E5FF),
                title: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13.5)),
                subtitle: Text(subtitle, style: const TextStyle(color: Colors.white54, fontSize: 11)),
                value: value,
                onChanged: (v) {
                  onChanged(v);
                  setSheet(() {});
                },
              );
            }

            return Directionality(
              textDirection: TextDirection.rtl,
              child: Padding(
                padding: EdgeInsets.only(
                  left: 16,
                  right: 16,
                  top: 12,
                  bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
                ),
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Center(
                        child: Container(
                          width: 40,
                          height: 4,
                          margin: const EdgeInsets.only(bottom: 12),
                          decoration: BoxDecoration(
                            color: Colors.white24,
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                      ),
                      const Text(
                        'تنظیمات',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'JET VPN • $appVersion',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.white38, fontSize: 11),
                      ),
                      const Divider(color: Colors.white12, height: 24),
                      switchTile(
                        title: 'بروزرسانی خودکار هنگام باز شدن',
                        subtitle: 'لیست سرورها و وضعیت اشتراک از سرور گرفته شود',
                        value: autoRefreshOnStart,
                        onChanged: (v) async {
                          setState(() => autoRefreshOnStart = v);
                          await _savePrefBool('pref_auto_refresh_on_start', v);
                        },
                      ),
                      switchTile(
                        title: 'پینگ خودکار هنگام باز شدن',
                        subtitle: 'ممکن است باز شدن را کمی کند کند؛ روی انتخاب سرور اثر نگذارد',
                        value: autoPingOnStart,
                        onChanged: (v) async {
                          setState(() => autoPingOnStart = v);
                          await _savePrefBool('pref_auto_ping_on_start', v);
                        },
                      ),
                      switchTile(
                        title: 'نگه داشتن آخرین سرور',
                        subtitle: 'بعد از بروزرسانی به سرور کم‌پینگ‌تر نپرد (توصیه می‌شود)',
                        value: preferLastServer,
                        onChanged: (v) async {
                          setState(() => preferLastServer = v);
                          await _savePrefBool('pref_prefer_last_server', v);
                        },
                      ),
                      switchTile(
                        title: 'حالت تونل: فقط فیلترشده‌ها',
                        subtitle: 'خاموش = تونل کل گوشی (همان سوئیچ داشبورد)',
                        value: onlyFilteredApps,
                        onChanged: (v) async {
                          Navigator.pop(ctx);
                          await _saveTunnelMode(v);
                        },
                      ),
                      ListTile(
                        contentPadding: const EdgeInsets.symmetric(horizontal: 8),
                        leading: const Icon(Icons.system_update_rounded, color: Color(0xFF69F0AE)),
                        title: const Text('بررسی بروزرسانی', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13.5)),
                        subtitle: Text('نسخه $appVersion · بسته $apkChannel', style: const TextStyle(color: Colors.white54, fontSize: 11)),
                        trailing: const Icon(Icons.chevron_left, color: Colors.white38),
                        onTap: () {
                          Navigator.pop(ctx);
                          _checkAppUpdate(silent: false);
                        },
                      ),
                      const Divider(color: Colors.white12, height: 20),
                      ListTile(
                        contentPadding: const EdgeInsets.symmetric(horizontal: 8),
                        leading: const Icon(Icons.dns_rounded, color: Color(0xFF00E5FF)),
                        title: const Text('سرور منتخب', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13.5)),
                        subtitle: Text(currentName, style: const TextStyle(color: Colors.white54, fontSize: 11), maxLines: 2, overflow: TextOverflow.ellipsis),
                        trailing: const Icon(Icons.chevron_left, color: Colors.white38),
                        onTap: () {
                          Navigator.pop(ctx);
                          if (serverList.isNotEmpty) {
                            _openServerPicker();
                          } else {
                            _showToast('ابتدا وارد حساب شوید');
                          }
                        },
                      ),
                      const SizedBox(height: 8),
                      OutlinedButton.icon(
                        onPressed: () {
                          Navigator.pop(ctx);
                          _openTelegram(telegramBotUrl);
                        },
                        icon: const Icon(Icons.support_agent_rounded, color: Color(0xFF00FFA3)),
                        label: const Text('پشتیبانی / ربات تلگرام', style: TextStyle(color: Color(0xFF00FFA3))),
                        style: OutlinedButton.styleFrom(
                          side: const BorderSide(color: Color(0xFF00FFA3), width: 1),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'تغییرات بلافاصله ذخیره می‌شوند.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.white.withOpacity(0.35), fontSize: 10.5),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildLoginView() {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 28.0, vertical: 20.0),
      child: Column(
        children: [
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(28),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF00E5FF).withOpacity(0.35),
                  blurRadius: 28,
                  spreadRadius: 3,
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(28),
              child: Image.network(
                appLogoUrl,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  color: const Color(0xFF131B2E),
                  child: const Icon(Icons.rocket_launch_rounded, size: 50, color: Color(0xFF00E5FF)),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Text('JET VPN', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Colors.white)),
          const SizedBox(height: 4),
          const Text('ورود هوشمند به اشتراک پرسرعت', style: TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 22),
          TextField(
            controller: _userController,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold, color: Colors.white),
            decoration: InputDecoration(
              hintText: 'نام کاربری (مثال: jet_user10)',
              hintStyle: const TextStyle(color: Colors.white30, fontSize: 12.5),
              prefixIcon: const Icon(Icons.fingerprint_rounded, color: Color(0xFF00E5FF)),
              filled: true,
              fillColor: const Color(0xFF131B2E),
              contentPadding: const EdgeInsets.symmetric(vertical: 14),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: Colors.white.withOpacity(0.08))),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: Colors.white.withOpacity(0.08))),
              focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: Color(0xFF00E5FF), width: 1.8)),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _passController,
            obscureText: _obscurePassword,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold, color: Colors.white),
            decoration: InputDecoration(
              hintText: 'رمز عبور اشتراک',
              hintStyle: const TextStyle(color: Colors.white30, fontSize: 12.5),
              prefixIcon: const Icon(Icons.lock_outline_rounded, color: Color(0xFF00E5FF)),
              suffixIcon: IconButton(
                icon: Icon(
                  _obscurePassword ? Icons.visibility_off_rounded : Icons.visibility_rounded,
                  color: Colors.grey,
                  size: 20,
                ),
                onPressed: () {
                  setState(() {
                    _obscurePassword = !_obscurePassword;
                  });
                },
              ),
              filled: true,
              fillColor: const Color(0xFF131B2E),
              contentPadding: const EdgeInsets.symmetric(vertical: 14),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: Colors.white.withOpacity(0.08))),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: Colors.white.withOpacity(0.08))),
              focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: Color(0xFF00E5FF), width: 1.8)),
            ),
          ),
          const SizedBox(height: 18),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00E5FF),
              foregroundColor: Colors.black,
              minimumSize: const Size(double.infinity, 48),
              elevation: 8,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            onPressed: () {
              final user = _userController.text.trim();
              final pass = _passController.text.trim();
              if (user.isNotEmpty && pass.isNotEmpty) {
                _fetchUserData(user, pass);
              } else {
                _showToast('لطفاً نام کاربری و رمز عبور را وارد کنید');
              }
            },
            child: const Text('ورود و دریافت کانفیگ‌ها', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.03),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.white.withOpacity(0.05)),
            ),
            child: const Text(
              'Version $appVersion',
              style: TextStyle(fontSize: 11, color: Colors.white38, letterSpacing: 0.8),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDashboardView() {
    final isConnected = _isVpnConnected;
    final currentServerName = serverList.isNotEmpty ? serverList[selectedServerIndex].name : 'سرور در دسترس';

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xFF131B2E),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white.withOpacity(0.05)),
                ),
                child: Text('کاربر: ${userData!['username']}', style: const TextStyle(color: Color(0xFF00E5FF), fontWeight: FontWeight.bold, fontSize: 11.5)),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  color: const Color(0xFF131B2E),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white.withOpacity(0.05)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.bolt_rounded, size: 15, color: activePing > 0 ? const Color(0xFF00FFA3) : Colors.grey),
                    const SizedBox(width: 4),
                    Text(
                      activePing > 0 ? '$activePing ms' : (isConnected ? 'پینگ...' : 'آفلاین'),
                      style: TextStyle(color: activePing > 0 ? const Color(0xFF00FFA3) : Colors.grey, fontWeight: FontWeight.bold, fontSize: 11),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: const Color(0xFF131B2E),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: Colors.white.withOpacity(0.06)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildCompactBadge('باقیمانده', _getDisplayRemaining(), Icons.pie_chart_rounded, const Color(0xFF00FFA3)),
                Container(width: 1, height: 32, color: Colors.white10),
                _buildCompactBadge('کل ترافیک', _getDisplayTotal(), Icons.data_usage_rounded, const Color(0xFF00E5FF)),
                Container(width: 1, height: 32, color: Colors.white10),
                _buildCompactBadge('مدت اعتبار', _getDisplayExpire(), Icons.timer_outlined, Colors.amberAccent),
              ],
            ),
          ),
          const SizedBox(height: 8),
          _buildTrafficCard(),
          const SizedBox(height: 8),
          _buildTunnelModeSwitch(),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: InkWell(
                  onTap: _openServerPicker,
                  borderRadius: BorderRadius.circular(16),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                    decoration: BoxDecoration(
                      color: const Color(0xFF131B2E),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFF00E5FF).withOpacity(0.2)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.public_rounded, color: Color(0xFF00E5FF), size: 18),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('موقعیت سرور (لمس جهت تغییر)', style: TextStyle(fontSize: 9.5, color: Colors.grey)),
                              Text(currentServerName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.white), overflow: TextOverflow.ellipsis),
                            ],
                          ),
                        ),
                        const Icon(Icons.arrow_forward_ios_rounded, size: 11, color: Colors.grey),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 6),
              InkWell(
                onTap: () {
                  if (savedUser != null && savedPass != null) {
                    _fetchUserData(savedUser!, savedPass!, isManualRefresh: true);
                  }
                },
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF131B2E),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFF00FFA3).withOpacity(0.3)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.sync_rounded, color: Color(0xFF00FFA3), size: 16),
                      SizedBox(width: 4),
                      Text(
                        'بروزرسانی',
                        style: TextStyle(color: Color(0xFF00FFA3), fontSize: 10.5, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          _buildNeonIpPill(),
          const SizedBox(height: 10),
          _build3DAnimatedButton(),
          const SizedBox(height: 8),
          Text(
            isConnected
                ? (onlyFilteredApps ? 'اتصال هوشمند (فقط برنامه‌های فیلترشده)' : 'اتصال کامل (تونل کل گوشی)')
                : 'جهت اتصال لمس کنید',
            style: TextStyle(
              color: isConnected ? const Color(0xFF00FFA3) : Colors.grey,
              fontWeight: FontWeight.bold,
              fontSize: 11.5,
            ),
          ),
          if (_shouldShowRenewInBot()) ...[
            const SizedBox(height: 12),
            InkWell(
              onTap: () => _openTelegram(telegramBotUrl),
              borderRadius: BorderRadius.circular(14),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      const Color(0xFF00E5FF).withOpacity(0.15),
                      const Color(0xFF00FFA3).withOpacity(0.15),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFF00E5FF).withOpacity(0.3)),
                ),
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.diamond_rounded, color: Color(0xFF00FFA3), size: 17),
                    SizedBox(width: 6),
                    Text(
                      'تمدید اشتراک در ربات تلگرام',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                    ),
                    SizedBox(width: 4),
                    Icon(Icons.arrow_forward_rounded, color: Color(0xFF00E5FF), size: 14),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 12),
          Text(
            'JET VPN • $appVersion',
            style: const TextStyle(fontSize: 10.5, color: Colors.white24),
          ),
          const SizedBox(height: 4),
        ],
      ),
    );
  }

  Widget _buildCompactBadge(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 18),
        const SizedBox(height: 2),
        Text(label, style: const TextStyle(color: Colors.grey, fontSize: 9.5)),
        const SizedBox(height: 1),
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 11.5, color: Colors.white)),
      ],
    );
  }
}
