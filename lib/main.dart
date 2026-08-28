import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_v2ray/flutter_v2ray.dart';
import 'package:percent_indicator/circular_percent_indicator.dart';

void main() {
  runApp(const JetConfigApp());
}

class ServerItem {
  final String rawUrl;
  final String name;
  final String host;
  final int port;
  final String protocol;
  int ping; // -1: تست نشده, -2: تایم‌اوت, >0: میلی‌ثانیه

  ServerItem({
    required this.rawUrl,
    required this.name,
    required this.host,
    required this.port,
    required this.protocol,
    this.ping = -1,
  });

  static ServerItem fromUrl(String url) {
    url = url.trim();
    if (url.startsWith('vless://') || url.startsWith('trojan://') || url.startsWith('ss://')) {
      try {
        final uri = Uri.parse(url);
        String remark = 'سرور پرسرعت';
        if (uri.hasFragment && uri.fragment.isNotEmpty) {
          remark = Uri.decodeComponent(uri.fragment);
        } else if (uri.host.isNotEmpty) {
          remark = uri.host;
        }
        return ServerItem(
          rawUrl: url,
          name: remark,
          host: uri.host,
          port: uri.port > 0 ? uri.port : 443,
          protocol: uri.scheme.toUpperCase(),
        );
      } catch (_) {}
    } else if (url.startsWith('vmess://')) {
      try {
        String b64 = url.substring(8).trim();
        int pad = b64.length % 4;
        if (pad > 0) b64 += '=' * (4 - pad);
        b64 = b64.replaceAll('-', '+').replaceAll('_', '/');
        final decoded = utf8.decode(base64.decode(b64));
        final map = json.decode(decoded);
        return ServerItem(
          rawUrl: url,
          name: map['ps'] ?? 'سرور VMess',
          host: map['add'] ?? '',
          port: int.tryParse('${map['port']}') ?? 443,
          protocol: 'VMESS',
        );
      } catch (_) {}
    }
    return ServerItem(
      rawUrl: url,
      name: 'سرور JetConfig',
      host: '',
      port: 443,
      protocol: 'V2RAY',
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
        scaffoldBackgroundColor: const Color(0xFF0F172A),
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

class _MainVpnScreenState extends State<MainVpnScreen> {
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
  final TextEditingController _passController = TextEditingController();

  bool isPasswordVisible = false;
  bool isLoading = false;
  bool isConnecting = false;
  bool isPingingAll = false;
  int activePing = -1;

  Map<String, dynamic>? userData;
  String? savedUser;
  List<ServerItem> serverList = [];
  int selectedServerIndex = 0;

  @override
  void initState() {
    super.initState();
    flutterV2ray.initializeV2Ray();
    _loadSavedCredentials();
  }

  Future<void> _loadSavedCredentials() async {
    final prefs = await SharedPreferences.getInstance();
    final user = prefs.getString('saved_username');
    final pass = prefs.getString('saved_password') ?? '';
    if (user != null && user.isNotEmpty) {
      setState(() {
        savedUser = user;
        _userController.text = user;
        _passController.text = pass;
      });
      _fetchUserData(user, pass);
    }
  }

  Future<List<String>> _fetchConfigsFromSubUrl(String subUrl) async {
    try {
      final res = await http.get(Uri.parse(subUrl), headers: {
        'User-Agent': 'v2rayNG/1.8.5',
      }).timeout(const Duration(seconds: 12));

      if (res.statusCode == 200) {
        String body = res.body.trim();
        String decoded = '';
        String clean = body.replaceAll('\n', '').replaceAll('\r', '').replaceAll(' ', '').trim();
        clean = clean.replaceAll('-', '+').replaceAll('_', '/');
        while (clean.length % 4 != 0) {
          clean += '=';
        }
        try {
          decoded = utf8.decode(base64.decode(clean));
        } catch (_) {
          decoded = body;
        }

        final lines = LineSplitter.split(decoded)
            .map((e) => e.trim())
            .where((e) => e.startsWith('vless://') || e.startsWith('vmess://') || e.startsWith('trojan://') || e.startsWith('ss://'))
            .toList();

        return lines;
      }
    } catch (_) {}
    return [];
  }

  Future<void> _fetchUserData(String username, [String password = '']) async {
    setState(() => isLoading = true);
    try {
      final uri = Uri.parse('https://majid6064.ir/api.php?username=${Uri.encodeComponent(username)}&password=${Uri.encodeComponent(password)}');
      final res = await http.get(uri).timeout(const Duration(seconds: 12));
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        if (data['ok'] == true) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('saved_username', username);
          await prefs.setString('saved_password', password);

          List<String> rawConfigs = List<String>.from(data['configs'] ?? []);

          // دانلود مستقیم روی گوشی در صورت مسدود بودن ارتباط در هاست
          if (rawConfigs.isEmpty && data['sub_url'] != null && data['sub_url'].toString().isNotEmpty) {
            rawConfigs = await _fetchConfigsFromSubUrl(data['sub_url']);
          }

          List<ServerItem> parsed = rawConfigs.map((c) => ServerItem.fromUrl(c)).toList();

          setState(() {
            userData = data;
            savedUser = username;
            serverList = parsed;
            selectedServerIndex = 0;
          });

          if (parsed.isNotEmpty) {
            _pingAllServers();
          } else {
            _showToast('اطلاعات دریافت شد اما سروری در اشتراک یافت نشد');
          }
        } else {
          _showToast(data['msg'] ?? 'خطا در احراز هویت');
        }
      } else {
        _showToast('خطا در ارتباط با سرور (${res.statusCode})');
      }
    } catch (e) {
      _showToast('خطا در اتصال به سرور');
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
      backgroundColor: const Color(0xFF334155),
    ));
  }

  Future<void> _toggleConnect() async {
    if (v2rayStatus.state == 'CONNECTED') {
      await flutterV2ray.stopV2Ray();
      setState(() => activePing = -1);
      return;
    }

    if (serverList.isEmpty) {
      _showToast('هیچ سرور فعالی یافت نشد');
      return;
    }

    if (await flutterV2ray.requestPermission()) {
      setState(() => isConnecting = true);
      try {
        final target = serverList[selectedServerIndex];
        final v2rayURL = FlutterV2ray.parseFromURL(target.rawUrl);
        await flutterV2ray.startV2Ray(
          remark: target.name,
          config: v2rayURL.getFullConfiguration(),
          proxyOnly: false,
        );
      } catch (e) {
        _showToast('خطا در اجرای هسته اتصال');
      } finally {
        setState(() => isConnecting = false);
      }
    }
  }

  void _openServerPicker() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E293B),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Directionality(
              textDirection: TextDirection.rtl,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('انتخاب سرور', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
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
                          label: const Text('تست مجدد پینگ', style: TextStyle(color: Colors.cyanAccent)),
                        ),
                      ],
                    ),
                    const Divider(color: Colors.white12),
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
                            if (s.ping < 250) pingColor = Colors.greenAccent;
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
                                color: isSel ? Colors.cyanAccent.withOpacity(0.12) : const Color(0xFF0F172A),
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(
                                  color: isSel ? Colors.cyanAccent : Colors.transparent,
                                  width: 1.5,
                                ),
                              ),
                              child: Row(
                                children: [
                                  Icon(Icons.dns_rounded, color: isSel ? Colors.cyanAccent : Colors.grey),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(s.name, style: TextStyle(fontWeight: FontWeight.bold, color: isSel ? Colors.cyanAccent : Colors.white)),
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

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('JetConfig VPN 🚀', style: TextStyle(fontWeight: FontWeight.bold)),
          centerTitle: true,
          backgroundColor: Colors.transparent,
          elevation: 0,
          actions: [
            if (savedUser != null)
              IconButton(
                icon: const Icon(Icons.logout, color: Colors.redAccent),
                onPressed: () async {
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.remove('saved_username');
                  await prefs.remove('saved_password');
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
            ? const Center(child: CircularProgressIndicator(color: Colors.cyanAccent))
            : (savedUser == null || userData == null)
                ? _buildLoginView()
                : _buildDashboardView(),
      ),
    );
  }

  Widget _buildLoginView() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        children: [
          const SizedBox(height: 30),
          const Icon(Icons.shield_rounded, size: 85, color: Colors.cyanAccent),
          const SizedBox(height: 20),
          const Text('ورود به حساب کاربری', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          const Text('اطلاعات اشتراک خود را وارد کنید', style: TextStyle(color: Colors.grey)),
          const SizedBox(height: 35),
          TextField(
            controller: _userController,
            textAlign: TextAlign.center,
            decoration: InputDecoration(
              hintText: 'نام کاربری (مثال: user_93330195_778)',
              prefixIcon: const Icon(Icons.person, color: Colors.cyanAccent),
              filled: true,
              fillColor: const Color(0xFF1E293B),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _passController,
            obscureText: !isPasswordVisible,
            textAlign: TextAlign.center,
            decoration: InputDecoration(
              hintText: 'رمز عبور (اختیاری)',
              prefixIcon: const Icon(Icons.lock, color: Colors.cyanAccent),
              suffixIcon: IconButton(
                icon: Icon(isPasswordVisible ? Icons.visibility : Icons.visibility_off, color: Colors.grey),
                onPressed: () => setState(() => isPasswordVisible = !isPasswordVisible),
              ),
              filled: true,
              fillColor: const Color(0xFF1E293B),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
            ),
          ),
          const SizedBox(height: 25),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.cyanAccent,
              foregroundColor: Colors.black,
              minimumSize: const Size(double.infinity, 52),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            onPressed: () {
              if (_userController.text.trim().isNotEmpty) {
                _fetchUserData(_userController.text.trim(), _passController.text.trim());
              }
            },
            child: const Text('ورود و دریافت سرورها', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
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
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(color: const Color(0xFF1E293B), borderRadius: BorderRadius.circular(16)),
                child: Text('کاربر: ${userData!['username']}', style: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold)),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(color: const Color(0xFF1E293B), borderRadius: BorderRadius.circular(16)),
                child: Row(
                  children: [
                    Icon(Icons.bolt, size: 18, color: activePing > 0 ? Colors.greenAccent : Colors.grey),
                    const SizedBox(width: 4),
                    Text(
                      activePing > 0 ? '$activePing ms' : (isConnected ? 'در حال پینگ...' : 'آفلاین'),
                      style: TextStyle(color: activePing > 0 ? Colors.greenAccent : Colors.grey, fontWeight: FontWeight.bold, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          CircularPercentIndicator(
            radius: 85.0,
            lineWidth: 12.0,
            animation: true,
            percent: percent,
            center: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('${userData!['remaining_gb']} GB', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 22)),
                const Text('حجم باقیمانده', style: TextStyle(color: Colors.grey, fontSize: 11)),
              ],
            ),
            circularStrokeCap: CircularStrokeCap.round,
            progressColor: percent > 0.85 ? Colors.redAccent : Colors.cyanAccent,
            backgroundColor: const Color(0xFF1E293B),
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildInfoBadge('کل حجم', '${userData!['total_gb']} GB', Icons.data_usage),
              _buildInfoBadge('اعتبار', '${userData!['expire_days']}', Icons.timer_outlined),
            ],
          ),
          const SizedBox(height: 24),
          InkWell(
            onTap: _openServerPicker,
            borderRadius: BorderRadius.circular(18),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: Colors.white12),
              ),
              child: Row(
                children: [
                  const Icon(Icons.public, color: Colors.cyanAccent),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('سرور انتخابی (لمس برای تغییر)', style: TextStyle(fontSize: 11, color: Colors.grey)),
                        Text(currentServerName, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14), overflow: TextOverflow.ellipsis),
                      ],
                    ),
                  ),
                  const Icon(Icons.arrow_forward_ios, size: 14, color: Colors.grey),
                ],
              ),
            ),
          ),
          const SizedBox(height: 30),
          GestureDetector(
            onTap: isConnecting ? null : _toggleConnect,
            child: Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  colors: isConnected
                      ? [Colors.greenAccent, Colors.teal]
                      : [Colors.cyanAccent, Colors.blueAccent],
                ),
                boxShadow: [
                  BoxShadow(
                    color: (isConnected ? Colors.teal : Colors.cyanAccent).withOpacity(0.35),
                    blurRadius: 25,
                    spreadRadius: 5,
                  )
                ],
              ),
              child: Center(
                child: isConnecting
                    ? const CircularProgressIndicator(color: Colors.black)
                    : Icon(
                        Icons.power_settings_new_rounded,
                        size: 55,
                        color: isConnected ? Colors.black : Colors.black87,
                      ),
              ),
            ),
          ),
          const SizedBox(height: 14),
          Text(
            isConnected ? 'متصل شد (امن)' : 'جهت اتصال لمس کنید',
            style: TextStyle(color: isConnected ? Colors.greenAccent : Colors.grey, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoBadge(String label, String value, IconData icon) {
    return Container(
      width: 140,
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Icon(icon, color: Colors.cyanAccent, size: 22),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(color: Colors.grey, fontSize: 11)),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
        ],
      ),
    );
  }
}
