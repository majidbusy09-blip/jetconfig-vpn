import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_v2ray_client/flutter_v2ray.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:path_provider/path_provider.dart';
import 'package:open_filex/open_filex.dart';
import 'package:installed_apps/installed_apps.dart';
import 'package:installed_apps/app_info.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const JetConfigApp());
}

// مشخصات نسخه (نمایش داخل اپ) — با هر ریلیز دستی بالا ببر
const String appVersion = 'v1.9.18';
const int appVersionCode = 48;
/// کانال بسته‌بندی: با --dart-define=APK_CHANNEL=arm64|universal|arm32 در بیلد ست می‌شود
const String apkChannel = String.fromEnvironment('APK_CHANNEL', defaultValue: 'arm64');
const String appUpdateMetaUrl = 'https://majid6064.ir/app_version.json';
const String tunnelBypassMetaUrl = 'https://majid6064.ir/tunnel_bypass.json';
const int tunnelBypassRefreshHours = 72; // هر ۷۲ ساعت یک‌بار از سرور
const String appLogoUrl = 'https://majid6064.ir/logo.png';
const String telegramBotUrl = 'https://t.me/JetConfig1bot';
const String telegramChannelUrl = 'https://t.me/jetconfig11';


/// تم ظاهری اپ — classic = ظاهر فعلی | jet = برند جت
class JetUiTheme {
  final String id;
  final String label;
  final Color bg;
  final Color card;
  final Color cardBorder;
  final Color accent;
  final Color accentSoft;
  final Color success;
  final Color successDeep;
  final Color connectIdleA;
  final Color connectIdleB;
  final Color text;
  final Color muted;
  final Color sheet;

  const JetUiTheme({
    required this.id,
    required this.label,
    required this.bg,
    required this.card,
    required this.cardBorder,
    required this.accent,
    required this.accentSoft,
    required this.success,
    required this.successDeep,
    required this.connectIdleA,
    required this.connectIdleB,
    required this.text,
    required this.muted,
    required this.sheet,
  });

  static const JetUiTheme classic = JetUiTheme(
    id: 'classic',
    label: 'کلاسیک',
    bg: Color(0xFF0A0E1A),
    card: Color(0xFF131B2E),
    cardBorder: Color(0x14FFFFFF),
    accent: Color(0xFF00E5FF),
    accentSoft: Color(0xFF00D2FF),
    success: Color(0xFF00FFA3),
    successDeep: Color(0xFF008B74),
    connectIdleA: Color(0xFF00D2FF),
    connectIdleB: Color(0xFF0052D4),
    text: Colors.white,
    muted: Colors.white54,
    sheet: Color(0xFF131B2E),
  );

  static const JetUiTheme jet = JetUiTheme(
    id: 'jet',
    label: 'جت',
    bg: Color(0xFF05071A),
    card: Color(0xFF0F1530),
    cardBorder: Color(0xAA8B5CF6),
    accent: Color(0xFFC4B5FD),
    accentSoft: Color(0xFF22D3EE),
    success: Color(0xFF2DD4BF),
    successDeep: Color(0xFF0F766E),
    connectIdleA: Color(0xFFA78BFA),
    connectIdleB: Color(0xFF4F46E5),
    text: Colors.white,
    muted: Color(0xFF94A3B8),
    sheet: Color(0xFF0B1024),
  );

  static JetUiTheme byId(String? id) {
    if (id == jet.id) return jet;
    return classic;
  }
}


// برنامه‌های داخلی — خارج از تونل (حالت بجز برنامه‌های داخلی)
// مرورگرها اینجا نیستند؛ دامنه .ir با routing مستقیم می‌شود
const List<String> _defaultIranianLocalPackages = [
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
  'com.tapsi.passenger',
  'taxi.tapsi.passenger',
  'com.digikala.app',
  'com.farsitel.bazaar',
  'com.cafe.bazaar',
  'ir.mservices.market',
  'com.myket',
  'ir.shaparak.ap',
];

const List<Map<String, String>> selectableVpnApps = [
  {'pkg': 'org.telegram.messenger', 'name': 'تلگرام'},
  {'pkg': 'org.telegram.messenger.web', 'name': 'تلگرام (وب/نسخه دیگر)'},
  {'pkg': 'org.telegram.messenger.beta', 'name': 'تلگرام بتا'},
  {'pkg': 'org.thunderdog.challegram', 'name': 'Telegram X'},
  {'pkg': 'org.telegram.plus', 'name': 'تلگرام پلاس'},
  {'pkg': 'nekox.messenger', 'name': 'NekoX'},
  {'pkg': 'com.instagram.android', 'name': 'اینستاگرام'},
  {'pkg': 'com.instagram.barcelona', 'name': 'Threads'},
  {'pkg': 'com.google.android.youtube', 'name': 'یوتیوب'},
  {'pkg': 'com.twitter.android', 'name': 'توییتر / X'},
  {'pkg': 'com.whatsapp', 'name': 'واتساپ'},
  {'pkg': 'com.whatsapp.w4b', 'name': 'واتساپ بیزنس'},
  {'pkg': 'com.zhiliaoapp.musically', 'name': 'تیک‌تاک'},
  {'pkg': 'com.ss.android.ugc.trill', 'name': 'تیک‌تاک بین‌الملل'},
  {'pkg': 'com.android.chrome', 'name': 'کروم'},
  {'pkg': 'com.chrome.beta', 'name': 'کروم بتا'},
  {'pkg': 'org.mozilla.firefox', 'name': 'فایرفاکس'},
  {'pkg': 'com.brave.browser', 'name': 'Brave'},
  {'pkg': 'com.microsoft.emmx', 'name': 'Edge'},
  {'pkg': 'com.opera.browser', 'name': 'اوپرا'},
  {'pkg': 'com.sec.android.app.sbrowser', 'name': 'مرورگر سامسونگ'},
  {'pkg': 'com.google.android.gm', 'name': 'جیمیل'},
  {'pkg': 'com.discord', 'name': 'دیسکورد'},
  {'pkg': 'com.spotify.music', 'name': 'اسپاتیفای'},
  {'pkg': 'com.reddit.frontpage', 'name': 'ردیت'},
  {'pkg': 'com.linkedin.android', 'name': 'لینکدین'},
  {'pkg': 'com.facebook.katana', 'name': 'فیسبوک'},
  {'pkg': 'com.facebook.orca', 'name': 'مسنجر'},
  {'pkg': 'com.facebook.lite', 'name': 'فیسبوک لایت'},
  {'pkg': 'com.snapchat.android', 'name': 'اسنپ‌چت'},
  {'pkg': 'com.pinterest', 'name': 'پین‌ترست'},
  {'pkg': 'com.google.android.apps.maps', 'name': 'گوگل مپ'},
  {'pkg': 'com.google.android.googlequicksearchbox', 'name': 'گوگل'},
  {'pkg': 'com.openai.chatgpt', 'name': 'ChatGPT'},
  {'pkg': 'com.google.android.apps.youtube.music', 'name': 'یوتیوب موزیک'},
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
  String tunnelMode = 'bypass_local'; // full | bypass_local | selected
  List<String> _iranPackages = List<String>.from(_defaultIranianLocalPackages);
  List<String> _iranDomains = [
    r'regexp:.*\.ir$',
    'domain:ir',
    'domain:digikala.com',
    'domain:shaparak.ir',
    'domain:bmi.ir',
    'domain:bankmellat.ir',
    'domain:cafebazaar.ir',
    'domain:myket.ir',
  ];
  List<String> selectedVpnPackages = [
    'org.telegram.messenger',
    'com.instagram.android',
    'com.google.android.youtube',
    'com.android.chrome',
    'com.twitter.android',
    'com.whatsapp',
  ];
  bool get onlyFilteredApps => tunnelMode != 'full';
  String _selectedAppsFilter = '';
  bool _obscurePassword = true;
  // تنظیمات کاربر
  /// ظاهر: classic | jet
  String uiThemeId = 'classic';
  JetUiTheme get ui => JetUiTheme.byId(uiThemeId);
  bool get isJetTheme => uiThemeId == 'jet';
  bool autoRefreshOnStart = true; // بروزرسانی اشتراک هنگام باز شدن
  /// جلوگیری از تکرار دیالوگ انقضا در یک نشست
  bool _subAlertShownThisSession = false;
  bool autoPingOnStart = false; // پینگ خودکار هنگام باز شدن
  bool preferLastServer = true; // نگه داشتن آخرین سرور انتخاب‌شده
  /// مود اتصال: true = هوشمند (یک دکمه، بدون لیست سرور) / false = دستی
  bool connectionModeSmart = true;
  /// آیا کاربر حداقل یک‌بار مود را انتخاب کرده؟
  bool connectionModeChosen = false;
  bool _modePickerLock = false;
  /// ترجیح در مود هوشمند: true = پایداری / false = کم‌ترین تأخیر
  bool preferStability = true;
  /// کاربر عمداً می‌خواهد وصل بماند (برای بازیابی خودکار)
  bool _userWantsConnected = false;
  bool _isRecovering = false;
  int _recoveryGen = 0;
  DateTime? _lastRecoveryAt;
  int _healthFailCount = 0;
  Timer? _healthTimer;
  /// اینترنت خود دستگاه (وای‌فای/داده) قطع است
  bool _deviceNetworkDown = false;
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
  /// پروفایل‌های محلی: هر کدام username/password/label
  List<Map<String, String>> profiles = [];
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
    Future.delayed(const Duration(seconds: 2), () async {
      if (!mounted) return;
      await _cleanupInstalledUpdateIfNeeded();
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
  /// اطمینان از inbound محلی HTTP روی 10809 تا اپ بتواند IP خروجی را بخواند
  String _ensureLocalHttpInbound(String configJson) {
    try {
      final decoded = jsonDecode(configJson);
      if (decoded is! Map) return configJson;
      final map = Map<String, dynamic>.from(decoded as Map);
      final inbounds = <dynamic>[];
      if (map['inbounds'] is List) {
        inbounds.addAll(List<dynamic>.from(map['inbounds'] as List));
      }
      bool hasHttp10809 = false;
      for (final ib in inbounds) {
        if (ib is! Map) continue;
        final proto = '${ib['protocol'] ?? ''}'.toLowerCase();
        final port = ib['port'];
        if (proto == 'http' && (port == 10809 || port == '10809')) {
          hasHttp10809 = true;
          break;
        }
      }
      if (!hasHttp10809) {
        inbounds.add({
          'tag': 'http-in-jet',
          'port': 10809,
          'listen': '127.0.0.1',
          'protocol': 'http',
          'settings': {
            'timeout': 0,
            'allowTransparent': false,
          },
          'sniffing': {
            'enabled': true,
            'destOverride': ['http', 'tls', 'quic'],
            'routeOnly': false,
          },
        });
      }
      // SOCKS کمکی
      bool hasSocks = false;
      for (final ib in inbounds) {
        if (ib is! Map) continue;
        final proto = '${ib['protocol'] ?? ''}'.toLowerCase();
        if (proto == 'socks') {
          hasSocks = true;
          break;
        }
      }
      if (!hasSocks) {
        inbounds.add({
          'tag': 'socks-in-jet',
          'port': 10808,
          'listen': '127.0.0.1',
          'protocol': 'socks',
          'settings': {
            'auth': 'noauth',
            'udp': true,
          },
          'sniffing': {
            'enabled': true,
            'destOverride': ['http', 'tls', 'quic'],
            'routeOnly': false,
          },
        });
      }
      // sniffing روی inboundهای موجود (کمک به روتینگ دامنه‌ای)
      for (var i = 0; i < inbounds.length; i++) {
        final ib = inbounds[i];
        if (ib is! Map) continue;
        final m = Map<String, dynamic>.from(ib);
        final sniff = m['sniffing'];
        if (sniff is! Map || sniff['enabled'] != true) {
          m['sniffing'] = {
            'enabled': true,
            'destOverride': ['http', 'tls', 'quic'],
            'routeOnly': false,
          };
          inbounds[i] = m;
        }
      }
      map['inbounds'] = inbounds;
      return jsonEncode(map);
    } catch (_) {
      return configJson;
    }
  }

  String _prepareConfigForCore(String raw) {
    final s = raw.trim();
    if (s.isEmpty) return s;

    if (s.startsWith('{')) {
      try {
        final decoded = jsonDecode(s);
        if (decoded is Map) {
          final map = Map<String, dynamic>.from(decoded);
          _injectIranDomainDirectRules(map);
          return _ensureLocalHttpInbound(jsonEncode(map));
        }
      } catch (_) {
        return s;
      }
      return s;
    }

    if (s.startsWith('vless://') ||
        s.startsWith('vmess://') ||
        s.startsWith('trojan://') ||
        s.startsWith('ss://')) {
      try {
        final parsedUrl = V2ray.parseFromURL(s);
        final full = parsedUrl.getFullConfiguration();
        try {
          final decoded = jsonDecode(full);
          if (decoded is Map) {
            final map = Map<String, dynamic>.from(decoded);
            _injectIranDomainDirectRules(map);
            return _ensureLocalHttpInbound(jsonEncode(map));
          }
        } catch (_) {}
        return _ensureLocalHttpInbound(full);
      } catch (_) {
        return s;
      }
    }

    return s;
  }

  void _injectIranDomainDirectRules(Map<String, dynamic> cfg) {
    // همیشه شبکهٔ محلی (LAN) مستقیم — لازم برای Smart View / Miracast / Cast محلی
    // دامنه‌های .ir فقط وقتی تونل «کل گوشی» نیست
    // + پایداری استریم (یوتیوب و …): بلاک QUIC/UDP:443 تا روی TCP بیفتد
    String directTag = 'direct';
    String blockTag = 'block';
    final outs = cfg['outbounds'];
    if (outs is List) {
      var foundDirect = false;
      var foundBlock = false;
      for (final o in outs) {
        if (o is! Map) continue;
        final tag = '${o['tag'] ?? ''}'.toLowerCase();
        final proto = '${o['protocol'] ?? ''}'.toLowerCase();
        if (tag == 'direct' || tag == 'freedom' || tag == 'direct-out') {
          directTag = '${o['tag']}';
          foundDirect = true;
        } else if (!foundDirect && proto == 'freedom') {
          directTag = '${o['tag'] ?? 'direct'}';
          foundDirect = true;
        }
        if (tag == 'block' || tag == 'blocked' || tag == 'blackhole') {
          blockTag = '${o['tag']}';
          foundBlock = true;
        } else if (!foundBlock && proto == 'blackhole') {
          blockTag = '${o['tag'] ?? 'block'}';
          foundBlock = true;
        }
      }
      if (!foundDirect) {
        outs.add({'protocol': 'freedom', 'tag': 'direct'});
        directTag = 'direct';
      }
      if (!foundBlock) {
        outs.add({'protocol': 'blackhole', 'tag': 'block'});
        blockTag = 'block';
      }
    } else {
      cfg['outbounds'] = [
        {'protocol': 'freedom', 'tag': 'direct'},
        {'protocol': 'blackhole', 'tag': 'block'},
      ];
      directTag = 'direct';
      blockTag = 'block';
    }

    // DNS پایدار + ترجیح IPv4 (کاهش گیر یوتیوب روی IPv6 نیمه‌کاره)
    if (cfg['dns'] is! Map) {
      cfg['dns'] = {
        'servers': ['1.1.1.1', '8.8.8.8'],
        'queryStrategy': 'UseIPv4',
      };
    } else {
      final dns = Map<String, dynamic>.from(cfg['dns'] as Map);
      if (dns['servers'] is! List || (dns['servers'] as List).isEmpty) {
        dns['servers'] = ['1.1.1.1', '8.8.8.8'];
      }
      dns['queryStrategy'] = dns['queryStrategy'] ?? 'UseIPv4';
      cfg['dns'] = dns;
    }

    final privateRule = {
      'type': 'field',
      'ip': [
        'geoip:private',
        '10.0.0.0/8',
        '127.0.0.0/8',
        '172.16.0.0/12',
        '192.168.0.0/16',
        '169.254.0.0/16',
        '224.0.0.0/4',
      ],
      'outboundTag': directTag,
    };

    final iranRule = {
      'type': 'field',
      'domain': List<String>.from(_iranDomains),
      'outboundTag': directTag,
    };

    // QUIC = UDP/443 — بلاک تا کلاینت‌ها (یوتیوب و …) به TCP برگردند
    final quicBlockRule = {
      'type': 'field',
      'network': 'udp',
      'port': '443',
      'outboundTag': blockTag,
    };

    Map<String, dynamic> routing = cfg['routing'] is Map
        ? Map<String, dynamic>.from(cfg['routing'] as Map)
        : {'domainStrategy': 'IPIfNonMatch', 'rules': <dynamic>[]};
    final rules = <dynamic>[];
    if (routing['rules'] is List) {
      rules.addAll(List<dynamic>.from(routing['rules'] as List));
    }

    final hasPrivate = rules.any((r) =>
        r is Map &&
        r['ip'] is List &&
        (r['ip'] as List).any((d) => '$d'.contains('private') || '$d'.contains('192.168')));
    if (!hasPrivate) {
      rules.insert(0, privateRule);
    }

    if (tunnelMode != 'full') {
      final hasIran = rules.any((r) =>
          r is Map &&
          r['domain'] is List &&
          (r['domain'] as List).any((d) => '$d'.contains('.ir')));
      if (!hasIran) {
        rules.insert(0, iranRule);
      }
    }

    final hasQuicBlock = rules.any((r) =>
        r is Map &&
        '${r['network'] ?? ''}'.toLowerCase() == 'udp' &&
        '${r['port'] ?? ''}'.contains('443') &&
        ('${r['outboundTag'] ?? ''}'.toLowerCase().contains('block') ||
            '${r['outboundTag'] ?? ''}'.toLowerCase().contains('blackhole')));
    if (!hasQuicBlock) {
      // بعد از private/iran — قبل از قوانین عمومی پنل
      var insertAt = 0;
      if (hasPrivate) insertAt++;
      if (tunnelMode != 'full') {
        final hasIranNow = rules.any((r) =>
            r is Map &&
            r['domain'] is List &&
            (r['domain'] as List).any((d) => '$d'.contains('.ir')));
        if (hasIranNow) insertAt++;
      }
      if (insertAt > rules.length) insertAt = rules.length;
      rules.insert(insertAt, quicBlockRule);
    }

    routing['rules'] = rules;
    routing['domainStrategy'] = routing['domainStrategy'] ?? 'IPIfNonMatch';
    cfg['routing'] = routing;
  }

  static const List<String> _alwaysDirectPackages = [
    'com.jetconfig.vpn',
    'com.android.systemui',
    'com.android.phone',
    'com.android.server.telecom',
    'com.android.settings',
  ];

  /// Smart View / Screen Mirroring / Cast محلی — همیشه خارج از تونل
  static const List<String> _castMirrorPackages = [
    'com.samsung.android.smartmirroring',
    'com.samsung.android.screenmirroring',
    'com.samsung.android.allshare.service.mediashare',
    'com.samsung.android.allshare.service.fileshare',
    'com.samsung.android.mdx',
    'com.samsung.android.mdx.kit',
    'com.samsung.android.mdx.quickboard',
    'com.samsung.android.tvplus',
    'com.samsung.android.video',
    'com.samsung.android.homemenu',
    'com.samsung.android.app.tvout',
    'com.sec.android.app.wfctrl',
    'com.samsung.android.oneconnect',
    'com.samsung.android.networkstack',
    // gms/gsf نباید از تونل خارج شوند — یوتیوب و سرویس‌های گوگل به آن‌ها وابسته‌اند
    // (خروجشان باعث پخش‌نشدن اپ یوتیوب می‌شد؛ مرورگر مشکلی نداشت)
    'com.google.android.apps.chromecast.app',
    'com.google.android.apps.nbu.files',
    'com.android.companiondevicemanager',
    'com.android.networkstack',
    'com.android.networkstack.tethering',
    'com.samsung.android.mobileservice',
    'com.samsung.android.cmfa.framework',
    'com.samsung.android.scs',
    'com.samsung.android.wifi.p2paware',
    'com.sec.android.daemonapp',
    'com.samsung.android.sm.devicesecurity',
    'com.samsung.android.themecenter',
  ];


  /// خانواده‌های پکیج — با تیک یکی، مرتبط‌های نصب‌شده نامحسوس اضافه می‌شوند
  /// (نسخه‌های رسمی/لایت/بتا + WebView/سرویس‌های لازم برای همان خانواده)
  static const Map<String, List<String>> _relatedVpnPackages = {
    // —— تلگرام ——
    'org.telegram.messenger': [
      'org.telegram.messenger',
      'org.telegram.messenger.web',
      'org.telegram.messenger.beta',
      'org.thunderdog.challegram',
      'org.telegram.plus',
      'nekox.messenger',
      'com.android.webview',
      'com.google.android.webview',
    ],
    'org.telegram.messenger.web': [
      'org.telegram.messenger',
      'org.telegram.messenger.web',
      'org.telegram.messenger.beta',
      'com.android.chrome',
      'com.chrome.beta',
      'com.google.android.apps.chrome',
      'com.sec.android.app.sbrowser',
      'org.mozilla.firefox',
      'com.android.webview',
      'com.google.android.webview',
    ],
    'org.telegram.messenger.beta': [
      'org.telegram.messenger',
      'org.telegram.messenger.web',
      'org.telegram.messenger.beta',
    ],
    'org.thunderdog.challegram': [
      'org.thunderdog.challegram',
      'org.telegram.messenger',
      'org.telegram.messenger.web',
    ],
    // —— اینستا / تردز ——
    'com.instagram.android': [
      'com.instagram.android',
      'com.instagram.barcelona',
      'com.instagram.android.preload',
      'com.instagram.lite',
      'com.android.webview',
      'com.google.android.webview',
    ],
    'com.instagram.barcelona': [
      'com.instagram.android',
      'com.instagram.barcelona',
    ],
    'com.instagram.lite': [
      'com.instagram.android',
      'com.instagram.lite',
    ],
    // —— فیسبوک / مسنجر ——
    'com.facebook.katana': [
      'com.facebook.katana',
      'com.facebook.lite',
      'com.facebook.orca',
      'com.facebook.mlite',
      'com.facebook.system',
      'com.facebook.appmanager',
      'com.facebook.services',
      'com.android.webview',
      'com.google.android.webview',
    ],
    'com.facebook.orca': [
      'com.facebook.orca',
      'com.facebook.katana',
      'com.facebook.mlite',
      'com.facebook.lite',
    ],
    'com.facebook.lite': [
      'com.facebook.lite',
      'com.facebook.katana',
      'com.facebook.orca',
    ],
    // —— واتساپ ——
    'com.whatsapp': [
      'com.whatsapp',
      'com.whatsapp.w4b',
    ],
    'com.whatsapp.w4b': [
      'com.whatsapp',
      'com.whatsapp.w4b',
    ],
    // —— یوتیوب ——
    'com.google.android.youtube': [
      'com.google.android.youtube',
      'com.google.android.apps.youtube.music',
      'com.google.android.youtube.tv',
      'com.vanced.android.youtube',
      'app.revanced.android.youtube',
      'com.android.vending',
    ],
    'com.google.android.apps.youtube.music': [
      'com.google.android.apps.youtube.music',
      'com.google.android.youtube',
    ],
    // —— توییتر / X ——
    'com.twitter.android': [
      'com.twitter.android',
      'com.twitter.android.lite',
      'com.android.webview',
      'com.google.android.webview',
    ],
    // —— تیک‌تاک ——
    'com.zhiliaoapp.musically': [
      'com.zhiliaoapp.musically',
      'com.ss.android.ugc.trill',
      'com.ss.android.ugc.aweme',
      'com.android.webview',
      'com.google.android.webview',
    ],
    'com.ss.android.ugc.trill': [
      'com.ss.android.ugc.trill',
      'com.zhiliaoapp.musically',
    ],
    // —— دیسکورد ——
    'com.discord': [
      'com.discord',
      'com.android.webview',
      'com.google.android.webview',
    ],
    // —— ردیت ——
    'com.reddit.frontpage': [
      'com.reddit.frontpage',
      'com.reddit.frontpage.lite',
      'com.android.webview',
      'com.google.android.webview',
    ],
    // —— اسپاتیفای ——
    'com.spotify.music': [
      'com.spotify.music',
      'com.spotify.lite',
    ],
    // —— لینکدین ——
    'com.linkedin.android': [
      'com.linkedin.android',
      'com.android.webview',
      'com.google.android.webview',
    ],
    // —— اسنپ‌چت ——
    'com.snapchat.android': [
      'com.snapchat.android',
      'com.android.webview',
      'com.google.android.webview',
    ],
    // —— پین‌ترست ——
    'com.pinterest': [
      'com.pinterest',
      'com.android.webview',
      'com.google.android.webview',
    ],
    // —— ChatGPT / OpenAI ——
    'com.openai.chatgpt': [
      'com.openai.chatgpt',
      'com.android.webview',
      'com.google.android.webview',
      'com.android.chrome',
    ],
    // —— گوگل (جستجو / جیمیل / مپ) ——
    'com.google.android.googlequicksearchbox': [
      'com.google.android.googlequicksearchbox',
      'com.google.android.gm',
      'com.google.android.apps.maps',
    ],
    'com.google.android.gm': [
      'com.google.android.gm',
      'com.google.android.gms',
    ],
    'com.google.android.apps.maps': [
      'com.google.android.apps.maps',
    ],
    // —— مرورگرها + WebView ——
    'com.android.chrome': [
      'com.android.chrome',
      'com.chrome.beta',
      'com.chrome.dev',
      'com.chrome.canary',
      'com.google.android.apps.chrome',
      'com.android.webview',
      'com.google.android.webview',
    ],
    'com.chrome.beta': [
      'com.android.chrome',
      'com.chrome.beta',
      'com.android.webview',
      'com.google.android.webview',
    ],
    'com.google.android.apps.chrome': [
      'com.android.chrome',
      'com.google.android.apps.chrome',
      'com.android.webview',
      'com.google.android.webview',
    ],
    'org.mozilla.firefox': [
      'org.mozilla.firefox',
      'org.mozilla.firefox_beta',
      'org.mozilla.focus',
      'org.mozilla.fenix',
    ],
    'com.sec.android.app.sbrowser': [
      'com.sec.android.app.sbrowser',
      'com.sec.android.app.sbrowser.beta',
      'com.android.webview',
      'com.google.android.webview',
    ],
    'com.opera.browser': [
      'com.opera.browser',
      'com.opera.mini.native',
      'com.opera.mini.android',
    ],
    'com.brave.browser': [
      'com.brave.browser',
      'com.brave.browser_beta',
    ],
    'com.microsoft.emmx': [
      'com.microsoft.emmx',
    ],
    'com.android.webview': [
      'com.android.webview',
      'com.google.android.webview',
    ],
    'com.google.android.webview': [
      'com.android.webview',
      'com.google.android.webview',
    ],
    // —— سیگنال / تلگرام‌مانند ——
    'org.thoughtcrime.securesms': [
      'org.thoughtcrime.securesms',
    ],
    // —— اسکایپ ——
    'com.skype.raider': [
      'com.skype.raider',
      'com.skype.m2',
    ],
    // —— تلگرام‌های متفرقه رایج ایران ——
    'org.telegram.plus': [
      'org.telegram.plus',
      'org.telegram.messenger',
      'org.telegram.messenger.web',
    ],
    'nekox.messenger': [
      'nekox.messenger',
      'org.telegram.messenger',
    ],
  };

  Set<String> _expandRelatedPackages(Iterable<String> selected) {
    final out = <String>{...selected};
    for (final pkg in List<String>.from(out)) {
      final rel = _relatedVpnPackages[pkg];
      if (rel != null) out.addAll(rel);
      for (final entry in _relatedVpnPackages.entries) {
        if (entry.value.contains(pkg)) out.addAll(entry.value);
      }
    }
    return out;
  }

  /// اعضای خانوادهٔ یک پکیج (برای تیک/حذف هوشمند در UI)
  Set<String> _familyOf(String pkg) {
    final out = <String>{pkg};
    final rel = _relatedVpnPackages[pkg];
    if (rel != null) out.addAll(rel);
    for (final entry in _relatedVpnPackages.entries) {
      if (entry.value.contains(pkg)) out.addAll(entry.value);
    }
    return out;
  }


  Future<void> _loadCachedTunnelBypass() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString('tunnel_bypass_json');
      if (raw == null || raw.isEmpty) return;
      final data = json.decode(raw);
      if (data is! Map) return;
      _applyTunnelBypassMap(Map<String, dynamic>.from(data), save: false);
    } catch (e) {
      debugPrint('loadCachedTunnelBypass: $e');
    }
  }

  void _applyTunnelBypassMap(Map<String, dynamic> data, {bool save = true}) {
    try {
      final pkgs = data['packages'];
      final doms = data['domains'];
      if (pkgs is List && pkgs.isNotEmpty) {
        final list = pkgs.map((e) => e.toString().trim()).where((e) => e.isNotEmpty).toList();
        if (list.length >= 10) {
          _iranPackages = list;
        }
      }
      if (doms is List && doms.isNotEmpty) {
        final list = doms.map((e) => e.toString().trim()).where((e) => e.isNotEmpty).toList();
        if (list.isNotEmpty) {
          _iranDomains = list;
        }
      }
      if (save) {
        SharedPreferences.getInstance().then((prefs) async {
          await prefs.setString('tunnel_bypass_json', json.encode(data));
          await prefs.setInt('tunnel_bypass_fetched_at', DateTime.now().millisecondsSinceEpoch);
        });
      }
    } catch (e) {
      debugPrint('applyTunnelBypassMap: $e');
    }
  }

  /// لیست اپ/دامنه داخلی را در صورت نیاز از سرور تازه می‌کند (fallback = لیست داخل اپ)
  Future<void> _refreshTunnelBypassIfNeeded({bool force = false}) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final last = prefs.getInt('tunnel_bypass_fetched_at') ?? 0;
      final ageMs = DateTime.now().millisecondsSinceEpoch - last;
      final maxAge = tunnelBypassRefreshHours * 3600 * 1000;
      if (!force && last > 0 && ageMs < maxAge) {
        return;
      }
      final res = await http
          .get(Uri.parse(tunnelBypassMetaUrl))
          .timeout(const Duration(seconds: 10));
      if (res.statusCode != 200) return;
      final data = json.decode(res.body);
      if (data is Map) {
        _applyTunnelBypassMap(Map<String, dynamic>.from(data), save: true);
        debugPrint('tunnel bypass list refreshed (${_iranPackages.length} pkgs)');
      }
    } catch (e) {
      debugPrint('refreshTunnelBypass: $e');
    }
  }

  /// حالت «انتخاب من»: هر اپی که تیک نخورده مستقیم است؛ فقط تیک‌خورده‌ها از VPN
  Future<List<String>?> _blockedAppsForConnect() async {
    final castBypass = <String>{
      ..._alwaysDirectPackages,
      ..._castMirrorPackages,
    };

    // حتی «کل گوشی»: سرویس‌های آینه‌سازی/Cast محلی مستقیم بمانند
    if (tunnelMode == 'full') {
      return castBypass.toList();
    }
    if (tunnelMode == 'bypass_local') {
      return {..._iranPackages, ...castBypass}.toList();
    }

    if (selectedVpnPackages.isEmpty) {
      return {..._iranPackages, ...castBypass}.toList();
    }

    final selected = _expandRelatedPackages(selectedVpnPackages);
    final block = <String>{...castBypass};

    try {
      // false = شامل اپ‌های سیستم هم بشود تا واقعاً «فقط انتخابی» باشد
      final apps = await InstalledApps.getInstalledApps(excludeSystemApps: false, withIcon: false, detectPlatformType: false);
      for (final a in apps) {
        final pkg = a.packageName;
        if (pkg.isEmpty) continue;
        if (selected.contains(pkg)) continue;
        block.add(pkg);
      }
    } catch (e) {
      debugPrint('installed_apps error: $e');
      for (final item in selectableVpnApps) {
        final pkg = item['pkg']!;
        if (!selected.contains(pkg)) block.add(pkg);
      }
      block.addAll(_iranPackages);
    }

    for (final p in _iranPackages) {
      if (!selected.contains(p)) block.add(p);
    }

    return block.toList();
  }

  String get tunnelModeLabel {
    switch (tunnelMode) {
      case 'full':
        return 'کل گوشی';
      case 'selected':
        return 'انتخاب من';
      default:
        return 'هوشمند'; // تونل: بجز برنامه‌های داخلی
    }
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
          // کمی صبر تا تونل پایدار شود، بعد IP خروجی
          Future.delayed(const Duration(milliseconds: 1500), () {
            if (mounted) _fetchCurrentIp(force: true);
          });
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
    _fetchCurrentIp(force: true);
    if (connectionModeSmart && _userWantsConnected && !_isRecovering) {
      _scheduleSmartRecovery('verify_fail');
    } else {
      _showToast('اتصال برقرار نشد — سرور قطع یا ناموجود است');
    }
  }

  /// وقتی VPN وصل است، درخواست از پروکسی محلی هسته می‌رود تا IP واقعی خروجی بیاید
  /// پورت‌های inbound محلی هسته (HTTP)
  static const List<int> _localHttpProxyPorts = [10809, 10808, 2081, 2080];

  /// گرفتن IP خام از چند سرویس معتبر (مثل Happ / v2rayNG)
  Future<String?> _httpGetIp({required bool viaProxy}) async {
    final bust = DateTime.now().millisecondsSinceEpoch;
    final urls = <String>[
      'https://api.ipify.org?t=$bust',
      'https://api64.ipify.org?t=$bust',
      'https://icanhazip.com',
      'https://ifconfig.me/ip',
      'https://checkip.amazonaws.com',
    ];

    String? parseIp(String body) {
      final text = body.trim();
      // cloudflare trace: ip=x.x.x.x
      final m = RegExp(r'(?:^|\n)ip=([0-9a-fA-F:\.]+)').firstMatch(text);
      if (m != null) return m.group(1);
      final first = text.split(RegExp(r'[\s,;]+')).firstWhere(
        (s) => s.isNotEmpty,
        orElse: () => '',
      );
      if (first.isEmpty || first.length > 45) return null;
      if (first.contains('<') || first.contains('{')) return null;
      // IPv4 or IPv6-ish
      if (RegExp(r'^\d{1,3}(\.\d{1,3}){3}$').hasMatch(first) ||
          first.contains(':')) {
        return first;
      }
      return null;
    }

    if (viaProxy) {
      for (final port in _localHttpProxyPorts) {
        final client = HttpClient();
        client.connectionTimeout = const Duration(seconds: 4);
        client.idleTimeout = const Duration(seconds: 4);
        client.findProxy = (uri) => 'PROXY 127.0.0.1:$port';
        client.badCertificateCallback = (cert, host, port) => true;
        try {
          for (final u in urls) {
            try {
              final req =
                  await client.getUrl(Uri.parse(u)).timeout(const Duration(seconds: 4));
              req.headers.set(HttpHeaders.cacheControlHeader, 'no-cache');
              req.headers.set(HttpHeaders.pragmaHeader, 'no-cache');
              final res = await req.close().timeout(const Duration(seconds: 4));
              if (res.statusCode == 200) {
                final body = await res.transform(utf8.decoder).join();
                final ip = parseIp(body);
                if (ip != null) return ip;
              }
            } catch (_) {
              continue;
            }
          }
          // cloudflare trace از طریق پروکسی
          try {
            final req = await client
                .getUrl(Uri.parse('https://www.cloudflare.com/cdn-cgi/trace'))
                .timeout(const Duration(seconds: 4));
            final res = await req.close().timeout(const Duration(seconds: 4));
            if (res.statusCode == 200) {
              final body = await res.transform(utf8.decoder).join();
              final ip = parseIp(body);
              if (ip != null) return ip;
            }
          } catch (_) {}
        } finally {
          client.close(force: true);
        }
      }
      // در حالت تونل کامل، سیستم ممکن است خودش از VPN رد کند
    }

    // ——— مسیر مستقیم (بدون پروکسی اپ) — برای حالت قطع الزامی است
    final client = HttpClient();
    client.connectionTimeout = const Duration(seconds: 6);
    client.idleTimeout = const Duration(seconds: 6);
    // مهم: هرگز پروکسی سیستم/قبلی نماند
    client.findProxy = (uri) => 'DIRECT';
    client.badCertificateCallback = (cert, host, port) => true;
    try {
      for (final u in urls) {
        try {
          final req =
              await client.getUrl(Uri.parse(u)).timeout(const Duration(seconds: 5));
          req.headers.set(HttpHeaders.cacheControlHeader, 'no-cache');
          req.headers.set(HttpHeaders.pragmaHeader, 'no-cache');
          final res = await req.close().timeout(const Duration(seconds: 5));
          if (res.statusCode == 200) {
            final body = await res.transform(utf8.decoder).join();
            final ip = parseIp(body);
            if (ip != null) return ip;
          }
        } catch (_) {
          continue;
        }
      }
      try {
        final req = await client
            .getUrl(Uri.parse('https://www.cloudflare.com/cdn-cgi/trace'))
            .timeout(const Duration(seconds: 5));
        final res = await req.close().timeout(const Duration(seconds: 5));
        if (res.statusCode == 200) {
          final body = await res.transform(utf8.decoder).join();
          final ip = parseIp(body);
          if (ip != null) return ip;
        }
      } catch (_) {}
    } finally {
      client.close(force: true);
    }

    // فال‌بک پکیج http (ممکن است از proxy سیستم اندروید تبعیت کند)
    for (final u in urls) {
      try {
        final res = await http
            .get(
              Uri.parse(u),
              headers: const {
                'Cache-Control': 'no-cache, no-store',
                'Pragma': 'no-cache',
              },
            )
            .timeout(const Duration(seconds: 5));
        if (res.statusCode == 200) {
          final ip = parseIp(res.body);
          if (ip != null) return ip;
        }
      } catch (_) {
        continue;
      }
    }
    try {
      final res = await http
          .get(Uri.parse('https://www.cloudflare.com/cdn-cgi/trace'))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final ip = parseIp(res.body);
        if (ip != null) return ip;
      }
    } catch (_) {}
    return null;
  }

  /// قطع: IP واقعی گوشی | وصل: بدون عدد گمراه‌کننده (اپ از تونل خارج است)
  Future<void> _fetchCurrentIp({bool force = false}) async {
    if (_ipFetchInFlight && !force) return;
    final now = DateTime.now();
    if (!force &&
        _lastIpFetchAt != null &&
        now.difference(_lastIpFetchAt!).inSeconds < 2) {
      return;
    }
    _ipFetchInFlight = true;
    if (force && mounted) {
      setState(() => currentIpAddress = '...');
    }
    try {
      if (_isVpnConnected) {
        // روی اندروید خودِ اپ معمولاً از VPN رد نمی‌شود؛
        // عدد اشتباه (IP ایران) نشان نمی‌دهیم.
        if (mounted) {
          setState(() => currentIpAddress = 'محافظت‌شده');
          _lastIpFetchAt = DateTime.now();
        }
        // تلاش بی‌صدا برای IP خروجی از پروکسی محلی (اختیاری)
        final tip = await _httpGetIp(viaProxy: true);
        if (mounted && tip != null && tip.isNotEmpty && _isVpnConnected) {
          setState(() => currentIpAddress = tip);
          _lastIpFetchAt = DateTime.now();
        }
      } else {
        await Future.delayed(const Duration(milliseconds: 400));
        final ip = await _httpGetIp(viaProxy: false);
        if (mounted) {
          setState(() {
            currentIpAddress = (ip != null && ip.isNotEmpty) ? ip : '---';
          });
          _lastIpFetchAt = DateTime.now();
        }
      }
    } catch (_) {
      if (mounted && (currentIpAddress == '...' || currentIpAddress == '---')) {
        setState(() => currentIpAddress = _isVpnConnected ? 'محافظت‌شده' : '---');
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


  static const String _kProfilesKey = 'app_profiles_json';

  Future<void> _persistProfiles() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kProfilesKey, json.encode(profiles));
  }

  Future<void> _loadProfilesFromPrefs(SharedPreferences prefs) async {
    final raw = prefs.getString(_kProfilesKey);
    final List<Map<String, String>> loaded = [];
    if (raw != null && raw.isNotEmpty) {
      try {
        final decoded = json.decode(raw);
        if (decoded is List) {
          for (final e in decoded) {
            if (e is Map) {
              final u = '${e['username'] ?? ''}'.trim();
              final pw = '${e['password'] ?? ''}';
              if (u.isEmpty) continue;
              loaded.add({
                'username': u,
                'password': pw,
                'label': '${e['label'] ?? u}'.trim().isEmpty ? u : '${e['label'] ?? u}'.trim(),
              });
            }
          }
        }
      } catch (_) {}
    }
    // مهاجرت از ذخیرهٔ تک‌اشتراکی قبلی
    final legacyUser = prefs.getString('saved_username');
    final legacyPass = prefs.getString('saved_password') ?? '';
    if (legacyUser != null &&
        legacyUser.trim().isNotEmpty &&
        legacyPass.isNotEmpty &&
        !loaded.any((e) => e['username'] == legacyUser.trim())) {
      loaded.add({
        'username': legacyUser.trim(),
        'password': legacyPass,
        'label': legacyUser.trim(),
      });
    }
    profiles = loaded;
    if (loaded.isNotEmpty) {
      await prefs.setString(_kProfilesKey, json.encode(loaded));
    }
  }

  Future<void> _upsertProfile(String username, String password, {String? label}) async {
    final u = username.trim();
    if (u.isEmpty) return;
    final lbl = (label ?? u).trim().isEmpty ? u : (label ?? u).trim();
    final idx = profiles.indexWhere((e) => e['username'] == u);
    final entry = {'username': u, 'password': password, 'label': lbl};
    if (idx >= 0) {
      // برچسب قبلی را نگه دار اگر کاربر عوض نکرده
      final prevLabel = profiles[idx]['label'];
      if (label == null && prevLabel != null && prevLabel.isNotEmpty) {
        entry['label'] = prevLabel!;
      }
      profiles[idx] = entry;
    } else {
      profiles.add(entry);
    }
    await _persistProfiles();
  }

  Future<void> _deleteProfile(String username) async {
    final u = username.trim();
    profiles.removeWhere((e) => e['username'] == u);
    await _persistProfiles();
    final prefs = await SharedPreferences.getInstance();
    if (savedUser == u) {
      // اگر پروفایل فعال حذف شد
      await _clearActiveSession(prefs, stopVpn: true);
      if (profiles.isNotEmpty) {
        final next = profiles.first;
        await _activateProfile(next['username']!, next['password']!, fetch: true);
      }
    }
  }

  Future<void> _clearActiveSession(SharedPreferences prefs, {bool stopVpn = false}) async {
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
    if (stopVpn) {
      try {
        if (_isVpnConnected || _statusMeansConnected(v2rayStatus.state)) {
          await flutterV2ray.stopV2Ray();
        }
      } catch (_) {}
    }
    if (mounted) {
      setState(() {
        savedUser = null;
        savedPass = null;
        userData = null;
        serverList.clear();
        selectedServerIndex = 0;
        activePing = -1;
        _connectionVerified = false;
        _uiForceDisconnected = true;
        isConnecting = false;
        _userWantsConnected = false;
        _isRecovering = false;
      });
    }
  }

  Future<void> _activateProfile(String username, String password, {bool fetch = true}) async {
    // قطع اتصال قبلی قبل از سوئیچ
    _verifyGen++;
    _recoveryGen++;
    _userWantsConnected = false;
    _stopHealthWatch();
    try {
      await flutterV2ray.stopV2Ray();
    } catch (_) {}
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('saved_username', username);
    await prefs.setString('saved_password', password);
    // کش سرور پروفایل قبلی را پاک کن تا قاطی نشود
    await prefs.remove('cached_user_json');
    await prefs.remove('cached_servers_json');
    await prefs.remove('cached_for_username');
    await prefs.remove('last_server_id');
    if (mounted) {
      setState(() {
        savedUser = username;
        savedPass = password;
        userData = null;
        serverList.clear();
        selectedServerIndex = 0;
        activePing = -1;
        _connectionVerified = false;
        _uiForceDisconnected = true;
        isConnecting = false;
        _userController.text = username;
        _passController.text = password;
      });
    }
    await _upsertProfile(username, password);
    if (fetch) {
      await _fetchUserData(username, password, doPingOnLoad: false);
    }
  }

  Future<void> _loadSavedPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    await _loadProfilesFromPrefs(prefs);
    final user = prefs.getString('saved_username');
    final pass = prefs.getString('saved_password') ?? '';
    String savedTunnel = prefs.getString('pref_tunnel_mode') ?? '';
    if (savedTunnel.isEmpty) {
      final oldBool = prefs.getBool('only_filtered_apps');
      savedTunnel = (oldBool == false) ? 'full' : 'bypass_local';
    }
    if (savedTunnel != 'full' && savedTunnel != 'bypass_local' && savedTunnel != 'selected') {
      savedTunnel = 'bypass_local';
    }
    final savedSelectedRaw = prefs.getString('pref_selected_vpn_packages');
    List<String> savedSelected = [
      'org.telegram.messenger',
      'com.instagram.android',
      'com.google.android.youtube',
      'com.android.chrome',
      'com.twitter.android',
      'com.whatsapp',
    ];
    if (savedSelectedRaw != null && savedSelectedRaw.isNotEmpty) {
      try {
        final dec = json.decode(savedSelectedRaw);
        if (dec is List) {
          savedSelected = dec.map((e) => '$e').where((e) => e.isNotEmpty).toList();
        }
      } catch (_) {}
    }
    final prefTheme = prefs.getString('pref_ui_theme') ?? 'classic';
    final prefAutoRefresh = prefs.getBool('pref_auto_refresh_on_start') ?? true;
    final prefAutoPing = prefs.getBool('pref_auto_ping_on_start') ?? false;
    final prefKeepServer = prefs.getBool('pref_prefer_last_server') ?? true;
    final prefSmart = prefs.getBool('pref_connection_mode_smart') ?? true;
    final prefModeChosen = prefs.getBool('pref_connection_mode_chosen') ?? false;
    final prefStability = prefs.getBool('pref_prefer_stability') ?? true;

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
        tunnelMode = savedTunnel;
        // ignore: discarded_futures
        _loadCachedTunnelBypass().then((_) => _refreshTunnelBypassIfNeeded());
        selectedVpnPackages = savedSelected;
        uiThemeId = (prefTheme == 'jet') ? 'jet' : 'classic';
      autoRefreshOnStart = prefAutoRefresh;
        autoPingOnStart = prefAutoPing;
        preferLastServer = prefKeepServer;
        connectionModeSmart = prefSmart;
        connectionModeChosen = prefModeChosen;
        preferStability = prefStability;
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

  Future<void> _saveUiTheme(String id) async {
    final v = (id == 'jet') ? 'jet' : 'classic';
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('pref_ui_theme', v);
    if (mounted) setState(() => uiThemeId = v);
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

  Future<void> _saveTunnelMode(String mode) async {
    if (mode != 'full' && mode != 'bypass_local' && mode != 'selected') {
      mode = 'bypass_local';
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('pref_tunnel_mode', mode);
    await prefs.setBool('only_filtered_apps', mode != 'full');
    if (mounted) {
      setState(() {
        tunnelMode = mode;
      });
    }
    if (mode == 'selected' && selectedVpnPackages.isEmpty && mounted) {
      _showToast('برای انتخاب اپ‌ها دکمه را لمس طولانی کنید', isError: false);
    }
    if (_isVpnConnected) {
      _showToast('در حال اعمال حالت تونل...', isError: false);
      await _toggleConnect();
      await Future.delayed(const Duration(milliseconds: 300));
      await _toggleConnect();
    }
  }

  Future<void> _saveSelectedVpnPackages(List<String> pkgs) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('pref_selected_vpn_packages', json.encode(pkgs));
    if (mounted) {
      setState(() {
        selectedVpnPackages = List<String>.from(pkgs);
      });
    }
    if (_isVpnConnected && tunnelMode == 'selected') {
      _showToast('در حال اعمال لیست اپ‌ها...', isError: false);
      await _toggleConnect();
      await Future.delayed(const Duration(milliseconds: 300));
      await _toggleConnect();
    }
  }

  Future<void> _showSelectedAppsSheet() async {
    if (!mounted) return;

    final knownNames = <String, String>{
      for (final e in selectableVpnApps) e['pkg']!: e['name']!,
      'com.android.chrome': 'کروم (Chrome)',
      'com.chrome.beta': 'کروم بتا',
      'com.chrome.dev': 'کروم Dev',
      'com.google.android.apps.chrome': 'کروم',
      'com.android.webview': 'Android System WebView',
      'com.google.android.webview': 'Android System WebView',
      'org.telegram.messenger': 'تلگرام',
      'org.telegram.messenger.web': 'تلگرام (وب)',
      'org.telegram.messenger.beta': 'تلگرام بتا',
      'org.thunderdog.challegram': 'Telegram X',
      'com.instagram.android': 'اینستاگرام',
      'com.instagram.barcelona': 'Threads',
      'com.google.android.youtube': 'یوتیوب',
      'com.whatsapp': 'واتساپ',
      'com.twitter.android': 'توییتر / X',
      'org.mozilla.firefox': 'فایرفاکس',
      'com.sec.android.app.sbrowser': 'مرورگر سامسونگ',
      'com.opera.browser': 'اوپرا',
      'com.brave.browser': 'Brave',
      'com.microsoft.emmx': 'Edge',
      'com.facebook.katana': 'فیسبوک',
      'com.facebook.orca': 'مسنجر',
      'com.zhiliaoapp.musically': 'تیک‌تاک',
      'com.discord': 'دیسکورد',
    };

    const forceCheckPackages = <String>[
      'com.android.chrome',
      'com.chrome.beta',
      'com.chrome.dev',
      'com.google.android.apps.chrome',
      'com.android.webview',
      'com.google.android.webview',
      'org.telegram.messenger',
      'org.telegram.messenger.web',
      'org.telegram.messenger.beta',
      'org.thunderdog.challegram',
      'org.telegram.plus',
      'nekox.messenger',
      'com.instagram.android',
      'com.instagram.barcelona',
      'com.instagram.lite',
      'com.facebook.katana',
      'com.facebook.orca',
      'com.facebook.lite',
      'com.google.android.youtube',
      'com.google.android.apps.youtube.music',
      'com.whatsapp',
      'com.whatsapp.w4b',
      'com.twitter.android',
      'com.zhiliaoapp.musically',
      'com.ss.android.ugc.trill',
      'com.discord',
      'com.reddit.frontpage',
      'com.spotify.music',
      'com.linkedin.android',
      'com.snapchat.android',
      'com.openai.chatgpt',
      'com.google.android.gm',
      'com.google.android.apps.maps',
      'org.mozilla.firefox',
      'com.sec.android.app.sbrowser',
      'com.opera.browser',
      'com.brave.browser',
      'com.microsoft.emmx',
    ];

    var catalog = <Map<String, String>>[];
    final seen = <String>{};

    void addPkg(String pkg, String name) {
      if (pkg.isEmpty || pkg == 'com.jetconfig.vpn') return;
      if (seen.contains(pkg)) return;
      seen.add(pkg);
      catalog.add({'pkg': pkg, 'name': name});
    }

    // ۱) همه اپ‌های قابل‌اجرا (حتی سیستمی مثل کروم)
    try {
      final apps = await InstalledApps.getInstalledApps(
        excludeSystemApps: false,
        excludeNonLaunchableApps: false,
        withIcon: false,
        detectPlatformType: false,
      );
      for (final a in apps) {
        final pkg = a.packageName;
        // شلوغی سیستم را کم کن؛ ولی کروم/تلگرام و ... را نگه دار
        final isForced = forceCheckPackages.contains(pkg) ||
            knownNames.containsKey(pkg) ||
            pkg.contains('chrome') ||
            pkg.contains('telegram') ||
            pkg.contains('instagram') ||
            pkg.contains('firefox') ||
            pkg.contains('webview');
        final isJunk = pkg.startsWith('com.android.providers.') ||
            pkg.startsWith('com.android.server.') ||
            pkg == 'android' ||
            pkg.startsWith('com.qualcomm.') ||
            pkg.startsWith('com.samsung.android.providers.');
        if (isJunk && !isForced) continue;
        final name = (a.name.trim().isNotEmpty)
            ? a.name.trim()
            : (knownNames[pkg] ?? pkg);
        addPkg(pkg, name);
      }
    } catch (e) {
      debugPrint('sheet getInstalledApps: $e');
    }

    // ۲) پکیج‌های مهم را مستقیم با packageNames بگیر (قابل‌اطمینان‌تر)
    try {
      final forced = await InstalledApps.getInstalledApps(
        packageNames: forceCheckPackages,
        excludeSystemApps: false,
        withIcon: false,
        detectPlatformType: false,
      );
      for (final a in forced) {
        final pkg = a.packageName;
        final name = (a.name.trim().isNotEmpty)
            ? a.name.trim()
            : (knownNames[pkg] ?? pkg);
        addPkg(pkg, name);
      }
    } catch (e) {
      debugPrint('sheet packageNames: $e');
    }

    // ۳) isAppInstalled تک‌تک برای اطمینان از کروم و ...
    for (final pkg in forceCheckPackages) {
      if (seen.contains(pkg)) continue;
      try {
        final ok = await InstalledApps.isAppInstalled(pkg);
        if (ok == true) {
          String name = knownNames[pkg] ?? pkg;
          try {
            final info = await InstalledApps.getAppInfo(pkg, withIcon: false);
            if (info != null && info.name.trim().isNotEmpty) name = info.name.trim();
          } catch (_) {}
          addPkg(pkg, name);
        }
      } catch (_) {}
    }

    if (catalog.isEmpty) {
      for (final e in selectableVpnApps) {
        addPkg(e['pkg']!, e['name']!);
      }
    }

    for (final pkg in selectedVpnPackages) {
      if (!seen.contains(pkg)) {
        addPkg(pkg, knownNames[pkg] ?? pkg);
      }
    }

    void sortCatalog(List<Map<String, String>> list, Set<String> checked) {
      list.sort((a, b) {
        final ac = checked.contains(a['pkg']);
        final bc = checked.contains(b['pkg']);
        if (ac != bc) return ac ? -1 : 1;
        // محبوب‌ها بالاتر در جستجو
        int score(Map<String, String> e) {
          final pkg = e['pkg'] ?? '';
          if (pkg == 'com.android.chrome') return 0;
          if (pkg.contains('telegram')) return 1;
          if (pkg.contains('instagram')) return 2;
          if (pkg.contains('chrome')) return 3;
          return 10;
        }
        final s = score(a).compareTo(score(b));
        if (s != 0) return s;
        return (a['name'] ?? '').compareTo(b['name'] ?? '');
      });
    }

    var draft = List<String>.from(selectedVpnPackages);
    sortCatalog(catalog, draft.toSet());
    _selectedAppsFilter = '';

    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: const Color(0xFF131B2E),
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return Directionality(
          textDirection: TextDirection.rtl,
          child: StatefulBuilder(
            builder: (ctx, setLocal) {
              final media = MediaQuery.of(ctx);
              final kb = media.viewInsets.bottom;
              final maxListH = (media.size.height - kb) * 0.42;

              List<Map<String, String>> visible() {
                final f = _selectedAppsFilter.trim().toLowerCase();
                final list = catalog.where((e) {
                  if (f.isEmpty) return true;
                  final name = (e['name'] ?? '').toLowerCase();
                  final pkg = (e['pkg'] ?? '').toLowerCase();
                  // جستجوی هوشمند: chr → chrome
                  if (f == 'chr' || f == 'chro' || f == 'chrom') {
                    return name.contains('chrome') ||
                        name.contains('کروم') ||
                        pkg.contains('chrome');
                  }
                  if (f.contains('کروم')) {
                    return name.contains('کروم') ||
                        name.contains('chrome') ||
                        pkg.contains('chrome');
                  }
                  return name.contains(f) || pkg.contains(f);
                }).toList();
                sortCatalog(list, draft.toSet());
                return list;
              }

              return Padding(
                padding: EdgeInsets.only(bottom: kb),
                child: SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 40,
                          height: 4,
                          margin: const EdgeInsets.only(bottom: 12),
                          decoration: BoxDecoration(
                            color: Colors.white24,
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                        const Text(
                          'انتخاب من',
                          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'فقط اپ‌های تیک‌خورده از VPN می‌روند.\nبا تیک هر اپ، پیش‌نیازهای مرتبط (اگر نصب باشند) خودکار اضافه می‌شوند.',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.white38, fontSize: 11.5, height: 1.35),
                        ),
                        const SizedBox(height: 10),
                        TextField(
                          style: const TextStyle(color: Colors.white, fontSize: 13),
                          decoration: InputDecoration(
                            hintText: 'جستجو (مثلاً chrome یا کروم)',
                            hintStyle: const TextStyle(color: Colors.white30),
                            prefixIcon: const Icon(Icons.search, color: Colors.white38, size: 20),
                            filled: true,
                            fillColor: const Color(0xFF0D1424),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide.none,
                            ),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                          ),
                          onChanged: (v) => setLocal(() => _selectedAppsFilter = v),
                        ),
                        const SizedBox(height: 8),
                        ConstrainedBox(
                          constraints: BoxConstraints(maxHeight: maxListH.clamp(120.0, 420.0)),
                          child: Builder(
                            builder: (_) {
                              final items = visible();
                              if (items.isEmpty) {
                                return const Padding(
                                  padding: EdgeInsets.all(24),
                                  child: Text(
                                    'اپی پیدا نشد — اگر کروم نصب است یک‌بار VPN را قطع کنید و دوباره لیست را باز کنید',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(color: Colors.white54, fontSize: 12),
                                  ),
                                );
                              }
                              return ListView.builder(
                                shrinkWrap: true,
                                keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                                itemCount: items.length,
                                itemBuilder: (_, i) {
                                  final item = items[i];
                                  final pkg = item['pkg']!;
                                  final name = item['name']!;
                                  final on = draft.contains(pkg);
                                  return CheckboxListTile(
                                    value: on,
                                    activeColor: const Color(0xFF00E5FF),
                                    title: Text(name, style: const TextStyle(color: Colors.white, fontSize: 13.5)),
                                    subtitle: Text(pkg, style: const TextStyle(color: Colors.white30, fontSize: 10)),
                                    onChanged: (v) {
                                      setLocal(() {
                                        final family = _familyOf(pkg);
                                        final installed = catalog.map((e) => e['pkg']!).toSet();
                                        if (v == true) {
                                          for (final p in family) {
                                            // حتی اگر در کاتالوگ نباشد، برای اتصال ذخیره شود
                                            if (p == pkg || installed.contains(p) || forceCheckPackages.contains(p)) {
                                              if (!draft.contains(p)) draft.insert(0, p);
                                            }
                                          }
                                        } else {
                                          draft.removeWhere((p) => family.contains(p));
                                        }
                                        sortCatalog(catalog, draft.toSet());
                                      });
                                    },
                                  );
                                },
                              );
                            },
                          ),
                        ),
                        const SizedBox(height: 10),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF00E5FF),
                              foregroundColor: Colors.black,
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                            ),
                            onPressed: () async {
                              final installed = catalog.map((e) => e['pkg']!).toSet();
                              final expanded = _expandRelatedPackages(draft).toList();
                              // فقط نصب‌شده‌ها + چیزهایی که کاربر صریح داشته
                              final checked = <String>[];
                              for (final pkg in expanded) {
                                if (installed.contains(pkg) || draft.contains(pkg) || forceCheckPackages.contains(pkg)) {
                                  if (!checked.contains(pkg)) checked.add(pkg);
                                }
                              }
                              Navigator.pop(ctx);
                              await _saveSelectedVpnPackages(checked);
                            },
                            child: Text(
                              'ذخیره (${draft.length} اپ)',
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        );
      },
    );
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


  /// User-Agent شبیه کلاینت‌های رسمی تا در پنل «کلاینت‌های اشتراک» درست دیده شود
  String _clientUserAgent() {
    try {
      final os = Platform.isAndroid
          ? 'Android'
          : (Platform.isIOS ? 'iOS' : Platform.operatingSystem);
      var ver = Platform.operatingSystemVersion;
      // کوتاه‌سازی نسخه طولانی اندروید
      if (ver.length > 40) {
        ver = ver.substring(0, 40);
      }
      return 'JetConfig/$appVersion ($os; $ver)';
    } catch (_) {
      return 'JetConfig/$appVersion';
    }
  }

  /// ثبت حضور کلاینت واقعی در پنل (سابسکریپشن از روی گوشی با UA درست)
  Future<void> _registerClientOnPanel(Map data) async {
    try {
      final sub = (data['subscription_url'] ?? data['sub_link'] ?? '').toString().trim();
      if (sub.isEmpty || !sub.startsWith('http')) return;
      final req = http.Request('GET', Uri.parse(sub));
      req.headers['User-Agent'] = _clientUserAgent();
      req.headers['Accept'] = '*/*';
      final client = http.Client();
      try {
        final streamed = await client.send(req).timeout(const Duration(seconds: 8));
        // بدنه لازم نیست؛ فقط هدر برای ثبت در پنل
        await streamed.stream.drain();
      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('registerClientOnPanel: $e');
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
          await _upsertProfile(username, password);

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

          // ثبت کلاینت در پنل پاسارگاد/مرزبان با UA واقعی گوشی
          unawaited(_registerClientOnPanel(Map<String, dynamic>.from(data as Map)));

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


  /// انتخاب بهترین سرور برای مود هوشمند (بعد از پینگ سریع+واقعی)
  Future<void> _selectSmartBestServer({int? excludeIndex}) async {
    if (serverList.isEmpty) return;
    int bestIdx = -1;
    int bestPing = 1 << 30;

    for (int i = 0; i < serverList.length; i++) {
      if (excludeIndex != null && i == excludeIndex) continue;
      final p = serverList[i].ping;
      if (p <= 0) continue;
      if (preferStability && p < 30) continue;
      if (p < bestPing) {
        bestPing = p;
        bestIdx = i;
      }
    }
    if (bestIdx < 0) {
      bestPing = 1 << 30;
      for (int i = 0; i < serverList.length; i++) {
        if (excludeIndex != null && i == excludeIndex) continue;
        final p = serverList[i].ping;
        if (p <= 0) continue;
        if (p < bestPing) {
          bestPing = p;
          bestIdx = i;
        }
      }
    }
    if (bestIdx < 0) {
      bestIdx = selectedServerIndex.clamp(0, serverList.length - 1);
    }
    if (mounted) {
      setState(() => selectedServerIndex = bestIdx);
    }
    await _saveSelectedServer(serverList[bestIdx], index: bestIdx);
  }


  void _stopHealthWatch() {
    _healthTimer?.cancel();
    _healthTimer = null;
    _healthFailCount = 0;
  }

  void _startHealthWatch() {
    _stopHealthWatch();
    if (!connectionModeSmart || !_userWantsConnected) return;
    // چک سریع‌تر: قطعی اینترنت دستگاه را زودتر بفهمیم
    _healthTimer = Timer.periodic(const Duration(seconds: 8), (_) {
      _healthTick();
    });
    // اولین چک زودتر از دورهٔ کامل
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) _healthTick();
    });
  }

  /// آیا اینترنت خود گوشی (نه لزوماً تونل) زنده است؟
  Future<bool> _hasDeviceNetwork() async {
    for (final host in <String>['1.1.1.1', '8.8.8.8']) {
      try {
        final socket = await Socket.connect(
          host,
          host == '8.8.8.8' ? 53 : 443,
          timeout: const Duration(seconds: 2),
        );
        socket.destroy();
        return true;
      } catch (_) {}
    }
    return false;
  }

  Future<void> _healthTick() async {
    if (!mounted || !connectionModeSmart || !_userWantsConnected) return;
    if (_isRecovering || isConnecting) return;

    // هسته قطع شده
    if (!_statusMeansConnected(v2rayStatus.state)) {
      if (mounted && _connectionVerified) {
        setState(() {
          _connectionVerified = false;
          activePing = -1;
        });
      }
      _scheduleSmartRecovery('health_state');
      return;
    }

    // سلامت واقعی تونل (وقتی اینترنت گوشی قطع است معمولاً timeout می‌شود)
    int delay = -1;
    try {
      delay = await flutterV2ray
          .getConnectedServerDelay()
          .timeout(const Duration(seconds: 4));
    } catch (_) {
      delay = -1;
    }
    if (!mounted || !_userWantsConnected) return;

    if (delay >= 0 && delay <= 15000) {
      _healthFailCount = 0;
      if (mounted) {
        setState(() {
          activePing = delay;
          _deviceNetworkDown = false;
          // اگر قبلاً از سبز خارج شده بود و تونل دوباره سالم است
          if (!_connectionVerified) {
            _connectionVerified = true;
          }
        });
      }
      return;
    }

    // شکست: فوراً دکمه از سبز خارج شود (حتی قبل از بازیابی)
    _healthFailCount++;
    if (mounted) {
      setState(() {
        _connectionVerified = false;
        activePing = -1;
        // اگر خود شبکه هم پاسخ ندهد برچسب مناسب
        _deviceNetworkDown = true; // موقت؛ پایین‌تر دقیق می‌شود
      });
    }

    // تشخیص تقریبی: آیا خود دستگاه شبکه دارد؟
    // فقط وقتی تونل جواب نداد — اگر سوکت هم شکست → اینترنت دستگاه
    final netOk = await _hasDeviceNetwork();
    if (!mounted) return;
    if (mounted) {
      setState(() => _deviceNetworkDown = !netOk);
    }

    if (!netOk) {
      // شبکه دستگاه قطع — منتظر تیک بعدی؛ دکمه دیگر سبز نیست
      return;
    }

    // شبکه هست ولی تونل مرده → بازیابی
    _healthFailCount = 0;
    _scheduleSmartRecovery('health_delay');
  }

  void _scheduleSmartRecovery(String reason) {
    if (!connectionModeSmart || !_userWantsConnected) return;
    if (_isRecovering) return;
    final now = DateTime.now();
    final minGap = reason == 'network_back' ? 3 : 10;
    if (_lastRecoveryAt != null &&
        now.difference(_lastRecoveryAt!).inSeconds < minGap) {
      return; // ضد flapping
    }
    debugPrint('scheduleSmartRecovery: $reason');
    _lastRecoveryAt = now;
    Future.microtask(() => _runSmartRecovery(reason));
  }

  Future<void> _runSmartRecovery(String reason) async {
    if (!mounted || !connectionModeSmart || !_userWantsConnected) return;
    if (_isRecovering) return;
    final gen = ++_recoveryGen;
    _isRecovering = true;
    _stopHealthWatch();
    if (mounted) {
      setState(() {
        isConnecting = true;
        _connectionVerified = false;
        _uiForceDisconnected = false;
      });
    }
    debugPrint('runSmartRecovery start: $reason');

    try {
      // اگر خود اینترنت گوشی قطع است بازیابی بی‌فایده است
      if (!await _hasDeviceNetwork()) {
        if (!mounted || gen != _recoveryGen) return;
        if (mounted) {
          setState(() {
            _isRecovering = false;
            isConnecting = false;
            _connectionVerified = false;
            _deviceNetworkDown = true;
            activePing = -1;
          });
        }
        // health watch را برگردان تا با برگشت شبکه دوباره تلاش کند
        _startHealthWatch();
        return;
      }
      if (mounted) setState(() => _deviceNetworkDown = false);

      // ۱) تلاش مجدد همان سرور
      try {
        await flutterV2ray.stopV2Ray();
      } catch (_) {}
      await Future.delayed(const Duration(milliseconds: 400));
      if (!mounted || gen != _recoveryGen || !_userWantsConnected) return;

      var ok = await _startCoreOnIndex(
        selectedServerIndex.clamp(0, serverList.length - 1),
        recoveryGen: gen,
      );
      if (ok && await _waitUntilVerified(gen, seconds: 10)) {
        debugPrint('recovery: same server ok');
        return;
      }

      // ۲) پینگ و سوییچ به سرور بعدی
      if (!mounted || gen != _recoveryGen || !_userWantsConnected) return;
      final prevIdx = selectedServerIndex;
      await _pingAllServers(allowFallbackSwitch: true);
      if (!mounted || gen != _recoveryGen || !_userWantsConnected) return;
      await _selectSmartBestServer();
      // اگر همان قبلی بود، دومین بهترین
      if (selectedServerIndex == prevIdx && serverList.length > 1) {
        await _selectSmartBestServer(excludeIndex: prevIdx);
      }
      try {
        await flutterV2ray.stopV2Ray();
      } catch (_) {}
      await Future.delayed(const Duration(milliseconds: 300));
      ok = await _startCoreOnIndex(
        selectedServerIndex.clamp(0, serverList.length - 1),
        recoveryGen: gen,
      );
      if (ok && await _waitUntilVerified(gen, seconds: 10)) {
        debugPrint('recovery: failover ok');
        return;
      }

      // ۳) یک‌بار رفرش اشتراک (قطعی کامل) سپس آخرین تلاش
      if (!mounted || gen != _recoveryGen || !_userWantsConnected) return;
      if (savedUser != null && savedPass != null) {
        await _fetchUserData(
          savedUser!,
          savedPass!,
          silentBackground: true,
          doPingOnLoad: false,
        );
        if (!mounted || gen != _recoveryGen || !_userWantsConnected) return;
        await _pingAllServers(allowFallbackSwitch: true);
        await _selectSmartBestServer();
        try {
          await flutterV2ray.stopV2Ray();
        } catch (_) {}
        await Future.delayed(const Duration(milliseconds: 300));
        ok = await _startCoreOnIndex(
          selectedServerIndex.clamp(0, serverList.length - 1),
          recoveryGen: gen,
        );
        if (ok && await _waitUntilVerified(gen, seconds: 12)) {
          debugPrint('recovery: after refresh ok');
          return;
        }
      }

      if (!mounted || gen != _recoveryGen) return;
      _userWantsConnected = false;
      if (mounted) {
        setState(() {
          _isRecovering = false;
          isConnecting = false;
          _connectionVerified = false;
          _uiForceDisconnected = true;
        });
      }
      _showToast('اتصال پایدار نشد — بعداً دوباره امتحان کن');
    } catch (e) {
      debugPrint('recovery error: $e');
      if (mounted && gen == _recoveryGen) {
        setState(() {
          _isRecovering = false;
          isConnecting = false;
        });
      }
    } finally {
      if (gen == _recoveryGen && mounted && !_connectionVerified) {
        // اگر وسط verify هستیم isRecovering را verify تمام می‌کند
      }
    }
  }

  Future<bool> _waitUntilVerified(int gen, {int seconds = 10}) async {
    final steps = seconds * 2;
    for (var i = 0; i < steps; i++) {
      if (!mounted || gen != _recoveryGen || !_userWantsConnected) return false;
      if (_connectionVerified && _statusMeansConnected(v2rayStatus.state)) {
        if (mounted) setState(() => _isRecovering = false);
        return true;
      }
      await Future.delayed(const Duration(milliseconds: 500));
    }
    return false;
  }

  /// فقط استارت هسته روی ایندکس (بدون پینگ مجدد)
  Future<bool> _startCoreOnIndex(int index, {required int recoveryGen}) async {
    if (serverList.isEmpty || index < 0 || index >= serverList.length) return false;
    if (!mounted || recoveryGen != _recoveryGen || !_userWantsConnected) return false;
    if (tunnelMode == 'selected' && selectedVpnPackages.isEmpty) {
      if (mounted) _showToast('در حالت «انتخاب من» حداقل یک اپ را تیک بزن');
      return false;
    }
    final target = serverList[index];
    try {
      final bool permissionGranted = await flutterV2ray.requestPermission();
      if (!permissionGranted) return false;
      final configString = _prepareConfigForCore(target.config);
      if (configString.isEmpty) return false;
      if (mounted) {
        setState(() {
          selectedServerIndex = index;
          isConnecting = true;
          _uiForceDisconnected = false;
          _connectionVerified = false;
        });
      }
      await flutterV2ray.startV2Ray(
        remark: target.name,
        config: configString,
        blockedApps: await _blockedAppsForConnect(),
        proxyOnly: false,
        notificationDisconnectButtonName: 'قطع اتصال',
      );
      await _saveSelectedServer(target, index: index);
      return true;
    } catch (e) {
      debugPrint('startCoreOnIndex error: $e');
      return false;
    }
  }

  Future<void> _toggleConnect() async {
    // اگر UI وصل است یا هسته هنوز CONNECTED / در حال اتصال است → قطع کن
    final coreStillUp = _statusMeansConnected(v2rayStatus.state);
    if (_isVpnConnected || coreStillUp || isConnecting || _isRecovering) {
      _verifyGen++; // باطل کردن verify در جریان
      _recoveryGen++; // باطل کردن بازیابی
      _userWantsConnected = false;
      _stopHealthWatch();
      if (mounted) {
        setState(() {
          _uiForceDisconnected = true;
          _connectionVerified = false;
          activePing = -1;
          isConnecting = false;
          _isRecovering = false;
          _deviceNetworkDown = false;
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
      // صبر تا تونل سیستم کاملاً بسته شود، بعد IP واقعی
      Future.delayed(const Duration(milliseconds: 700), () {
        if (mounted) _fetchCurrentIp(force: true);
      });
      return;
    }

    _userWantsConnected = true;
    _stopHealthWatch();

    // مود هوشمند: پینگ → اگر زنده نبود رفرش اشتراک → پینگ دوباره → اتصال
    if (connectionModeSmart) {
      if (mounted) {
        setState(() {
          isConnecting = true;
          _uiForceDisconnected = false;
          _connectionVerified = false;
        });
      }
      try {
        // اگر لیست خالی است اول رفرش کن
        if (serverList.isEmpty && savedUser != null && savedPass != null) {
          await _fetchUserData(
            savedUser!,
            savedPass!,
            silentBackground: true,
            doPingOnLoad: false,
          );
        }

        if (serverList.isNotEmpty) {
          await _pingAllServers(allowFallbackSwitch: true);
          await _selectSmartBestServer();
        }

        if (!mounted) return;
        var hasAlive = serverList.any((s) => s.ping > 0);

        // هیچ سرور زنده‌ای نیست → یک‌بار بروزرسانی اشتراک و تلاش مجدد
        if (!hasAlive && savedUser != null && savedPass != null) {
          debugPrint('smart connect: no alive servers → refresh subscription');
          await _fetchUserData(
            savedUser!,
            savedPass!,
            silentBackground: true,
            doPingOnLoad: false,
          );
          if (!mounted) return;
          if (serverList.isNotEmpty) {
            await _pingAllServers(allowFallbackSwitch: true);
            await _selectSmartBestServer();
          }
          hasAlive = serverList.any((s) => s.ping > 0);
        }

        if (!hasAlive) {
          _showToast(
            serverList.isEmpty
                ? 'لیست سرور خالی است — از ربات وارد شو یا پشتیبانی'
                : 'بعد از بروزرسانی هم سرور زنده‌ای پیدا نشد',
          );
          if (mounted) {
            setState(() {
              isConnecting = false;
              _connectionVerified = false;
              _uiForceDisconnected = true;
            });
          }
          _userWantsConnected = false;
          return;
        }
      } catch (e) {
        debugPrint('smart pre-connect error: $e');
      }
    } else if (serverList.isEmpty) {
      _showToast('هیچ سروری در لیست وجود ندارد — یک‌بار بروزرسانی کن');
      _userWantsConnected = false;
      return;
    }

    final target = serverList[selectedServerIndex.clamp(0, serverList.length - 1)];
    if (target.ping == -2) {
      _showToast('این سرور ناموجود است — در حال تلاش…');
    }

    if (mounted) {
      setState(() {
        isConnecting = true;
        _uiForceDisconnected = false;
        _connectionVerified = false;
      });
    }

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
        blockedApps: await _blockedAppsForConnect(),
        proxyOnly: false,
        notificationDisconnectButtonName: 'قطع اتصال',
      );
      await _saveSelectedServer(target);
      // تأیید واقعی در onStatusChanged → _verifyLiveConnection
      // اگر هسته اصلاً CONNECTED نداد، بعد از چند ثانیه قطع کن
      Future.delayed(const Duration(seconds: 8), () {
        if (!mounted) return;
        if (_isRecovering) return; // بازیابی خودش مدیریت می‌کند
        if (isConnecting && !_connectionVerified && !_uiForceDisconnected && _userWantsConnected) {
          _verifyGen++;
          if (connectionModeSmart) {
            _scheduleSmartRecovery('connect_timeout');
          } else {
            flutterV2ray.stopV2Ray().catchError((_) {});
            setState(() {
              isConnecting = false;
              _connectionVerified = false;
              _uiForceDisconnected = true;
            });
            _showToast('زمان اتصال تمام شد — سرور دیگری را امتحان کن');
          }
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
    final t = ui;
    final glowColor = isConnected ? t.success : t.accent;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: t.card,
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
      child: Text(
        currentIpAddress,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.w900,
          fontSize: 12,
          letterSpacing: 0.5,
          fontFamily: 'monospace',
        ),
      ),
    );
  }


  Future<void> _showAddProfileDialog() async {
    final uCtrl = TextEditingController();
    final pCtrl = TextEditingController();
    var obscure = true;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return Directionality(
          textDirection: TextDirection.rtl,
          child: StatefulBuilder(
            builder: (ctx, setLocal) {
              return AlertDialog(
                backgroundColor: const Color(0xFF1A2332),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
                title: const Text('افزودن اشتراک', style: TextStyle(color: Colors.white, fontSize: 16)),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: uCtrl,
                      style: const TextStyle(color: Colors.white),
                      decoration: const InputDecoration(
                        labelText: 'نام کاربری',
                        labelStyle: TextStyle(color: Colors.white54),
                      ),
                    ),
                    TextField(
                      controller: pCtrl,
                      obscureText: obscure,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        labelText: 'رمز عبور',
                        labelStyle: const TextStyle(color: Colors.white54),
                        suffixIcon: IconButton(
                          icon: Icon(obscure ? Icons.visibility_off : Icons.visibility, color: Colors.grey),
                          onPressed: () => setLocal(() => obscure = !obscure),
                        ),
                      ),
                    ),
                  ],
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx, false),
                    child: const Text('انصراف', style: TextStyle(color: Colors.redAccent)),
                  ),
                  TextButton(
                    onPressed: () => Navigator.pop(ctx, true),
                    child: const Text('افزودن', style: TextStyle(color: Color(0xFF00E5FF))),
                  ),
                ],
              );
            },
          ),
        );
      },
    );
    if (ok != true) return;
    final u = uCtrl.text.trim();
    final pw = pCtrl.text.trim();
    if (u.isEmpty || pw.isEmpty) {
      _showToast('نام کاربری و رمز را وارد کن');
      return;
    }
    await _activateProfile(u, pw, fetch: true);
    if (mounted && userData != null) {
      _showToast('اشتراک اضافه شد', isError: false);
    }
  }

  Future<void> _showProfilesSheet() async {
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: const Color(0xFF131B2E),
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return Directionality(
          textDirection: TextDirection.rtl,
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 40,
                    height: 4,
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      color: Colors.white24,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  const Text(
                    'اشتراک‌های من',
                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'برای تعویض، روی هر اشتراک بزن',
                    style: TextStyle(color: Colors.white38, fontSize: 11),
                  ),
                  const SizedBox(height: 12),
                  if (profiles.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 20),
                      child: Text('هنوز اشتراکی ذخیره نشده', style: TextStyle(color: Colors.white54)),
                    )
                  else
                    ConstrainedBox(
                      constraints: BoxConstraints(
                        maxHeight: MediaQuery.of(ctx).size.height * 0.45,
                      ),
                      child: ListView.separated(
                        shrinkWrap: true,
                        itemCount: profiles.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, i) {
                          final pr = profiles[i];
                          final u = pr['username'] ?? '';
                          final label = pr['label'] ?? u;
                          final active = u == savedUser;
                          return Material(
                            color: active
                                ? const Color(0xFF00E5FF).withOpacity(0.12)
                                : const Color(0xFF0D1424),
                            borderRadius: BorderRadius.circular(14),
                            child: ListTile(
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                                side: BorderSide(
                                  color: active ? const Color(0xFF00E5FF) : Colors.white10,
                                ),
                              ),
                              leading: Icon(
                                active
                                    ? Icons.check_circle_rounded
                                    : Icons.person_outline_rounded,
                                color: active ? const Color(0xFF00E5FF) : Colors.white54,
                              ),
                              title: Text(
                                label,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                ),
                              ),
                              subtitle: Text(
                                u,
                                style: const TextStyle(color: Colors.white38, fontSize: 11),
                              ),
                              trailing: IconButton(
                                icon: const Icon(
                                  Icons.delete_outline_rounded,
                                  color: Colors.redAccent,
                                  size: 20,
                                ),
                                onPressed: () async {
                                  Navigator.pop(ctx);
                                  await _deleteProfile(u);
                                  if (mounted) {
                                    _showToast('اشتراک از این دستگاه حذف شد', isError: false);
                                  }
                                },
                              ),
                              onTap: () async {
                                Navigator.pop(ctx);
                                if (active) return;
                                await _activateProfile(
                                  u,
                                  pr['password'] ?? '',
                                  fetch: true,
                                );
                                if (mounted) {
                                  _showToast('اشتراک فعال شد', isError: false);
                                }
                              },
                            ),
                          );
                        },
                      ),
                    ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF00E5FF),
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                      onPressed: () {
                        Navigator.pop(ctx);
                        _showAddProfileDialog();
                      },
                      icon: const Icon(Icons.add_rounded),
                      label: const Text(
                        'افزودن اشتراک',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _sectionLabel(String text) {
    return Padding(
      padding: EdgeInsets.only(right: 4, bottom: isJetTheme ? 3 : 6, top: isJetTheme ? 0 : 2),
      child: Align(
        alignment: Alignment.centerRight,
        child: Text(
          text,
          style: TextStyle(
            color: Colors.white54,
            fontSize: isJetTheme ? 10.5 : 11.5,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }

  Widget _buildConnectionModeSwitch() {
    Widget side({
      required String label,
      required IconData icon,
      required bool selected,
      required Color color,
      required VoidCallback onTap,
    }) {
      return Expanded(
        child: GestureDetector(
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: EdgeInsets.symmetric(vertical: isJetTheme ? 7 : 9),
            decoration: BoxDecoration(
              gradient: selected && isJetTheme
                  ? LinearGradient(colors: [color.withOpacity(0.6), color.withOpacity(0.22)])
                  : null,
              color: selected
                  ? (isJetTheme ? null : color.withOpacity(0.22))
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: selected ? color : Colors.transparent,
                width: selected && isJetTheme ? 1.6 : 1.2,
              ),
              boxShadow: selected && isJetTheme
                  ? [BoxShadow(color: color.withOpacity(0.4), blurRadius: 12)]
                  : null,
            ),
            child: Center(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(icon, size: 15, color: selected ? color : Colors.grey),
                  const SizedBox(width: 5),
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: selected ? Colors.white : Colors.grey,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _sectionLabel('نحوه اتصال'),
        Container(
          padding: const EdgeInsets.all(3),
          decoration: _dashCardDeco(borderColor: ui.accent, radius: 14),
          child: Row(
            children: [
              side(
                label: 'هوشمند',
                icon: Icons.auto_awesome_rounded,
                selected: connectionModeSmart,
                color: ui.accent,
                onTap: () async {
                  if (connectionModeSmart) return;
                  await _saveConnectionMode(smart: true);
                  if (mounted) {
                    _showToast('نحوه اتصال: هوشمند', isError: false);
                  }
                },
              ),
              const SizedBox(width: 4),
              side(
                label: 'دستی',
                icon: Icons.tune_rounded,
                selected: !connectionModeSmart,
                color: const Color(0xFFFFD54F),
                onTap: () async {
                  if (!connectionModeSmart) return;
                  if (_isRecovering) {
                    _recoveryGen++;
                    _isRecovering = false;
                  }
                  if (!_isVpnConnected) {
                    _userWantsConnected = false;
                    _stopHealthWatch();
                  }
                  await _saveConnectionMode(smart: false);
                  if (mounted) {
                    _showToast('نحوه اتصال: دستی', isError: false);
                  }
                },
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTunnelModeSwitch() {
    Widget chip({
      required String mode,
      required String label,
      required IconData icon,
      required Color color,
    }) {
      final on = tunnelMode == mode;
      return Expanded(
        child: GestureDetector(
          onTap: () => _saveTunnelMode(mode),
          onLongPress: mode == 'selected' ? () => _showSelectedAppsSheet() : null,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: EdgeInsets.symmetric(vertical: isJetTheme ? 6 : 8, horizontal: 2),
            decoration: BoxDecoration(
              gradient: on && isJetTheme
                  ? LinearGradient(colors: [color.withOpacity(0.55), color.withOpacity(0.2)])
                  : null,
              color: on ? (isJetTheme ? null : color.withOpacity(0.2)) : Colors.transparent,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: on ? color : Colors.transparent, width: on && isJetTheme ? 1.6 : 1.2),
              boxShadow: on && isJetTheme ? [BoxShadow(color: color.withOpacity(0.35), blurRadius: 10)] : null,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 15, color: on ? color : Colors.grey),
                const SizedBox(height: 3),
                Text(
                  label,
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.bold,
                    height: 1.15,
                    color: on ? Colors.white : Colors.grey,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _sectionLabel('تونل'),
        Container(
          padding: const EdgeInsets.all(4),
          decoration: _dashCardDeco(borderColor: ui.success, radius: 16),
          child: Row(
            children: [
              chip(mode: 'full', label: 'کل گوشی', icon: Icons.public, color: ui.accent),
              const SizedBox(width: 3),
              chip(mode: 'bypass_local', label: 'هوشمند', icon: Icons.home_work_outlined, color: ui.success),
              const SizedBox(width: 3),
              chip(mode: 'selected', label: 'انتخاب من', icon: Icons.checklist_rtl, color: const Color(0xFFFFD54F)),
            ],
          ),
        ),
        if (tunnelMode == 'selected')
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              'لمس طولانی «انتخاب من» = لیست اپ‌ها  ·  ${selectedVpnPackages.length} اپ',
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white38, fontSize: 10),
            ),
          ),
      ],
    );
  }

  Widget _buildTrafficCard() {
    final isConnected = _isVpnConnected;
    final downloadBytes = isConnected ? v2rayStatus.download : 0;
    final uploadBytes = isConnected ? v2rayStatus.upload : 0;

    final t = ui;
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 14, vertical: isJetTheme ? 7 : 10),
      decoration: _dashCardDeco(borderColor: t.accent, radius: 16),
      child: Row(
        children: [
          Expanded(
            child: Row(
              children: [
                Icon(Icons.arrow_downward_rounded, size: 18, color: t.success),
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
                Icon(Icons.arrow_upward_rounded, size: 18, color: t.accent),
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
    final t = ui;
    final jet = isJetTheme;

    return GestureDetector(
      onTap: isConnecting ? null : _toggleConnect,
      child: AnimatedBuilder(
        animation: Listenable.merge([_pulseAnimation, _rotateController]),
        builder: (context, child) {
          final scale = isConnected ? _pulseAnimation.value : 1.0;
          final primaryColor = isConnected ? t.success : t.connectIdleA;
          final secondaryColor = isConnected ? t.successDeep : t.connectIdleB;

          return Transform.scale(
            scale: scale,
            child: SizedBox(
              width: jet ? 142 : 165,
              height: jet ? 142 : 165,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // حلقه نئون بیرونی (تم جت)
                  if (jet)
                    Container(
                      width: 138,
                      height: 138,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: primaryColor.withOpacity(isConnected ? 0.55 : 0.35),
                          width: 2.5,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: primaryColor.withOpacity(0.45),
                            blurRadius: 28,
                            spreadRadius: 2,
                          ),
                          BoxShadow(
                            color: secondaryColor.withOpacity(0.25),
                            blurRadius: 40,
                            spreadRadius: 4,
                          ),
                        ],
                      ),
                    ),
                  if (isConnected || isConnecting)
                    Transform.rotate(
                      angle: _rotateController.value * 2 * math.pi,
                      child: Container(
                        width: jet ? 132 : 160,
                        height: jet ? 132 : 160,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: primaryColor.withOpacity(0.35),
                            width: 2,
                          ),
                          gradient: SweepGradient(
                            colors: [
                              Colors.transparent,
                              primaryColor.withOpacity(0.55),
                              Colors.transparent,
                              secondaryColor.withOpacity(0.35),
                              Colors.transparent,
                            ],
                          ),
                        ),
                      ),
                    ),
                  Container(
                    width: jet ? 128 : 135,
                    height: jet ? 128 : 135,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: primaryColor.withOpacity(isConnected ? 0.55 : 0.3),
                          blurRadius: isConnected ? (jet ? 22 : 40) : 24,
                          spreadRadius: isConnected ? (jet ? 3 : 8) : 2,
                        ),
                      ],
                    ),
                  ),
                  Container(
                    width: jet ? 100 : 105,
                    height: jet ? 100 : 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: isConnected
                            ? [t.success, t.successDeep]
                            : [t.connectIdleA, t.connectIdleB],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.white.withOpacity(jet ? 0.45 : 0.35),
                          offset: const Offset(-2, -2),
                          blurRadius: jet ? 8 : 5,
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
                                  isConnected
                                      ? (jet ? Icons.bolt_rounded : Icons.power_settings_new_rounded)
                                      : Icons.power_settings_new_rounded,
                                  size: jet ? 34 : 40,
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
                                  isConnected
                                      ? (jet ? 'متصل' : 'PROTECTED')
                                      : (jet ? 'آماده' : 'READY'),
                                  style: TextStyle(
                                    fontSize: jet ? 10 : 8,
                                    letterSpacing: jet ? 0.5 : 1.2,
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
    final t = ui;
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: t.bg,
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
                  errorBuilder: (_, __, ___) => Icon(Icons.rocket_launch_rounded, color: t.accent),
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
            icon: Icon(Icons.send_rounded, color: t.accent, size: 19),
            tooltip: 'کانال تلگرام',
            onPressed: () => _openTelegram(telegramChannelUrl),
          ),
          actions: [
            IconButton(
              icon: Icon(Icons.settings_rounded, color: t.accent, size: 21),
              tooltip: 'تنظیمات',
              onPressed: _openSettings,
            ),
            if (savedUser != null || profiles.isNotEmpty)
              IconButton(
                icon: Icon(Icons.people_alt_rounded, color: t.accent, size: 21),
                tooltip: 'اشتراک‌ها',
                onPressed: _showProfilesSheet,
              ),
            if (savedUser != null)
              IconButton(
                icon: isRefreshingServers
                    ? SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2, color: t.accent),
                      )
                    : Icon(Icons.sync_rounded, color: t.accent, size: 21),
                tooltip: 'بروزرسانی سرورها',
                onPressed: isRefreshingServers
                    ? null
                    : () => _fetchUserData(savedUser!, savedPass ?? '', isManualRefresh: true),
              ),
            if (savedUser != null)
              IconButton(
                icon: const Icon(Icons.logout_rounded, color: Colors.redAccent, size: 19),
                tooltip: 'خروج از نشست فعلی',
                onPressed: () async {
                  final prefs = await SharedPreferences.getInstance();
                  // فقط نشست فعال؛ پروفایل‌های ذخیره‌شده می‌مانند
                  await _clearActiveSession(prefs, stopVpn: true);
                  if (mounted) {
                    _userController.clear();
                    _passController.clear();
                  }
                },
              )
          ],
        ),
        body: Stack(
          fit: StackFit.expand,
          children: [
            if (isJetTheme) ...[
              DecoratedBox(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Color(0xFF2E1065),
                      Color(0xFF0F172A),
                      Color(0xFF020617),
                    ],
                    stops: [0.0, 0.45, 1.0],
                  ),
                ),
              ),
              Positioned(
                top: -80,
                left: -30,
                child: IgnorePointer(
                  child: Container(
                    width: 260,
                    height: 260,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(colors: [
                        const Color(0xFF8B5CF6).withOpacity(0.55),
                        Colors.transparent,
                      ]),
                    ),
                  ),
                ),
              ),
              Positioned(
                top: 120,
                right: -70,
                child: IgnorePointer(
                  child: Container(
                    width: 220,
                    height: 220,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(colors: [
                        const Color(0xFF06B6D4).withOpacity(0.35),
                        Colors.transparent,
                      ]),
                    ),
                  ),
                ),
              ),
              Positioned(
                bottom: -20,
                left: -40,
                child: IgnorePointer(
                  child: Container(
                    width: 280,
                    height: 180,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(100),
                      gradient: RadialGradient(colors: [
                        const Color(0xFF7C3AED).withOpacity(0.4),
                        Colors.transparent,
                      ]),
                    ),
                  ),
                ),
              ),
            ],
            isLoading
                ? Center(child: CircularProgressIndicator(color: t.accent))
                : (savedUser == null || userData == null)
                    ? _buildLoginView()
                    : _buildDashboardView(),
          ],
        ),
      ),
    );
  }


  // ---------- بروزرسانی پایدار APK ----------
  static const String _kUpPath = 'update_apk_path';
  static const String _kUpVer = 'update_apk_version';
  static const String _kUpCode = 'update_apk_version_code';
  static const String _kUpChannel = 'update_apk_channel';
  static const String _kUpSize = 'update_apk_size';
  static const String _kUpUrl = 'update_apk_url';

  Future<Directory> _updateStorageDir() async {
    // پایدارتر از temp؛ مخصوص اپ
    final support = await getApplicationSupportDirectory();
    final dir = Directory('${support.path}/updates');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  Future<Map<String, dynamic>?> _loadPendingUpdate() async {
    final prefs = await SharedPreferences.getInstance();
    final p = prefs.getString(_kUpPath);
    if (p == null || p.isEmpty) return null;
    final f = File(p);
    if (!await f.exists()) {
      await _clearPendingUpdatePrefs();
      return null;
    }
    final len = await f.length();
    final expected = prefs.getInt(_kUpSize) ?? 0;
    if (len < 1000 || (expected > 0 && len < expected * 0.95)) {
      // ناقص
      try {
        await f.delete();
      } catch (_) {}
      await _clearPendingUpdatePrefs();
      return null;
    }
    final code = prefs.getInt(_kUpCode) ?? 0;
    // اگر همین نسخه یا قدیمی‌تر نصب شده، فایل را پاک کن
    if (code > 0 && appVersionCode >= code) {
      try {
        await f.delete();
      } catch (_) {}
      await _clearPendingUpdatePrefs();
      return null;
    }
    return {
      'path': p,
      'version': prefs.getString(_kUpVer) ?? '',
      'version_code': code,
      'channel': prefs.getString(_kUpChannel) ?? apkChannel,
      'size': len,
      'url': prefs.getString(_kUpUrl) ?? '',
    };
  }

  Future<void> _clearPendingUpdatePrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kUpPath);
    await prefs.remove(_kUpVer);
    await prefs.remove(_kUpCode);
    await prefs.remove(_kUpChannel);
    await prefs.remove(_kUpSize);
    await prefs.remove(_kUpUrl);
  }

  Future<void> _savePendingUpdate({
    required String path,
    required String version,
    required int versionCode,
    required String channel,
    required int size,
    required String url,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kUpPath, path);
    await prefs.setString(_kUpVer, version);
    await prefs.setInt(_kUpCode, versionCode);
    await prefs.setString(_kUpChannel, channel);
    await prefs.setInt(_kUpSize, size);
    await prefs.setString(_kUpUrl, url);
  }

  Future<void> _deletePendingUpdateFile() async {
    final info = await _loadPendingUpdate();
    if (info != null) {
      try {
        final f = File(info['path'] as String);
        if (await f.exists()) await f.delete();
      } catch (_) {}
    }
    await _clearPendingUpdatePrefs();
  }

  /// پاکسازی فایل قدیمی بعد از نصب موفق (روی استارت)
  Future<void> _cleanupInstalledUpdateIfNeeded() async {
    try {
      await _loadPendingUpdate(); // داخلش اگر code <= appVersionCode پاک می‌کند
    } catch (_) {}
  }


  Future<void> _showUpToDateDialog() async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          backgroundColor: const Color(0xFF12261A),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
            side: BorderSide(color: const Color(0xFF00C853).withOpacity(0.45)),
          ),
          title: const Row(
            children: [
              Text('✅  ', style: TextStyle(fontSize: 22)),
              Expanded(
                child: Text(
                  'همه‌چیز به‌روز است',
                  style: TextStyle(
                    color: Color(0xFF69F0AE),
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ),
            ],
          ),
          content: Text(
            '🚀 نسخه $appVersion روی دستگاه شما نصب است و آخرین نسخه منتشرشده را دارید.\n\n'
            'نیازی به دانلود نیست — با خیال راحت ادامه بده.',
            style: const TextStyle(color: Colors.white70, fontSize: 13.5, height: 1.5),
          ),
          actions: [
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF00C853),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: () => Navigator.pop(ctx),
              child: const Text('باشه، عالی ✨'),
            ),
          ],
        ),
      ),
    );
  }

  /// بررسی بروزرسانی از سرور (کنترل با app_version.json → enabled)
  Future<void> _checkAppUpdate({bool silent = false}) async {
    try {
      // اول: اگر فایل محلی آماده است
      final pending = await _loadPendingUpdate();
      if (pending != null && !silent) {
        // متادیتای سرور را هم بگیر تا اگر نسخه جدیدتر آمد بگوییم
        Map<String, dynamic>? remote;
        try {
          final res = await http.get(Uri.parse(appUpdateMetaUrl)).timeout(const Duration(seconds: 12));
          if (res.statusCode == 200) {
            final data = json.decode(utf8.decode(res.bodyBytes));
            if (data is Map) remote = Map<String, dynamic>.from(data);
          }
        } catch (_) {}

        final localCode = pending['version_code'] as int;
        final remoteCode = int.tryParse('${remote?['version_code'] ?? 0}') ?? 0;
        final remoteNewer = remote != null && remote['enabled'] == true && remoteCode > localCode;

        if (!remoteNewer) {
          await _showPendingInstallDialog(pending);
          return;
        }
        // سرور جدیدتر است → ادامه می‌دهیم برای دانلود نسخه تازه (فایل قبلی بعداً جایگزین می‌شود)
      } else if (pending != null && silent) {
        // در حالت خاموش اگر فایل آماده است و نسخه بالاتر است، دیالوگ نصب نشان بده
        final localCode = pending['version_code'] as int;
        if (localCode > appVersionCode) {
          if (mounted) await _showPendingInstallDialog(pending);
          return;
        }
      }

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
          await _showUpToDateDialog();
        }
        return;
      }
      final remoteCode = int.tryParse('${data['version_code'] ?? 0}') ?? 0;
      final minCode = int.tryParse('${data['min_version_code'] ?? 0}') ?? 0;
      final force = data['force'] == true || (minCode > 0 && appVersionCode < minCode);
      if (remoteCode <= appVersionCode && !force) {
        if (!silent && mounted) {
          await _showUpToDateDialog();
        }
        return;
      }

      // اگر همان نسخه از قبل دانلود شده
      final again = await _loadPendingUpdate();
      if (again != null && (again['version_code'] as int) == remoteCode) {
        if (mounted) await _showPendingInstallDialog(again);
        return;
      }

      if (!mounted) return;
      final urls = (data['urls'] is Map)
          ? Map<String, dynamic>.from(data['urls'] as Map)
          : <String, dynamic>{};
      String channel = apkChannel;
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
        remoteCode: remoteCode,
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

  Future<void> _showPendingInstallDialog(Map<String, dynamic> pending) async {
    if (!mounted) return;
    final ver = pending['version']?.toString() ?? '?';
    final path = pending['path'] as String;
    final sizeMb = ((pending['size'] as int) / (1024 * 1024)).toStringAsFixed(1);
    final ch = pending['channel']?.toString() ?? apkChannel;

    final action = await showDialog<String>(
      context: context,
      barrierDismissible: true,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          backgroundColor: const Color(0xFF1A2332),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Text(
            'فایل بروزرسانی آماده است',
            style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
          ),
          content: Text(
            'نسخه دانلود‌شده: v$ver\n'
            'بسته: $ch\n'
            'حجم: $sizeMb مگابایت\n\n'
            'نیازی به دانلود مجدد نیست.\n'
            'می‌توانید نصب کنید یا فایل را حذف کنید.',
            style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.45),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, 'delete'),
              child: const Text('حذف فایل', style: TextStyle(color: Colors.redAccent)),
            ),
            TextButton(
              onPressed: () => Navigator.pop(ctx, 'later'),
              child: const Text('بعداً', style: TextStyle(color: Colors.white54)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF00C853),
                foregroundColor: Colors.white,
              ),
              onPressed: () => Navigator.pop(ctx, 'install'),
              child: const Text('نصب'),
            ),
          ],
        ),
      ),
    );

    if (action == 'delete') {
      await _deletePendingUpdateFile();
      if (mounted) _showToast('فایل بروزرسانی حذف شد');
    } else if (action == 'install') {
      final result = await OpenFilex.open(path, type: 'application/vnd.android.package-archive');
      debugPrint('OpenFilex pending: ${result.type} ${result.message}');
      if (result.type != ResultType.done && mounted) {
        _showToast('باز کردن نصب‌کننده ممکن نشد: ${result.message}');
      }
    }
  }

  Future<void> _showUpdateDialog({
    required String title,
    required String remoteVer,
    required int remoteCode,
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
                await _startApkDownload(
                  apkUrl: apkUrl,
                  remoteVer: remoteVer,
                  remoteCode: remoteCode,
                );
              },
              child: const Text('دانلود و نصب'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _startApkDownload({
    required String apkUrl,
    required String remoteVer,
    required int remoteCode,
  }) async {
    if (!mounted) return;

    final progress = ValueNotifier<double>(0);
    final status = ValueNotifier<String>('در حال آماده‌سازی…');
    var cancelled = false;
    http.Client? client;

    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return Directionality(
          textDirection: TextDirection.rtl,
          child: AlertDialog(
            backgroundColor: const Color(0xFF1A2332),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: const Text(
              'دانلود بروزرسانی',
              style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
            ),
            content: ValueListenableBuilder<String>(
              valueListenable: status,
              builder: (_, st, __) {
                return ValueListenableBuilder<double>(
                  valueListenable: progress,
                  builder: (_, p, __) {
                    final pct = (p * 100).clamp(0, 100).toStringAsFixed(0);
                    return Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(st, style: const TextStyle(color: Colors.white70, fontSize: 13)),
                        const SizedBox(height: 14),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: LinearProgressIndicator(
                            value: p > 0 && p < 1 ? p : (p >= 1 ? 1 : null),
                            minHeight: 8,
                            backgroundColor: Colors.white12,
                            color: const Color(0xFF00E5FF),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          p > 0 ? '$pct٪' : '…',
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: Color(0xFF00E5FF), fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 10),
                        const Text(
                          'فایل بعد از دانلود نگه داشته می‌شود.\n'
                          'اگر الان نصب نکردید، از «بررسی بروزرسانی» دوباره نصب کنید.',
                          style: TextStyle(color: Colors.white38, fontSize: 11.5, height: 1.4),
                        ),
                      ],
                    );
                  },
                );
              },
            ),
            actions: [
              TextButton(
                onPressed: () {
                  cancelled = true;
                  try {
                    client?.close();
                  } catch (_) {}
                  Navigator.pop(ctx);
                },
                child: const Text('انصراف', style: TextStyle(color: Colors.redAccent)),
              ),
            ],
          ),
        );
      },
    );

    File? file;
    try {
      status.value = 'در حال دانلود از سرور…';
      final dir = await _updateStorageDir();
      final safeVer = remoteVer.replaceAll(RegExp(r'[^0-9A-Za-z._-]'), '_');
      file = File('${dir.path}/jetvpn_${safeVer}_${apkChannel}.apk');

      // فایل‌های قدیمی آپدیت را پاک کن (نه در صورت انصراف ناقص همین فایل)
      try {
        await for (final entity in dir.list()) {
          if (entity is File && entity.path.endsWith('.apk') && entity.path != file.path) {
            try {
              await entity.delete();
            } catch (_) {}
          }
        }
      } catch (_) {}

      if (await file.exists()) {
        try {
          await file.delete();
        } catch (_) {}
      }

      client = http.Client();
      final req = http.Request('GET', Uri.parse(apkUrl));
      req.headers['User-Agent'] = 'JET-VPN-Updater/$appVersion';
      final streamed = await client.send(req).timeout(const Duration(minutes: 5));
      if (streamed.statusCode < 200 || streamed.statusCode >= 300) {
        throw Exception('HTTP ${streamed.statusCode}');
      }

      final total = streamed.contentLength ?? 0;
      final sink = file.openWrite();
      var received = 0;
      await for (final chunk in streamed.stream) {
        if (cancelled) break;
        sink.add(chunk);
        received += chunk.length;
        if (total > 0) {
          progress.value = (received / total).clamp(0.0, 1.0);
          status.value = 'در حال دانلود… ${(progress.value * 100).toStringAsFixed(0)}٪';
        } else {
          status.value = 'در حال دانلود… ${(received / (1024 * 1024)).toStringAsFixed(1)} مگابایت';
        }
      }
      await sink.close();
      try {
        client.close();
      } catch (_) {}
      client = null;

      if (cancelled) {
        try {
          if (await file.exists()) await file.delete();
        } catch (_) {}
        return;
      }

      final finalSize = await file.length();
      if (!await file.exists() || finalSize < 1000) {
        throw Exception('فایل دانلود ناقص است');
      }

      await _savePendingUpdate(
        path: file.path,
        version: remoteVer,
        versionCode: remoteCode,
        channel: apkChannel,
        size: finalSize,
        url: apkUrl,
      );

      progress.value = 1;
      status.value = 'دانلود کامل شد';

      if (mounted) {
        final nav = Navigator.of(context, rootNavigator: true);
        if (nav.canPop()) nav.pop();
      }

      if (!mounted) return;

      final goInstall = await showDialog<bool>(
        context: context,
        barrierDismissible: true,
        builder: (ctx) => Directionality(
          textDirection: TextDirection.rtl,
          child: AlertDialog(
            backgroundColor: const Color(0xFF1A2332),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: const Text(
              'آماده نصب',
              style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold),
            ),
            content: Text(
              'نسخه v$remoteVer دانلود و ذخیره شد.\n\n'
              'با «نصب» صفحه نصب اندروید باز می‌شود.\n'
              'اگر الان نخواهید، بعداً از «بررسی بروزرسانی» بدون دانلود مجدد نصب کنید.\n\n'
              'اگر پیام منبع ناشناس آمد:\n'
              '۱) جزئیات بیشتر\n'
              '۲) نصب در هر حال',
              style: const TextStyle(color: Colors.white70, fontSize: 13, height: 1.45),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('بعداً', style: TextStyle(color: Colors.white54)),
              ),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00C853),
                  foregroundColor: Colors.white,
                ),
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('نصب'),
              ),
            ],
          ),
        ),
      );

      if (goInstall == true) {
        final result = await OpenFilex.open(file.path, type: 'application/vnd.android.package-archive');
        debugPrint('OpenFilex: ${result.type} ${result.message}');
        if (result.type != ResultType.done && mounted) {
          _showToast('باز کردن نصب‌کننده ممکن نشد: ${result.message}');
        }
      } else if (mounted) {
        _showToast('فایل ذخیره شد — از بررسی بروزرسانی دوباره نصب کنید');
      }
    } catch (e) {
      debugPrint('in-app update error: $e');
      try {
        client?.close();
      } catch (_) {}
      // فایل ناقص را پاک کن؛ prefs را فقط اگر کامل ذخیره نشده بود
      try {
        if (file != null && await file.exists()) {
          final pending = await _loadPendingUpdate();
          if (pending == null || pending['path'] != file.path) {
            await file.delete();
          }
        }
      } catch (_) {}
      if (mounted) {
        final nav = Navigator.of(context, rootNavigator: true);
        if (nav.canPop()) nav.pop();
        _showToast('دانلود ناموفق بود — بعداً دوباره تلاش کن');
      }
    } finally {
      progress.dispose();
      status.dispose();
    }
  }

  Future<void> _changeAppPassword() async {
    final user = savedUser?.trim() ?? '';
    final pass = savedPass?.trim() ?? '';
    if (user.isEmpty || pass.isEmpty) {
      _showToast('ابتدا وارد حساب شو');
      return;
    }
    final controller = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1A2332),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Text('تغییر رمز ورود اپ', style: TextStyle(color: Colors.white, fontSize: 16)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'رمز جدید: ۵ تا ۸ حرف یا عدد انگلیسی\n(رمز اولیه معمولاً ۴ رقم بود)',
                style: TextStyle(color: Colors.white70, fontSize: 12.5, height: 1.4),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                obscureText: true,
                maxLength: 8,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'رمز جدید',
                  hintStyle: const TextStyle(color: Colors.white38),
                  counterStyle: const TextStyle(color: Colors.white38),
                  filled: true,
                  fillColor: const Color(0xFF0F1419),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('انصراف', style: TextStyle(color: Colors.white54)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF00C853)),
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('ذخیره', style: TextStyle(color: Colors.white)),
            ),
          ],
        );
      },
    );
    if (ok != true) return;
    final newPass = controller.text.trim();
    if (newPass.length < 5 || newPass.length > 8) {
      _showToast('رمز باید ۵ تا ۸ کاراکتر باشد');
      return;
    }
    if (!RegExp(r'^[A-Za-z0-9]+$').hasMatch(newPass)) {
      _showToast('فقط حرف و عدد انگلیسی');
      return;
    }
    _showToast('در حال ذخیره…');
    try {
      final uri = Uri.parse(
        'https://majid6064.ir/api.php'
        '?username=${Uri.encodeComponent(user)}'
        '&password=${Uri.encodeComponent(pass)}'
        '&action=change_password'
        '&new_password=${Uri.encodeComponent(newPass)}',
      );
      final res = await http.get(uri).timeout(const Duration(seconds: 12));
      final data = json.decode(utf8.decode(res.bodyBytes));
      if (data is Map && data['ok'] == true) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('saved_password', newPass);
        if (user.isNotEmpty) {
          await _upsertProfile(user, newPass);
        }
        if (mounted) {
          setState(() => savedPass = newPass);
          _passController.text = newPass;
        }
        _showToast('رمز عوض شد — در ربات هم «سرویس‌های من» را ببین');
      } else {
        _showToast((data is Map ? data['msg'] : null)?.toString() ?? 'تغییر رمز ناموفق');
      }
    } catch (_) {
      _showToast('خطا در ارتباط با سرور');
    }
  }


  Future<void> _saveConnectionMode({required bool smart, bool markChosen = true}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('pref_connection_mode_smart', smart);
    if (markChosen) {
      await prefs.setBool('pref_connection_mode_chosen', true);
    }
    if (mounted) {
      setState(() {
        connectionModeSmart = smart;
        if (markChosen) connectionModeChosen = true;
      });
    }
  }

  /// دیالوگ انتخاب مود (اولین ورود یا از تنظیمات)
  Future<void> _ensureConnectionModePicker() async {
    if (!mounted || connectionModeChosen || _modePickerLock) return;
    if (userData == null || isLoading) return;
    _modePickerLock = true;
    try {
      await Future.delayed(const Duration(milliseconds: 450));
      if (!mounted || connectionModeChosen) return;
      await _showConnectionModePicker(force: true);
    } finally {
      _modePickerLock = false;
    }
  }

  Future<void> _showConnectionModePicker({bool force = false}) async {
    if (!mounted) return;
    if (!force && connectionModeChosen) return;
    if (isLoading) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _ensureConnectionModePicker();
      });
      return;
    }
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) {
        return Directionality(
          textDirection: TextDirection.rtl,
          child: AlertDialog(
            backgroundColor: const Color(0xFF1A2332),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: const Text(
              'چطور می‌خواهی وصل شوی؟',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
              textAlign: TextAlign.center,
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'هر وقت خواستی از تنظیمات می‌توانی عوض کنی.',
                  style: TextStyle(color: Colors.white54, fontSize: 12),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                _modeChoiceCard(
                  ctx,
                  title: 'هوشمند',
                  subtitle: 'یک دکمه اتصال — اپ خودش بهترین سرور را انتخاب می‌کند',
                  icon: Icons.auto_awesome_rounded,
                  color: const Color(0xFF00E5FF),
                  onTap: () async {
                    Navigator.pop(ctx);
                    await _saveConnectionMode(smart: true);
                    if (mounted) _showToast('مود هوشمند فعال شد', isError: false);
                  },
                ),
                const SizedBox(height: 10),
                _modeChoiceCard(
                  ctx,
                  title: 'دستی',
                  subtitle: 'خودت سرور را ببین، پینگ بگیر و انتخاب کن',
                  icon: Icons.tune_rounded,
                  color: const Color(0xFFFFD54F),
                  onTap: () async {
                    Navigator.pop(ctx);
                    await _saveConnectionMode(smart: false);
                    if (mounted) _showToast('مود دستی فعال شد', isError: false);
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }


  Widget _settingsModeChip({
    required String label,
    required bool selected,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Material(
      color: selected ? color.withOpacity(0.18) : const Color(0xFF0D1526),
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: selected ? color : Colors.white12, width: selected ? 1.6 : 1),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: selected ? color : Colors.white54,
              fontWeight: FontWeight.w900,
              fontSize: 14,
            ),
          ),
        ),
      ),
    );
  }

  Widget _modeChoiceCard(
    BuildContext ctx, {
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Material(
      color: const Color(0xFF131B2E),
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: color.withOpacity(0.45)),
          ),
          child: Row(
            children: [
              Icon(icon, color: color, size: 28),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: TextStyle(color: color, fontWeight: FontWeight.w900, fontSize: 15)),
                    const SizedBox(height: 4),
                    Text(subtitle, style: const TextStyle(color: Colors.white70, fontSize: 11.5, height: 1.35)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String get _smartStatusLine {
    if (!connectionModeSmart) return '';
    if (_deviceNetworkDown) return 'اینترنت دستگاه قطع است — منتظر شبکه…';
    if (_isRecovering) return 'در حال بازیابی اتصال…';
    if (isRefreshingServers) return 'در حال بروزرسانی اشتراک…';
    if (isPingingAll) return 'در حال بررسی سرورها…';
    if (isConnecting) return 'در حال اتصال…';
    if (_isVpnConnected) return 'متصل — مدیریت سرور با اپ';
    if (_userWantsConnected && !_isVpnConnected) return 'در حال بررسی اتصال…';
    return '';
  }


  Widget _themeChoiceChip({
    required String id,
    required String title,
    required String subtitle,
    required bool selected,
    required VoidCallback onTap,
  }) {
    final t = JetUiTheme.byId(id);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
          decoration: BoxDecoration(
            color: selected ? t.accent.withOpacity(0.18) : t.card.withOpacity(0.9),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: selected ? t.accent : Colors.white12,
              width: selected ? 1.6 : 1,
            ),
          ),
          child: Column(
            children: [
              Container(
                width: 28,
                height: 10,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  gradient: LinearGradient(colors: [t.connectIdleA, t.connectIdleB]),
                ),
              ),
              const SizedBox(height: 8),
              Text(title, style: TextStyle(color: selected ? t.accent : Colors.white, fontWeight: FontWeight.bold, fontSize: 13.5)),
              const SizedBox(height: 2),
              Text(subtitle, style: const TextStyle(color: Colors.white38, fontSize: 10.5)),
            ],
          ),
        ),
      ),
    );
  }

  void _openSettings() {
    showModalBottomSheet(
      context: context,
      backgroundColor: ui.sheet,
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
                activeColor: ui.accent,
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
                      const Text(
                        'ظاهر برنامه',
                        style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 12.5),
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Expanded(
                            child: _themeChoiceChip(
                              id: 'classic',
                              title: 'کلاسیک',
                              subtitle: 'ظاهر آشنا',
                              selected: uiThemeId == 'classic',
                              onTap: () async {
                                await _saveUiTheme('classic');
                                setSheet(() {});
                              },
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: _themeChoiceChip(
                              id: 'jet',
                              title: 'جت',
                              subtitle: 'نئون و مسکات',
                              selected: uiThemeId == 'jet',
                              onTap: () async {
                                await _saveUiTheme('jet');
                                setSheet(() {});
                              },
                            ),
                          ),
                        ],
                      ),
                      const Divider(color: Colors.white12, height: 24),
                      const Text(
                        'اتصال و سرور',
                        style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 12.5),
                      ),

                      switchTile(
                        title: 'ترجیح پایداری',
                        subtitle: 'در اتصال هوشمند: پایدارتر به‌جای فقط کم‌پینگ',
                        value: preferStability,
                        onChanged: (v) async {
                          setState(() => preferStability = v);
                          await _savePrefBool('pref_prefer_stability', v);
                        },
                      ),
                      switchTile(
                        title: 'بروزرسانی سرور هنگام باز شدن',
                        subtitle: 'با هر ورود، لیست سرورها و وضعیت اشتراک تازه شود',
                        value: autoRefreshOnStart,
                        onChanged: (v) async {
                          setState(() => autoRefreshOnStart = v);
                          await _savePrefBool('pref_auto_refresh_on_start', v);
                        },
                      ),
                      switchTile(
                        title: 'پینگ هنگام باز شدن',
                        subtitle: 'با ورود به اپ پینگ گرفته شود (کمی کندتر)',
                        value: autoPingOnStart,
                        onChanged: (v) async {
                          setState(() => autoPingOnStart = v);
                          await _savePrefBool('pref_auto_ping_on_start', v);
                        },
                      ),
                      switchTile(
                        title: 'سرور قبلی را نگه دار',
                        subtitle: 'بعد از بروزرسانی خودکار سرور عوض نشود',
                        value: preferLastServer,
                        onChanged: (v) async {
                          setState(() => preferLastServer = v);
                          await _savePrefBool('pref_prefer_last_server', v);
                        },
                      ),
                      ListTile(
                        contentPadding: const EdgeInsets.symmetric(horizontal: 8),
                        leading: const Icon(Icons.checklist_rtl, color: Color(0xFFFFD54F)),
                        title: const Text('اپ‌های «انتخاب من»', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13.5)),
                        subtitle: Text(
                          tunnelMode == 'selected'
                              ? '${selectedVpnPackages.length} اپ برای VPN'
                              : 'برای حالت تونل «انتخاب من»',
                          style: const TextStyle(color: Colors.white54, fontSize: 11),
                        ),
                        trailing: const Icon(Icons.chevron_left, color: Colors.white38),
                        onTap: () {
                          Navigator.pop(ctx);
                          _showSelectedAppsSheet();
                        },
                      ),
                      ListTile(
                        contentPadding: const EdgeInsets.symmetric(horizontal: 8),
                        leading: const Icon(Icons.people_alt_rounded, color: Color(0xFF00E5FF)),
                        title: const Text('مدیریت اشتراک‌ها', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13.5)),
                        subtitle: Text(
                          profiles.isEmpty ? 'افزودن و تعویض چند اشتراک روی این گوشی' : '${profiles.length} اشتراک ذخیره شده',
                          style: const TextStyle(color: Colors.white54, fontSize: 11),
                        ),
                        trailing: const Icon(Icons.chevron_left, color: Colors.white38),
                        onTap: () {
                          Navigator.pop(ctx);
                          _showProfilesSheet();
                        },
                      ),
                      ListTile(
                        contentPadding: const EdgeInsets.symmetric(horizontal: 8),
                        leading: const Icon(Icons.password_rounded, color: Color(0xFFFFD54F)),
                        title: const Text('تغییر رمز ورود اپ', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13.5)),
                        subtitle: const Text('۵ تا ۸ کاراکتر · در سرویس‌های من ربات هم دیده می‌شود', style: TextStyle(color: Colors.white54, fontSize: 11)),
                        trailing: const Icon(Icons.chevron_left, color: Colors.white38),
                        onTap: () {
                          Navigator.pop(ctx);
                          _changeAppPassword();
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
                      if (!connectionModeSmart)
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
    final t = ui;
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
                  color: t.accent.withOpacity(0.35),
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
                  color: t.card,
                  child: Icon(Icons.rocket_launch_rounded, size: 50, color: t.accent),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text('JET VPN', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: t.text)),
          const SizedBox(height: 4),
          Text('ورود هوشمند به اشتراک پرسرعت', style: TextStyle(color: t.muted, fontSize: 12)),
          const SizedBox(height: 22),
          TextField(
            controller: _userController,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold, color: t.text),
            decoration: InputDecoration(
              hintText: 'نام کاربری (مثال: jet_user10)',
              hintStyle: TextStyle(color: t.muted.withOpacity(0.6), fontSize: 12.5),
              prefixIcon: Icon(Icons.fingerprint_rounded, color: t.accent),
              filled: true,
              fillColor: t.card,
              contentPadding: const EdgeInsets.symmetric(vertical: 14),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: t.cardBorder)),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: t.cardBorder)),
              focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: t.accent, width: 1.8)),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _passController,
            obscureText: _obscurePassword,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.bold, color: t.text),
            decoration: InputDecoration(
              hintText: 'رمز عبور اشتراک',
              hintStyle: TextStyle(color: t.muted.withOpacity(0.6), fontSize: 12.5),
              prefixIcon: Icon(Icons.lock_outline_rounded, color: t.accent),
              suffixIcon: IconButton(
                icon: Icon(
                  _obscurePassword ? Icons.visibility_off_rounded : Icons.visibility_rounded,
                  color: t.muted,
                  size: 20,
                ),
                onPressed: () {
                  setState(() {
                    _obscurePassword = !_obscurePassword;
                  });
                },
              ),
              filled: true,
              fillColor: t.card,
              contentPadding: const EdgeInsets.symmetric(vertical: 14),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: t.cardBorder)),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: t.cardBorder)),
              focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide(color: t.accent, width: 1.8)),
            ),
          ),
          const SizedBox(height: 18),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: t.accent,
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
          if (profiles.isNotEmpty) ...[
            const SizedBox(height: 18),
            const Align(
              alignment: Alignment.centerRight,
              child: Text('اشتراک‌های ذخیره‌شده', style: TextStyle(color: Colors.white54, fontSize: 12)),
            ),
            const SizedBox(height: 8),
            ...profiles.map((pr) {
              final u = pr['username'] ?? '';
              final label = pr['label'] ?? u;
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Material(
                  color: const Color(0xFF131B2E),
                  borderRadius: BorderRadius.circular(14),
                  child: ListTile(
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                      side: BorderSide(color: Colors.white.withOpacity(0.06)),
                    ),
                    dense: true,
                    leading: const Icon(Icons.person_rounded, color: Color(0xFF00E5FF), size: 20),
                    title: Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                    subtitle: Text(u, style: const TextStyle(color: Colors.white38, fontSize: 11)),
                    trailing: const Icon(Icons.login_rounded, color: Color(0xFF00E5FF), size: 20),
                    onTap: () => _activateProfile(u, pr['password'] ?? '', fetch: true),
                  ),
                ),
              );
            }),
          ],
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


  /// استایل کارت تم جت (نئون) — کلاسیک بدون تغییر
  BoxDecoration _dashCardDeco({Color? borderColor, double radius = 18}) {
    final t = ui;
    if (!isJetTheme) {
      return BoxDecoration(
        color: t.card,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      );
    }
    final bc = borderColor ?? t.accent;
    return BoxDecoration(
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: bc.withOpacity(0.55), width: 1.3),
      boxShadow: [
        BoxShadow(color: bc.withOpacity(0.18), blurRadius: 10, spreadRadius: 0),
        BoxShadow(color: Colors.black.withOpacity(0.25), blurRadius: 4, offset: const Offset(0, 2)),
      ],
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          t.card.withOpacity(0.98),
          const Color(0xFF1E1B4B).withOpacity(0.88),
        ],
      ),
    );
  }

  Widget _buildDashboardView() {
    final t = ui;
    final isConnected = _isVpnConnected;
    final currentServerName = serverList.isNotEmpty
        ? serverList[selectedServerIndex.clamp(0, serverList.length - 1)].name
        : 'سرور در دسترس';
    if (!connectionModeChosen) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _ensureConnectionModePicker();
      });
    }

    final jet = isJetTheme;
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: 14, vertical: jet ? 2 : 4),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              GestureDetector(
                onTap: _showProfilesSheet,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                  decoration: BoxDecoration(
                    color: t.card,
                    borderRadius: BorderRadius.circular(jet ? 16 : 12),
                    border: Border.all(color: t.accent.withOpacity(jet ? 0.55 : 0.35)),
                    boxShadow: jet
                        ? [
                            BoxShadow(
                              color: t.accent.withOpacity(0.2),
                              blurRadius: 12,
                            ),
                          ]
                        : null,
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.swap_horiz_rounded, size: 14, color: t.accent),
                      const SizedBox(width: 4),
                      Text(
                        'کاربر: ${userData!['username']}',
                        style: TextStyle(
                          color: t.accent,
                          fontWeight: FontWeight.bold,
                          fontSize: 11.5,
                        ),
                      ),
                      if (profiles.length > 1) ...[
                        const SizedBox(width: 4),
                        Text(
                          '(${profiles.length})',
                          style: const TextStyle(color: Colors.white38, fontSize: 10),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  color: t.card,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white.withOpacity(0.05)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.bolt_rounded, size: 15, color: activePing > 0 ? t.success : Colors.grey),
                    const SizedBox(width: 4),
                    Text(
                      activePing > 0 ? '$activePing ms' : (isConnected ? 'پینگ...' : 'آفلاین'),
                      style: TextStyle(color: activePing > 0 ? t.success : Colors.grey, fontWeight: FontWeight.bold, fontSize: 11),
                    ),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: jet ? 6 : 10),
          Container(
            padding: EdgeInsets.symmetric(horizontal: 14, vertical: jet ? 8 : 12),
            decoration: _dashCardDeco(borderColor: t.accentSoft),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildCompactBadge('باقیمانده', _getDisplayRemaining(), Icons.pie_chart_rounded, t.success),
                Container(width: 1, height: 32, color: Colors.white10),
                _buildCompactBadge('کل ترافیک', _getDisplayTotal(), Icons.data_usage_rounded, t.accent),
                Container(width: 1, height: 32, color: Colors.white10),
                _buildCompactBadge('مدت اعتبار', _getDisplayExpire(), Icons.timer_outlined, Colors.amberAccent),
              ],
            ),
          ),
          SizedBox(height: jet ? 5 : 8),
          _buildTrafficCard(),
          SizedBox(height: jet ? 5 : 8),
          _buildConnectionModeSwitch(),
          SizedBox(height: jet ? 5 : 8),
          _buildTunnelModeSwitch(),
          SizedBox(height: jet ? 5 : 8),
          if (!connectionModeSmart)
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    onTap: _openServerPicker,
                    borderRadius: BorderRadius.circular(16),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                      decoration: BoxDecoration(
                        color: t.card,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: t.accent.withOpacity(0.2)),
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
                      color: t.card,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: t.success.withOpacity(0.3)),
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
            )
          else
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: t.card,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: t.accent.withOpacity(0.15)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.auto_awesome_rounded, color: Color(0xFF00E5FF), size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      isConnecting || isPingingAll || isRefreshingServers
                          ? _smartStatusLine
                          : (isConnected ? 'مود هوشمند · سرور به‌صورت خودکار مدیریت می‌شود' : 'مود هوشمند · فقط اتصال را بزن'),
                      style: const TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 10),
          _buildNeonIpPill(),
          const SizedBox(height: 10),
          _build3DAnimatedButton(),
          const SizedBox(height: 8),
          Text(
            isConnected
                ? 'تونل: $tunnelModeLabel'
                : 'جهت اتصال لمس کنید',
            style: TextStyle(
              color: isConnected ? t.success : Colors.grey,
              fontWeight: FontWeight.bold,
              fontSize: 11.5,
            ),
          ),
          if (connectionModeSmart && _smartStatusLine.isNotEmpty && (isConnecting || isPingingAll || isRefreshingServers || _isRecovering || _deviceNetworkDown || (_userWantsConnected && !_isVpnConnected))) ...[
            const SizedBox(height: 8),
            Text(
              _smartStatusLine,
              textAlign: TextAlign.center,
              style: TextStyle(color: t.accent, fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ],
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
                      t.accent.withOpacity(0.15),
                      t.success.withOpacity(0.15),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: t.accent.withOpacity(0.3)),
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
