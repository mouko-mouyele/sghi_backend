import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'screens/login_screen.dart';
import 'screens/patient_home_screen.dart';
import 'screens/doctor_home_screen.dart';

void main() => runApp(const SghlApp());

class SghlApp extends StatelessWidget {
  const SghlApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SGHL Mobile',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0D9488),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const SplashScreen(),
    );
  }
}

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');
    final role = prefs.getString('role');
    if (!mounted) return;
    Widget next = const LoginScreen();
    if (token != null && role != null) {
      if (role == 'PATIENT') next = const PatientHomeScreen();
      if (role == 'MEDECIN') next = const DoctorHomeScreen();
    }
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => next));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.local_hospital, size: 64, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 16),
            Text('SGHL Mobile', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 24),
            const CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}
