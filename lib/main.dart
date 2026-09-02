import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_v2ray/flutter_v2ray.dart';
import 'package:url_launcher/url_launcher.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const JetConfigApp());
}

// مشخصات نسخه
const String appVersion = 'v1.5.0';
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
      title: 'JetConfig VPN',
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
  late final FlutterV2ray flutterV2ray = FlutterV2ray(
    onStatusChanged: (status) {
      if (mounted) {
        setState(() {
          v2rayStatus = status;
        });
      }
      if (status.state == 'CONNECTED') {
        _checkActivePing();
        _fetchCurrentIp();
      } else {
        if (mounted) {
          setState(() {
            activePing = -1;
          });
        }
        _fetchCurrentIp();
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
  bool onlyFilteredApps = true;
  bool _obscurePassword = true;
  int activePing = -1;
  String currentIpAddress = '...';

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
  }

  Future<void> _initCore() async {
    await flutterV2ray.initializeV2Ray();
  }

  Future<void> _fetchCurrentIp() async {
    try {
      final res = await http.get(Uri.parse('https://api.ipify.org')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200 && mounted) {
        setState(() {
          currentIpAddress = res.body.trim();
        });
      }
    } catch (_) {
      if (mounted && currentIpAddress == '...') {
        setState(() => currentIpAddress = '---');
      }
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
    // حجم نامحدود
    if (total == null || total == 0 || total == 0.0 || total == '0') {
      return 'نامحدود';
    }
    // باقیمانده را با حداکثر دو رقم اعشار نشان بده
    final rem = remaining is num
        ? (remaining as num).toDouble()
        : double.tryParse('$remaining') ?? 0;
    if (rem <= 0) return '0 GB';
    if (rem < 1) return '${rem.toStringAsFixed(2)} GB';
    return '${rem.toStringAsFixed(rem == rem.roundToDouble() ? 0 : 1)} GB';
  }

  String _getDisplayTotal() {
    if (userData == null) return 'نامحدود';
    final total = userData!['total_gb'];
    if (total == null || total == 0 || total == 0.0 || total == '0') {
      return 'نامحدود';
    }
    final t = total is num ? (total as num).toDouble() : double.tryParse('$total') ?? 0;
    if (t < 1) return '${t.toStringAsFixed(2)} GB';
    return '${t.toStringAsFixed(t == t.roundToDouble() ? 0 : 1)} GB';
  }

  String _getDisplayExpire() {
    if (userData == null) return 'نامحدود';
    final expire = userData!['expire_days'];
    if (expire == null) return 'نامحدود';

    final expireStr = '$expire'.trim();
    if (expireStr.isEmpty ||
        expireStr == 'null' ||
        expireStr.contains('نامحدود') ||
        expireStr.contains('VIP') ||
        expireStr.toLowerCase().contains('unlimited')) {
      return 'نامحدود';
    }

    // اگر خود API گفته منقضی / پایان حجم، همان را نشان بده
    if (expireStr.contains('منقضی')) return 'منقضی شده';
    if (expireStr.contains('پایان حجم')) return 'پایان حجم';

    // رشته‌های آماده از API را مستقیم نمایش بده
    // مثال: "1 روز مانده" | "5 ساعت مانده" | "3 روز (شروع از اتصال)" | "شروع پس از اتصال"
    if (expireStr.contains('مانده') ||
        expireStr.contains('شروع') ||
        expireStr.contains('ساعت') ||
        expireStr.contains('دقیقه') ||
        expireStr.contains('روز')) {
      return expireStr;
    }

    // فقط عدد خام
    final intVal = int.tryParse(expireStr.replaceAll(RegExp(r'[^0-9\-]'), ''));
    if (intVal != null) {
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

    if (mounted) {
      setState(() {
        onlyFilteredApps = savedTunnelMode;
      });
    }

    if (user != null && user.isNotEmpty && pass.isNotEmpty) {
      if (mounted) {
        setState(() {
          savedUser = user;
          savedPass = pass;
          _userController.text = user;
          _passController.text = pass;
        });
      }
      _fetchUserData(user, pass);
    }
  }

  Future<void> _saveTunnelMode(bool val) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('only_filtered_apps', val);
    if (mounted) {
      setState(() {
        onlyFilteredApps = val;
      });
    }

    if (v2rayStatus.state == 'CONNECTED') {
      _showToast('در حال تغییر حالت شبکه...', isError: false);
      await _toggleConnect();
      await Future.delayed(const Duration(milliseconds: 300));
      await _toggleConnect();
    }
  }

  Future<void> _openTelegram(String url) async {
    if (url.isEmpty) return;
    try {
      final uri = Uri.parse(url);
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      try {
        final fallback = url.startsWith('tg://')
            ? url.replaceFirst('tg://', 'https://t.me/')
            : url;
        await launchUrl(Uri.parse(fallback), mode: LaunchMode.platformDefault);
      } catch (__) {
        // ignore
      }
    }
  }

  Future<void> _fetchUserData(String username, String password, {bool isManualRefresh = false}) async {
    setState(() => isLoading = true);
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

          if (mounted) {
            setState(() {
              userData = data;
              savedUser = username;
              savedPass = password;
              serverList = parsed;
              selectedServerIndex = 0;
            });
          }

          if (isManualRefresh) {
            _showToast('کانفیگ‌ها بروزرسانی شدند', isError: false);
          }

          if (parsed.isNotEmpty) {
            _pingAllServers();
          }
        } else {
          _showToast(data['msg'] ?? 'نام کاربری یا رمز عبور اشتباه است');
        }
      }
    } catch (e) {
      _showToast('خطا در اتصال به سرور');
    } finally {
      if (mounted) setState(() => isLoading = false);
    }
  }

  Future<int> _testTcpPing(String host, int port) async {
    if (host.isEmpty) return -2;
    final sw = Stopwatch()..start();
    try {
      final socket = await Socket.connect(host, port, timeout: const Duration(milliseconds: 2500));
      socket.destroy();
      sw.stop();
      return sw.elapsedMilliseconds;
    } catch (_) {
      return -2;
    }
  }

  void _sortServersByPing() {
    setState(() {
      final currentSelected = serverList.isNotEmpty ? serverList[selectedServerIndex] : null;
      serverList.sort((a, b) {
        if (a.ping > 0 && b.ping > 0) return a.ping.compareTo(b.ping);
        if (a.ping > 0) return -1;
        if (b.ping > 0) return 1;
        if (a.ping == -1 && b.ping == -2) return -1;
        if (a.ping == -2 && b.ping == -1) return 1;
        return 0;
      });

      if (currentSelected != null) {
        int newIdx = serverList.indexOf(currentSelected);
        selectedServerIndex = (newIdx != -1) ? newIdx : 0;
      }
    });
  }

  Future<void> _pingAllServers() async {
    if (serverList.isEmpty || isPingingAll) return;
    setState(() => isPingingAll = true);

    await Future.wait(serverList.map((s) async {
      final p = await _testTcpPing(s.host, s.port);
      if (mounted) {
        setState(() {
          s.ping = p;
        });
      }
    }));

    if (mounted) {
      _sortServersByPing();
      setState(() => isPingingAll = false);
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
    if (v2rayStatus.state == 'CONNECTED') {
      await flutterV2ray.stopV2Ray();
      if (mounted) setState(() => activePing = -1);
      _fetchCurrentIp();
      return;
    }

    if (serverList.isEmpty) {
      _showToast('هیچ سروری در لیست وجود ندارد');
      return;
    }

    setState(() => isConnecting = true);

    try {
      final bool permissionGranted = await flutterV2ray.requestPermission();
      if (!permissionGranted) {
        _showToast('مجوز اتصال VPN تایید نشد');
        if (mounted) setState(() => isConnecting = false);
        return;
      }

      final target = serverList[selectedServerIndex];
      String configString = target.config.trim();

      if (configString.startsWith('vless://') ||
          configString.startsWith('vmess://') ||
          configString.startsWith('trojan://') ||
          configString.startsWith('ss://')) {
        final parsedUrl = FlutterV2ray.parseFromURL(configString);
        configString = parsedUrl.getFullConfiguration();
      }

      await flutterV2ray.startV2Ray(
        remark: target.name,
        config: configString,
        blockedApps: onlyFilteredApps ? iranianAndBrowserPackages : null,
        proxyOnly: false,
      );
    } catch (e) {
      _showToast('خطا در برقراری اتصال');
    } finally {
      if (mounted) {
        setState(() => isConnecting = false);
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
                            if (s.ping < 250) pingColor = const Color(0xFF00FFA3);
                            else if (s.ping < 500) pingColor = Colors.orangeAccent;
                            else pingColor = Colors.redAccent;
                            pingText = '${s.ping} ms';
                          } else if (s.ping == -2) {
                            pingColor = Colors.redAccent;
                            pingText = 'تایم‌اوت';
                          }

                          return InkWell(
                            onTap: () {
                              setState(() {
                                selectedServerIndex = i;
                              });
                              Navigator.pop(ctx);
                              if (v2rayStatus.state == 'CONNECTED') {
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
    final isConnected = v2rayStatus.state == 'CONNECTED';
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
    final isConnected = v2rayStatus.state == 'CONNECTED';
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
    final isConnected = v2rayStatus.state == 'CONNECTED';

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
              const Text('JetConfig VPN', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16.5)),
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
            if (savedUser != null)
              IconButton(
                icon: const Icon(Icons.sync_rounded, color: Color(0xFF00E5FF), size: 21),
                tooltip: 'بروزرسانی کانفیگ‌ها',
                onPressed: () => _fetchUserData(savedUser!, savedPass ?? '', isManualRefresh: true),
              ),
            if (savedUser != null)
              IconButton(
                icon: const Icon(Icons.logout_rounded, color: Colors.redAccent, size: 19),
                tooltip: 'خروج از حساب',
                onPressed: () async {
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.remove('saved_username');
                  await prefs.remove('saved_password');
                  if (v2rayStatus.state == 'CONNECTED') {
                    await flutterV2ray.stopV2Ray();
                  }
                  if (mounted) {
                    setState(() {
                      savedUser = null;
                      savedPass = null;
                      userData = null;
                      serverList.clear();
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
          const Text('JetConfig VPN', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: Colors.white)),
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
    final isConnected = v2rayStatus.state == 'CONNECTED';
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
          const SizedBox(height: 12),
          Text(
            'JetConfig VPN • $appVersion',
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
