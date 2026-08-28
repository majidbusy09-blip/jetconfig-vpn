import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_v2ray/flutter_v2ray.dart';
import 'package:percent_indicator/circular_percent_indicator.dart';

void main() {
  runApp(const JetConfigApp());
}

const String appLogoUrl = 'https://majid6064.ir/logo.png';

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
      setState(() {
        v2rayStatus = status;
      });
      if (status.state == 'CONNECTED') {
        _checkActivePing();
      } else {
        setState(() => activePing = -1);
      }
    },
  );

  V2RayStatus v2rayStatus = V2RayStatus();
  final TextEditingController _userController = TextEditingController();

  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;
  late AnimationController _rotateController;

  bool isLoading = false;
  bool isConnecting = false;
  bool isPingingAll = false;
  int activePing = -1;

  Map<String, dynamic>? userData;
  String? savedUser;
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

    _loadSavedCredentials();
  }

  Future<void> _initCore() async {
    await flutterV2ray.initializeV2Ray();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _rotateController.dispose();
    _userController.dispose();
    super.dispose();
  }

  Future<void> _loadSavedCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    final user = prefs.getString('saved_username');
    if (user != null && user.isNotEmpty) {
      setState(() {
        savedUser = user;
        _userController.text = user;
      });
      _fetchUserData(user);
    }
  }

  Future<void> _fetchUserData(String username) async {
    setState(() => isLoading = true);
    try {
      final uri = Uri.parse('https://majid6064.ir/api.php?username=${Uri.encodeComponent(username)}');
      final res = await http.get(uri).timeout(const Duration(seconds: 12));
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        if (data['ok'] == true) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('saved_username', username);

          final List<dynamic> rawServers = data['servers'] ?? [];
          final parsed = rawServers.map((s) => ServerModel.fromJson(s)).toList();

          setState(() {
            userData = data;
            savedUser = username;
            serverList = parsed;
            selectedServerIndex = 0;
          });

          if (parsed.isNotEmpty) {
            _pingAllServers();
          }
        } else {
          _showToast(data['msg'] ?? 'نام کاربری یافت نشد');
        }
      }
    } catch (e) {
      _showToast('خطا در برقراری ارتباط با سرور');
    } finally {
      setState(() => isLoading = false);
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

  void _showToast(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg, textDirection: TextDirection.rtl),
      behavior: SnackBarBehavior.floating,
      backgroundColor: const Color(0xFF1E293B),
    ));
  }

  Future<void> _toggleConnect() async {
    if (v2rayStatus.state == 'CONNECTED') {
      await flutterV2ray.stopV2Ray();
      setState(() => activePing = -1);
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
        setState(() => isConnecting = false);
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
        proxyOnly: false,
      );
    } catch (e) {
      _showToast('خطا در برقراری اتصال: $e');
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
                        const Text('سرورهای هوشمند', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
                        Row(
                          children: [
                            TextButton.icon(
                              onPressed: () {
                                _sortServersByPing();
                                setSheetState(() {});
                              },
                              icon: const Icon(Icons.flash_on_rounded, size: 18, color: Colors.amberAccent),
                              label: const Text('مرتب‌سازی پینگ', style: TextStyle(color: Colors.amberAccent, fontSize: 12, fontWeight: FontWeight.bold)),
                            ),
                            TextButton.icon(
                              onPressed: isPingingAll
                                  ? null
                                  : () async {
                                      await _pingAllServers();
                                      setSheetState(() {});
                                    },
                              icon: isPingingAll
                                  ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.cyanAccent))
                                  : const Icon(Icons.refresh, size: 18, color: Colors.cyanAccent),
                              label: const Text('تست مجدد', style: TextStyle(color: Colors.cyanAccent, fontSize: 12)),
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
                          String pingText = 'تست نشده';
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
                              padding: const EdgeInsets.all(14),
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
                                  Icon(Icons.dns_rounded, color: isSel ? const Color(0xFF00E5FF) : Colors.grey),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(s.name, style: TextStyle(fontWeight: FontWeight.bold, color: isSel ? const Color(0xFF00E5FF) : Colors.white)),
                                        Text('${s.protocol} | پورت ${s.port}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                                      ],
                                    ),
                                  ),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: pingColor.withOpacity(0.15),
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Text(pingText, style: TextStyle(color: pingColor, fontSize: 12, fontWeight: FontWeight.bold)),
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
              width: 190,
              height: 190,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  if (isConnected || isConnecting)
                    Transform.rotate(
                      angle: _rotateController.value * 2 * math.pi,
                      child: Container(
                        width: 185,
                        height: 185,
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
                    width: 155,
                    height: 155,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: primaryColor.withOpacity(isConnected ? 0.5 : 0.25),
                          blurRadius: isConnected ? 40 : 25,
                          spreadRadius: isConnected ? 8 : 2,
                        ),
                      ],
                    ),
                  ),
                  Container(
                    width: 145,
                    height: 145,
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
                          offset: const Offset(0, 10),
                          blurRadius: 15,
                        )
                      ],
                    ),
                  ),
                  Container(
                    width: 122,
                    height: 122,
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
                          offset: const Offset(-3, -3),
                          blurRadius: 6,
                        ),
                        BoxShadow(
                          color: Colors.black.withOpacity(0.5),
                          offset: const Offset(4, 5),
                          blurRadius: 10,
                        ),
                      ],
                    ),
                    child: Center(
                      child: isConnecting
                          ? const SizedBox(
                              width: 42,
                              height: 42,
                              child: CircularProgressIndicator(
                                strokeWidth: 3.5,
                                color: Colors.white,
                              ),
                            )
                          : Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.power_settings_new_rounded,
                                  size: 48,
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
                                    fontSize: 9,
                                    letterSpacing: 1.5,
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
                  width: 32,
                  height: 32,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => const Icon(Icons.rocket_launch_rounded, color: Color(0xFF00E5FF)),
                ),
              ),
              const SizedBox(width: 10),
              const Text('JetConfig VPN', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 0.5)),
            ],
          ),
          centerTitle: true,
          backgroundColor: Colors.transparent,
          elevation: 0,
          actions: [
            if (savedUser != null)
              IconButton(
                icon: const Icon(Icons.logout_rounded, color: Colors.redAccent),
                onPressed: () async {
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.remove('saved_username');
                  if (v2rayStatus.state == 'CONNECTED') {
                    await flutterV2ray.stopV2Ray();
                  }
                  setState(() {
                    savedUser = null;
                    userData = null;
                    serverList.clear();
                  });
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
      padding: const EdgeInsets.symmetric(horizontal: 28.0, vertical: 30.0),
      child: Column(
        children: [
          const SizedBox(height: 10),
          Container(
            width: 130,
            height: 130,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(32),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF00E5FF).withOpacity(0.35),
                  blurRadius: 30,
                  spreadRadius: 4,
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(32),
              child: Image.network(
                appLogoUrl,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  color: const Color(0xFF131B2E),
                  child: const Icon(Icons.rocket_launch_rounded, size: 70, color: Color(0xFF00E5FF)),
                ),
              ),
            ),
          ),
          const SizedBox(height: 25),
          const Text('JetConfig VPN', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w900, color: Colors.white, letterSpacing: 1)),
          const SizedBox(height: 6),
          const Text('ورود هوشمند به اشتراک پرسرعت', style: TextStyle(color: Colors.grey, fontSize: 13)),
          const SizedBox(height: 35),
          TextField(
            controller: _userController,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
            decoration: InputDecoration(
              hintText: 'نام کاربری (مثال: user_93330195_778)',
              hintStyle: const TextStyle(color: Colors.white30, fontSize: 14),
              prefixIcon: const Icon(Icons.fingerprint_rounded, color: Color(0xFF00E5FF)),
              filled: true,
              fillColor: const Color(0xFF131B2E),
              contentPadding: const EdgeInsets.symmetric(vertical: 18),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(20),
                borderSide: BorderSide(color: Colors.white.withOpacity(0.08)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(20),
                borderSide: BorderSide(color: Colors.white.withOpacity(0.08)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(20),
                borderSide: const BorderSide(color: Color(0xFF00E5FF), width: 1.8),
              ),
            ),
          ),
          const SizedBox(height: 22),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00E5FF),
              foregroundColor: Colors.black,
              minimumSize: const Size(double.infinity, 54),
              elevation: 8,
              shadowColor: const Color(0xFF00E5FF).withOpacity(0.4),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
            ),
            onPressed: () {
              if (_userController.text.trim().isNotEmpty) {
                _fetchUserData(_userController.text.trim());
              }
            },
            child: const Text('ورود و بارگذاری سرورها', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _buildDashboardView() {
    final double percent = (userData!['total_gb'] != null && userData!['total_gb'] > 0)
        ? (userData!['used_gb'] / userData!['total_gb']).clamp(0.0, 1.0)
        : 0.0;
    final isConnected = v2rayStatus.state == 'CONNECTED';
    final currentServerName = serverList.isNotEmpty ? serverList[selectedServerIndex].name : 'سرور در دسترس';

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFF131B2E),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white.withOpacity(0.05)),
                ),
                child: Text('کاربر: ${userData!['username']}', style: const TextStyle(color: Color(0xFF00E5FF), fontWeight: FontWeight.bold)),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: const Color(0xFF131B2E),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white.withOpacity(0.05)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.bolt_rounded, size: 18, color: activePing > 0 ? const Color(0xFF00FFA3) : Colors.grey),
                    const SizedBox(width: 4),
                    Text(
                      activePing > 0 ? '$activePing ms' : (isConnected ? 'در حال پینگ...' : 'آفلاین'),
                      style: TextStyle(
                        color: activePing > 0 ? const Color(0xFF00FFA3) : Colors.grey,
                        fontWeight: FontWeight.bold,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          CircularPercentIndicator(
            radius: 80.0,
            lineWidth: 11.0,
            animation: true,
            percent: percent,
            center: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('${userData!['remaining_gb']} GB', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 22, color: Colors.white)),
                const Text('حجم باقیمانده', style: TextStyle(color: Colors.grey, fontSize: 11)),
              ],
            ),
            circularStrokeCap: CircularStrokeCap.round,
            progressColor: percent > 0.85 ? Colors.redAccent : const Color(0xFF00E5FF),
            backgroundColor: const Color(0xFF131B2E),
          ),
          const SizedBox(height: 18),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildInfoBadge('کل ترافیک', '${userData!['total_gb']} GB', Icons.data_usage_rounded),
              _buildInfoBadge('مدت اعتبار', '${userData!['expire_days']}', Icons.timer_outlined),
            ],
          ),
          const SizedBox(height: 20),
          InkWell(
            onTap: _openServerPicker,
            borderRadius: BorderRadius.circular(20),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF131B2E),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: const Color(0xFF00E5FF).withOpacity(0.2)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.public_rounded, color: Color(0xFF00E5FF)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('موقعیت سرور (لمس جهت تغییر)', style: TextStyle(fontSize: 11, color: Colors.grey)),
                        Text(currentServerName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white), overflow: TextOverflow.ellipsis),
                      ],
                    ),
                  ),
                  const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: Colors.grey),
                ],
              ),
            ),
          ),
          const SizedBox(height: 28),
          _build3DAnimatedButton(),
          const SizedBox(height: 14),
          Text(
            isConnected ? 'سیستم رمزنگاری فعال است' : 'جهت اتصال به شبکه لمس کنید',
            style: TextStyle(
              color: isConnected ? const Color(0xFF00FFA3) : Colors.grey,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoBadge(String label, String value, IconData icon) {
    return Container(
      width: 145,
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF131B2E),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Column(
        children: [
          Icon(icon, color: const Color(0xFF00E5FF), size: 22),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: Colors.grey, fontSize: 11)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white)),
        ],
      ),
    );
  }
}
