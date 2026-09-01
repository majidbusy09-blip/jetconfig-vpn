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

const String appVersion = 'v1.5.0';
const String appLogoUrl = 'https://majid6064.ir/logo.png';
const String telegramBotUrl = 'https://t.me/JetConfig1bot';
const String telegramChannelUrl = 'https://t.me/jetconfig11';

const List<String> iranianAndBrowserPackages = [
  'com.android.chrome', 'org.mozilla.firefox', 'com.sec.android.app.sbrowser',
  'com.opera.browser', 'com.opera.mini.native', 'com.brave.browser',
  'com.microsoft.emmx', 'app.nobitex', 'ir.nobitex.market', 'ir.wallex.app',
  'ir.tabdeal.app', 'com.ramzinex.app', 'ir.bitpin', 'com.abantether',
  'com.asanpardakht', 'ir.asanpardakht', 'com.ap.app', 'ir.mizan.hamrahcard',
  'com.mizan.hamrahcard', 'com.bpm.sekeh', 'com.sadadpsp.eva', 'ir.sep.qpay',
  'ir.pec.cpay', 'com.pec.top', 'ir.parsianbank.top', 'com.tara.app',
  'com.digikala.digipay', 'ir.digipay.app', 'com.snapppay.app', 'ir.bmi.bam.nativeweb',
  'ir.melli.bam', 'ir.bmi.baam', 'com.bmi.omad', 'ir.bmi.token', 'com.sadadpsp.bmi',
  'ir.bankmaskan.mobilebank', 'ir.bankmaskan.rayanmehr', 'ir.bankmaskan.hamrah',
  'com.maskan.mobilebank', 'ir.bankmellat.mobile', 'com.mellat.mobile',
  'ir.tejaratbank.mobilebank', 'com.tejarat.mbank', 'com.saderat.mb', 'ir.bsi.mobilebank',
  'ir.samanpr.blu', 'ir.blubank', 'ir.sb24.mobilbank', 'com.saman.mobile',
  'ir.banksepah.mobilebank', 'ir.omidbank.app', 'ir.bpi.mobilebank', 'com.pasargad.mobile',
  'ir.parsianbank.mobilebank', 'ir.agribank.mobile', 'ir.bankrefah.mobilebank',
  'ir.citybank.mobilebank', 'ir.day24.mobilebank', 'ir.sina.mobile', 'ir.ayandeh.hamrah',
  'ir.postbank.mobile', 'ir.ttbank.mobilebank', 'cab.snapp.passenger', 'com.snapp.passenger',
  'cab.snapp.driver', 'ir.tapsi.cab', 'com.digikala.mobile', 'ir.divar', 'ir.sheypoor.mobile',
  'org.neshan.maps', 'ir.balad.navigation', 'com.torob', 'ir.basalam.app', 'ir.alibaba.travel',
  'ir.mtnirancell.myirancell', 'ir.mci.ecareapp', 'ir.rightel.ecare', 'ir.eitaa.messenger',
  'ir.rubika.app', 'ir.resaneh.rubika', 'ir.ble.messenger', 'ir.gov.my', 'ir.police.my',
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
        if (mounted) setState(() => activePing = -1);
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

    _pulseController = AnimationController(vsync: this, duration: const Duration(milliseconds: 1800))..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 0.96, end: 1.07).animate(CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut));
    _rotateController = AnimationController(vsync: this, duration: const Duration(seconds: 8))..repeat();

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
        setState(() => currentIpAddress = res.body.trim());
      }
    } catch (_) {
      if (mounted && currentIpAddress == '...') setState(() => currentIpAddress = '---');
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
    int bytes = bytesInput is int ? bytesInput : (bytesInput is String ? int.tryParse(bytesInput) ?? 0 : 0);
    if (bytes <= 0) return '0 KB';
    const suffixes = ['B', 'KB', 'MB', 'GB', 'TB'];
    int i = (math.log(bytes) / math.log(1024)).floor();
    if (i >= suffixes.length) i = suffixes.length - 1;
    double size = bytes / math.pow(1024, i);
    return '${size.toStringAsFixed(size < 10 ? 1 : 0)} ${suffixes[i]}';
  }

  String _getDisplayRemaining() {
    if (userData == null) return 'نامحدود';
    final total = userData!['total_gb'];
    final remaining = userData!['remaining_gb'];
    if (total == null || total == 0 || total == '0') return 'نامحدود';
    return '${remaining ?? 0} GB';
  }

  String _getDisplayTotal() {
    if (userData == null) return 'نامحدود';
    final total = userData!['total_gb'];
    if (total == null || total == 0 || total == '0') return 'نامحدود';
    return '$total GB';
  }

  String _getDisplayExpire() {
    if (userData == null) return 'نامحدود';
    final expire = userData!['expire_days'];
    final expireStr = '$expire'.trim();

    if (expire == null || expireStr == 'null' || expireStr.isEmpty || expireStr.contains('نامحدود') || expireStr.contains('VIP') || expireStr.contains('Unlimited') ||
        ((total == 0 || total == null) && (expireStr == '0' || expireStr == '0 روز' || expireStr == 'منقضی شده'))) {
      return 'نامحدود';
    }

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
          Icon(isError ? Icons.error_outline_rounded : Icons.check_circle_outline_rounded,
              color: isError ? const Color(0xFFFF5252) : const Color(0xFF00FFA3),
              size: 20),
          const SizedBox(width: 10),
          Expanded(child: Text(msg, textDirection: TextDirection.rtl,
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13))),
        ],
      ),
      behavior: SnackBarBehavior.floating,
      backgroundColor: const Color(0xFF1E293B),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: isError ? const Color(0xFFFF5252).withOpacity(0.6) : const Color(0xFF00E5FF).withOpacity(0.6), width: 1.3)),
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      duration: const Duration(seconds: 3),
    ));
  }

  Future<void> _loadSavedPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    final user = prefs.getString('saved_username');
    final pass = prefs.getString('saved_password') ?? '';
    final savedTunnelMode = prefs.getBool('only_filtered_apps') ?? true;

    if (mounted) setState(() => onlyFilteredApps = savedTunnelMode);

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

  // ==================== تابع باز کردن تلگرام (اصلاح‌شده و تمیز) ====================
  Future<void> _openTelegram(String url) async {
    if (url.isEmpty) return;

    try {
      final uri = Uri.parse(url);
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      // fallback
      await launchUrl(Uri.parse(url.startsWith('tg://') ? url.replaceFirst('tg://', 'https://t.me/') : url),
          mode: LaunchMode.platformDefault);
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

          if (isManualRefresh) _showToast('کانفیگ‌ها بروزرسانی شدند', isError: false);

          if (parsed.isNotEmpty) _pingAllServers();
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
      if (mounted) setState(() => s.ping = p);
    }));

    if (mounted) {
      _sortServersByPing();
      setState(() => isPingingAll = false);
    }
  }

  Future<void> _checkActivePing() async {
    try {
      final delay = await flutterV2ray.getConnectedServerDelay();
      if (mounted) setState(() => activePing = delay);
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
      if (mounted) setState(() => isConnecting = false);
    }
  }

  void _openServerPicker() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF131B2E),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Directionality(
              textDirection: TextDirection.rtl,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
                child: Column(
                  mainAxisSize: mainAxisSize.min,
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
                              label: const Text('تست مجدر', style: TextStyle(color: Colors.cyanAccent, fontSize: 11.5)),
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
                                border: Border.all(color: isSel ? const Color(0xFF00E5FF) : Colors.white.withOpacity(0.05), width: 1.5),
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
                                    decoration: BoxDecoration(color: pingColor.withOpacity(0.15), borderRadius: BorderRadius.circular(10)),
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
          BoxShadow(color: glowColor.withOpacity(isConnected ? 0.25 : 0.12), blurRadius: 10, spreadRadius: 1),
        ],
      ),
      child: Text(
        currentIpAddress,
        style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: Colors.white),
        textAlign: TextAlign.center,
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
                          border: Border.all(color: primaryColor.withOpacity(0.35), width: 2),
                          gradient: SweepGradient(colors: [Colors.transparent, primaryColor.withOpacity(0.4), Colors.transparent]),
                        ),
                      ),
                    ),
                  Container(
                    width: 135,
                    height: 135,
                    decoration: BoxDecoration(shape: BoxShape.circle, boxShadow: [
                      BoxShadow(color: primaryColor.withOpacity(isConnected ? 0.5 : 0.25), blurRadius: isConnected ? 35 : 20, spreadRadius: isConnected ? 6 : 1),
                    ]),
                  ),
                  Container(
                    width: 125,
                    height: 125,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: [
                        Colors.white.withOpacity(0.2),
                        const Color(0xFF1E293B),
                        Colors.black.withOpacity(0.8),
                      ]),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withOpacity(0.6), offset: const Offset(0, 8), blurRadius: 12),
                      ],
                    ),
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset: const Offset(3, 4), blurRadius: 8),
                    ],
                  ),
                  Container(
                    width: 105,
                    height: 105,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(begin: Alignment.topLeft, end: Alignment.bottomRight, colors: isConnected
                          ? [const Color(0xFF00FFA3), const Color(0xFF008B74)]
                          : [const Color(0xFF00D2FF), const Color(0xFF0052D4)],
                    ),
                    boxShadow: [
                      BoxShadow(color: Colors.white.withOpacity(0.35), offset: const Offset(-2, -2), blurRadius: 5),
                      BoxShadow(color: Colors.black.withOpacity(0.5), offset:
