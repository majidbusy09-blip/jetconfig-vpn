import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_v2ray/flutter_v2ray.dart';
import 'package:percent_indicator/circular_percent_indicator.dart';

void main() {
  runApp(const JetConfigApp());
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
    },
  );

  var v2rayStatus = ValueNotifier<V2RayStatus>(V2RayStatus());
  final TextEditingController _userController = TextEditingController();

  bool isLoading = false;
  Map<String, dynamic>? userData;
  String? savedUser;

  @override
  void initState() {
    super.initState();
    flutterV2ray.initializeV2Ray();
    _loadSavedUser();
  }

  Future<void> _loadSavedUser() async {
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
      final res = await http.get(Uri.parse('https://majid6064.ir/api.php?username=$username'));
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        if (data['ok'] == true) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('saved_username', username);
          setState(() {
            userData = data;
            savedUser = username;
          });
        } else {
          _showToast(data['msg'] ?? 'خطا در احراز هویت');
        }
      }
    } catch (e) {
      _showToast('خطا در اتصال به سرور');
    } finally {
      setState(() => isLoading = false);
    }
  }

  void _showToast(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg, textDirection: TextDirection.rtl)));
  }

  Future<void> _toggleConnect() async {
    if (userData == null || userData!['sub_url'] == null) return;

    if (v2rayStatus.value.state == 'CONNECTED') {
      await flutterV2ray.stopV2Ray();
      return;
    }

    if (await flutterV2ray.requestPermission()) {
      final String subUrl = userData!['sub_url'];
      try {
        final res = await http.get(Uri.parse(subUrl));
        if (res.statusCode == 200) {
          String rawConfig = utf8.decode(base64.decode(base64.normalize(res.body.trim())));
          List<String> configs = rawConfig.split('\n').where((s) => s.trim().isNotEmpty).toList();
          
          if (configs.isNotEmpty) {
            final parser = flutterV2ray.parseV2rayUrl(configs.first);
            await flutterV2ray.startV2Ray(
              remark: 'JetConfig VPN',
              config: parser.toShareUrl(),
              proxyOnly: false,
            );
          }
        }
      } catch (e) {
        _showToast('خطا در دریافت سرورها');
      }
    }
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
                  if (v2rayStatus.value.state == 'CONNECTED') {
                    await flutterV2ray.stopV2Ray();
                  }
                  setState(() {
                    savedUser = null;
                    userData = null;
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
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.shield_rounded, size: 90, color: Colors.cyanAccent),
          const SizedBox(height: 24),
          const Text('ورود به حساب اشتراک', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          const Text('نام کاربری کانفیگ خود را وارد کنید', style: TextStyle(color: Colors.grey)),
          const SizedBox(height: 32),
          TextField(
            controller: _userController,
            textAlign: TextAlign.center,
            decoration: InputDecoration(
              hintText: 'مثال: user_93330195_778',
              filled: true,
              fillColor: const Color(0xFF1E293B),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
            ),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.cyanAccent,
              foregroundColor: Colors.black,
              minimumSize: const Size(double.infinity, 52),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            ),
            onPressed: () {
              if (_userController.text.trim().isNotEmpty) {
                _fetchUserData(_userController.text.trim());
              }
            },
            child: const Text('ورود و فعال‌سازی', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _buildDashboardView() {
    final double percent = userData!['total_gb'] > 0
        ? (userData!['used_gb'] / userData!['total_gb']).clamp(0.0, 1.0)
        : 0.0;
    final isConnected = v2rayStatus.value.state == 'CONNECTED';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text('کاربر: ${userData!['username']}', style: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold)),
          ),
          const SizedBox(height: 30),
          CircularPercentIndicator(
            radius: 95.0,
            lineWidth: 14.0,
            animation: true,
            percent: percent,
            center: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('${userData!['remaining_gb']} GB', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 24)),
                const Text('حجم باقیمانده', style: TextStyle(color: Colors.grey, fontSize: 12)),
              ],
            ),
            circularStrokeCap: CircularStrokeCap.round,
            progressColor: percent > 0.85 ? Colors.redAccent : Colors.cyanAccent,
            backgroundColor: const Color(0xFF1E293B),
          ),
          const SizedBox(height: 30),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildInfoBadge('کل حجم', '${userData!['total_gb']} GB', Icons.data_usage),
              _buildInfoBadge('اعتبار', '${userData!['expire_days']}', Icons.timer_outlined),
            ],
          ),
          const SizedBox(height: 45),
          GestureDetector(
            onTap: _toggleConnect,
            child: Container(
              width: 130,
              height: 130,
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
                child: Icon(
                  Icons.power_settings_new_rounded,
                  size: 60,
                  color: isConnected ? Colors.black : Colors.black87,
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
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
      width: 135,
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Icon(icon, color: Colors.cyanAccent, size: 24),
          const SizedBox(height: 6),
          Text(label, style: const TextStyle(color: Colors.grey, fontSize: 12)),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
        ],
      ),
    );
  }
}

