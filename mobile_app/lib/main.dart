import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:alarm/alarm.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest_all.dart' as tz;
import 'package:timezone/timezone.dart' as tz;
import 'package:flutter_timezone/flutter_timezone.dart';

// ==========================================
// CONFIGURATION & GLOBAL INSTANCES
// ==========================================

const String baseUrl = "http://10.0.2.2:8000"; 

final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
    FlutterLocalNotificationsPlugin();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // 1. Initialize Timezones
  tz.initializeTimeZones();
  try {
    final timeZoneName = await FlutterTimezone.getLocalTimezone();
    tz.setLocalLocation(tz.getLocation(timeZoneName.toString()));
  } catch (e) {
    debugPrint('Could not get local timezone: $e');
  }

  // 2. Initialize Local Notifications & Alarm plugin
  const AndroidInitializationSettings initializationSettingsAndroid =
      AndroidInitializationSettings('@mipmap/ic_launcher');
  const InitializationSettings initializationSettings =
      InitializationSettings(android: initializationSettingsAndroid);

  await flutterLocalNotificationsPlugin.initialize(settings: initializationSettings);
  await flutterLocalNotificationsPlugin
      .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
      ?.requestNotificationsPermission();

  await Alarm.init();

  final prefs = await SharedPreferences.getInstance();
  final int? savedPatientId = prefs.getInt('patient_id');
  final String? savedPatientName = prefs.getString('patient_name');

  runApp(MyApp(savedPatientId: savedPatientId, savedPatientName: savedPatientName));
}

// ==========================================
// ROOT APP WIDGET
// ==========================================

class MyApp extends StatelessWidget {
  final int? savedPatientId;
  final String? savedPatientName;
  
  const MyApp({super.key, this.savedPatientId, this.savedPatientName});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Medication Tracker MVP',
      theme: ThemeData(primarySwatch: Colors.teal),
      home: savedPatientId != null
          ? PatientDashboard(user: {'id': savedPatientId, 'name': savedPatientName})
          : const WelcomeScreen(),
    );
  }
}

// ==========================================
// WELCOME SCREEN
// ==========================================

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Medication Tracker')),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Icon(Icons.medical_services, size: 80, color: Colors.teal),
            const SizedBox(height: 20),
            const Text(
              'Welcome! Select your role to begin:',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18),
            ),
            const SizedBox(height: 40),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(padding: const EdgeInsets.all(16)),
              icon: const Icon(Icons.person),
              label: const Text('I am a Caregiver (Manage Family)', style: TextStyle(fontSize: 16)),
              onPressed: () {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const CaregiverLoginScreen()));
              },
            ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(padding: const EdgeInsets.all(16)),
              icon: const Icon(Icons.elderly),
              label: const Text('I am Father / Mother (Enter Access Code)', style: TextStyle(fontSize: 16)),
              onPressed: () {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const PatientCodeScreen()));
              },
            ),
          ],
        ),
      ),
    );
  }
}

// ==========================================
// PATIENT CODE LOGIN
// ==========================================

class PatientCodeScreen extends StatefulWidget {
  const PatientCodeScreen({super.key});

  @override
  State<PatientCodeScreen> createState() => _PatientCodeScreenState();
}

class _PatientCodeScreenState extends State<PatientCodeScreen> {
  final _codeController = TextEditingController();
  bool isLoading = false;

  void verifyCode() async {
    setState(() => isLoading = true);
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/auth/patient-code-login'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"access_code": _codeController.text.trim()}),
      );

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        
        final prefs = await SharedPreferences.getInstance();
        await prefs.setInt('patient_id', data['id']);
        await prefs.setString('patient_name', data['name']);

        if (!mounted) return;
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => PatientDashboard(user: data)),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Invalid access code.')));
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    } finally {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Father / Mother Login')),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Enter your 4-digit access code:', textAlign: TextAlign.center, style: TextStyle(fontSize: 16)),
            const SizedBox(height: 20),
            TextField(
              controller: _codeController,
              textAlign: TextAlign.center,
              style: const TextStyle(fontSize: 28, letterSpacing: 8, fontWeight: FontWeight.bold),
              decoration: const InputDecoration(hintText: 'ABCD', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 20),
            isLoading
                ? const CircularProgressIndicator()
                : ElevatedButton(
                    style: ElevatedButton.styleFrom(minimumSize: const Size.fromHeight(50)),
                    onPressed: verifyCode,
                    child: const Text('Open My Medications', style: TextStyle(fontSize: 18)),
                  ),
          ],
        ),
      ),
    );
  }
}

// ==========================================
// CAREGIVER AUTHENTICATION
// ==========================================

class CaregiverLoginScreen extends StatefulWidget {
  const CaregiverLoginScreen({super.key});

  @override
  State<CaregiverLoginScreen> createState() => _CaregiverLoginScreenState();
}

class _CaregiverLoginScreenState extends State<CaregiverLoginScreen> {
  final emailController = TextEditingController();
  final passController = TextEditingController();
  final nameController = TextEditingController();
  bool isRegistering = false;

  void submit() async {
    final endpoint = isRegistering ? '/auth/register-caregiver' : '/auth/login-caregiver';
    final body = isRegistering 
        ? {"name": nameController.text, "email": emailController.text, "password": passController.text}
        : {"email": emailController.text, "password": passController.text};

    final res = await http.post(
      Uri.parse('$baseUrl$endpoint'),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode(body),
    );

    if (res.statusCode == 200) {
      final data = jsonDecode(res.body);
      if (!mounted) return;
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => CaregiverDashboard(user: data)));
    } else {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Authentication failed')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(isRegistering ? 'Caregiver Register' : 'Caregiver Login')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (isRegistering) TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Your Name')),
            TextField(controller: emailController, decoration: const InputDecoration(labelText: 'Email')),
            TextField(controller: passController, decoration: const InputDecoration(labelText: 'Password'), obscureText: true),
            const SizedBox(height: 20),
            ElevatedButton(onPressed: submit, child: Text(isRegistering ? 'Register' : 'Login')),
            TextButton(
              onPressed: () => setState(() => isRegistering = !isRegistering),
              child: Text(isRegistering ? 'Already have an account? Login' : 'Need an account? Register'),
            )
          ],
        ),
      ),
    );
  }
}

// ==========================================
// CAREGIVER DASHBOARD
// ==========================================

class CaregiverDashboard extends StatefulWidget {
  final Map<String, dynamic> user;
  const CaregiverDashboard({super.key, required this.user});

  @override
  State<CaregiverDashboard> createState() => _CaregiverDashboardState();
}

class _CaregiverDashboardState extends State<CaregiverDashboard> {
  List familyMembers = [];

  @override
  void initState() {
    super.initState();
    fetchFamily();
  }

  void fetchFamily() async {
    final res = await http.get(Uri.parse('$baseUrl/users/family/${widget.user['id']}'));
    if (res.statusCode == 200) {
      setState(() => familyMembers = jsonDecode(res.body));
    }
  }

  void addPatientDialog() {
    final nameController = TextEditingController();
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add Family Member (e.g. Father)'),
        content: TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Name')),
        actions: [
          TextButton(
            onPressed: () async {
              final res = await http.post(
                Uri.parse('$baseUrl/patients/add'),
                headers: {"Content-Type": "application/json"},
                body: jsonEncode({"name": nameController.text, "caregiver_id": widget.user['id']}),
              );
              if (res.statusCode == 200) {
                final newPatient = jsonDecode(res.body);
                Navigator.pop(context);
                fetchFamily();
                
                showDialog(
                  context: context,
                  builder: (_) => AlertDialog(
                    title: const Text('Access Code Generated!'),
                    content: Text('Give this code to ${newPatient['name']}:\n\nCode: ${newPatient['access_code']}', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                    actions: [TextButton(onPressed: () => Navigator.pop(context), child: const Text('OK'))],
                  ),
                );
              }
            },
            child: const Text('Generate Code'),
          )
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Caregiver: ${widget.user['name']}'), actions: [
        IconButton(icon: const Icon(Icons.add), onPressed: addPatientDialog)
      ]),
      body: ListView.builder(
        itemCount: familyMembers.length,
        itemBuilder: (context, index) {
          final m = familyMembers[index];
          return Card(
            margin: const EdgeInsets.all(8.0),
            child: ListTile(
              title: Text(m['name'], style: const TextStyle(fontWeight: FontWeight.bold)),
              subtitle: Text('Access Code: ${m['access_code'] ?? "N/A"}'),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  IconButton(
                    icon: const Icon(Icons.list_alt, color: Colors.teal),
                    tooltip: 'View/Delete Medications',
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => PatientMedicationsScreen(
                          patientId: m['id'],
                          patientName: m['name'],
                        ),
                      ),
                    ),
                  ),
                  ElevatedButton(
                    child: const Text('Add Meds'),
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => AddMedicationScreen(patientId: m['id']),
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
}

// ==========================================
// VIEW & DELETE MEDICATIONS
// ==========================================

class PatientMedicationsScreen extends StatefulWidget {
  final int patientId;
  final String patientName;

  const PatientMedicationsScreen({
    super.key,
    required this.patientId,
    required this.patientName,
  });

  @override
  State<PatientMedicationsScreen> createState() => _PatientMedicationsScreenState();
}

class _PatientMedicationsScreenState extends State<PatientMedicationsScreen> {
  List meds = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    fetchPatientMeds();
  }

  void fetchPatientMeds() async {
    setState(() => isLoading = true);
    try {
      final res = await http.get(Uri.parse('$baseUrl/medications/${widget.patientId}'));
      if (res.statusCode == 200) {
        setState(() => meds = jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint("Error fetching patient meds: $e");
    } finally {
      setState(() => isLoading = false);
    }
  }

  void deleteMedication(int medId, String medName) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Confirm Deletion'),
        content: Text('Are you sure you want to delete "$medName"? This will remove it from ${widget.patientName}\'s app immediately.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red, foregroundColor: Colors.white),
            onPressed: () async {
              Navigator.pop(context);
              try {
                await Alarm.stop(medId + 100000);
                await flutterLocalNotificationsPlugin.cancel(id: medId);

                final res = await http.delete(Uri.parse('$baseUrl/medications/$medId'));
                if (res.statusCode == 200) {
                  if (!mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Medication deleted successfully.')),
                  );
                  fetchPatientMeds();
                }
              } catch (e) {
                debugPrint("Error deleting medication: $e");
              }
            },
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('${widget.patientName}\'s Medications')),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : meds.isEmpty
              ? const Center(
                  child: Text(
                    'No active medications assigned.',
                    style: TextStyle(fontSize: 16, color: Colors.grey),
                  ),
                )
              : ListView.builder(
                  itemCount: meds.length,
                  itemBuilder: (context, index) {
                    final med = meds[index];
                    return Card(
                      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      elevation: 2,
                      child: ListTile(
                        title: Text(med['medicine_name'], style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
                        subtitle: Text('Dosage: ${med['dosage']}\nTime: ${med['schedule_time']}'),
                        isThreeLine: true,
                        trailing: IconButton(
                          icon: const Icon(Icons.delete, color: Colors.red),
                          onPressed: () => deleteMedication(med['id'], med['medicine_name']),
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}

// ==========================================
// ADD MEDICATION & SCHEDULE BOTH NOTIFICATION & ALARM
// ==========================================

class AddMedicationScreen extends StatefulWidget {
  final int patientId;
  const AddMedicationScreen({super.key, required this.patientId});

  @override
  State<AddMedicationScreen> createState() => _AddMedicationScreenState();
}

class _AddMedicationScreenState extends State<AddMedicationScreen> {
  final nameController = TextEditingController();
  final dosageController = TextEditingController();
  final timeController = TextEditingController(text: "08:00");

  void _pickTime() async {
    final TimeOfDay? picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.now(),
    );
    if (picked != null) {
      final hours = picked.hour.toString().padLeft(2, '0');
      final minutes = picked.minute.toString().padLeft(2, '0');
      setState(() {
        timeController.text = "$hours:$minutes";
      });
    }
  }

  Future<void> _scheduleReminders(String medicineName, String dosage, String timeStr, int notificationId) async {
    try {
      final parts = timeStr.split(':');
      final hour = int.parse(parts[0]);
      final minute = int.parse(parts[1]);

      final now = tz.TZDateTime.now(tz.local);
      var scheduledDate = tz.TZDateTime(
        tz.local,
        now.year,
        now.month,
        now.day,
        hour,
        minute,
      );

      if (scheduledDate.isBefore(now)) {
        scheduledDate = scheduledDate.add(const Duration(days: 1));
      }

      // 1. Schedule Normal Push Notification at exact schedule time
      const AndroidNotificationDetails androidDetails = AndroidNotificationDetails(
        'medication_reminder_channel',
        'Medication Reminders',
        channelDescription: 'Time to take your scheduled medicine',
        importance: Importance.max,
        priority: Priority.high,
      );

      await flutterLocalNotificationsPlugin.zonedSchedule(
        id: notificationId,
        title: 'Time for medicine: $medicineName',
        body: 'Dosage: $dosage',
        scheduledDate: scheduledDate,
        notificationDetails: const NotificationDetails(android: androidDetails),
        androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
        matchDateTimeComponents: DateTimeComponents.time,
      );

      // 2. Schedule Persistent Audio Alarm 5 minutes later
      final followUpDate = scheduledDate.add(const Duration(minutes: 2));
      final int alarmId = notificationId + 100000;

      final alarmSettings = AlarmSettings(
        id: alarmId,
        dateTime: followUpDate,
        assetAudioPath: 'assets/alarm.mp3',
        loopAudio: true,
        vibrate: true,
        volume: 1.0,
        fadeDuration: 0.0,
        notificationSettings: NotificationSettings(
          title: '🚨 URGENT ALARM: Take $medicineName!',
          body: 'You have not confirmed taking $medicineName ($dosage). Open the app and tap "I Ate" to stop this alarm.',
          stopButton: 'Stop Alarm',
        ),
      );

      await Alarm.set(alarmSettings: alarmSettings);
    } catch (e, stackTrace) {
      debugPrint("ALARM ERROR: $e");
      debugPrint("STACKTRACE: $stackTrace");
    }
  }

  void save() async {
    final res = await http.post(
      Uri.parse('$baseUrl/medications'),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "patient_id": widget.patientId,
        "medicine_name": nameController.text,
        "dosage": dosageController.text,
        "schedule_time": timeController.text,
      }),
    );

    if (res.statusCode == 200 || res.statusCode == 201) {
      final data = jsonDecode(res.body);
      int medicationId = data['id'] ?? (DateTime.now().millisecondsSinceEpoch ~/ 1000);

      await _scheduleReminders(
        nameController.text,
        dosageController.text,
        timeController.text,
        medicationId,
      );
    }

    if (!mounted) return;
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add Medication')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Medicine Name')),
            TextField(controller: dosageController, decoration: const InputDecoration(labelText: 'Dosage (e.g. 1 pill)')),
            TextField(
              controller: timeController,
              readOnly: true,
              onTap: _pickTime,
              decoration: const InputDecoration(
                labelText: 'Alarm Time (HH:MM)',
                suffixIcon: Icon(Icons.access_time),
              ),
            ),
            const SizedBox(height: 20),
            ElevatedButton(onPressed: save, child: const Text('Save & Set Alarms')),
          ],
        ),
      ),
    );
  }
}

// ==========================================
// PATIENT DASHBOARD
// ==========================================

class PatientDashboard extends StatefulWidget {
  final Map<String, dynamic> user;
  const PatientDashboard({super.key, required this.user});

  @override
  State<PatientDashboard> createState() => _PatientDashboardState();
}

class _PatientDashboardState extends State<PatientDashboard> {
  List meds = [];
  final Set<int> takenMedIds = {}; // Tracks meds marked as taken in this session

  @override
  void initState() {
    super.initState();
    fetchMeds();
  }

  void fetchMeds() async {
    final res = await http.get(Uri.parse('$baseUrl/medications/${widget.user['id']}'));
    if (res.statusCode == 200) {
      setState(() => meds = jsonDecode(res.body));
    }
  }

  void logoutPatient() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    if (!mounted) return;
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const WelcomeScreen()));
  }

  void confirmMedicationTaken(Map<String, dynamic> med) async {
    final int medId = med['id'];
    final int alarmId = medId + 100000;

    // 1. Stop the alarm and cancel notification immediately
    await Alarm.stop(alarmId);
    await flutterLocalNotificationsPlugin.cancel(id: medId);

    // 2. Update local state to switch button to "Medicine Taken"
    setState(() {
      takenMedIds.add(medId);
    });

    // 3. Call backend API to log compliance
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/medications/take'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "patient_id": widget.user['id'],
          "medication_id": medId,
        }),
      );

      if (res.statusCode == 200) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Medicine marked as taken successfully!')),
        );
      } else {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Confirmed locally, sync pending.')),
        );
      }
    } catch (e) {
      debugPrint("Error syncing compliance log: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Medicines for ${widget.user['name']}'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: fetchMeds),
          IconButton(icon: const Icon(Icons.logout), onPressed: logoutPatient, tooltip: 'Unlink Device'),
        ],
      ),
      body: meds.isEmpty
          ? const Center(child: Text('No active medicines scheduled. All good!', style: TextStyle(fontSize: 16)))
          : ListView.builder(
              itemCount: meds.length,
              itemBuilder: (context, index) {
                final med = meds[index];
                final int medId = med['id'];
                final bool isTaken = takenMedIds.contains(medId);

                return Card(
                  margin: const EdgeInsets.all(12),
                  elevation: 4,
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(med['medicine_name'], style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
                            const SizedBox(height: 5),
                            Text('Dosage: ${med['dosage']}', style: const TextStyle(fontSize: 16, color: Colors.grey)),
                            Text('Time: ${med['schedule_time']}', style: const TextStyle(fontSize: 18, color: Colors.teal, fontWeight: FontWeight.bold)),
                          ],
                        ),
                        isTaken
                            ? ElevatedButton.icon(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.grey.shade300,
                                  foregroundColor: Colors.grey.shade700,
                                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                                ),
                                icon: const Icon(Icons.check_circle, color: Colors.green),
                                label: const Text('Medicine Taken', style: TextStyle(fontSize: 16)),
                                onPressed: null, // Disabled once clicked
                              )
                            : ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.green,
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                                ),
                                onPressed: () => confirmMedicationTaken(med),
                                child: const Text('I Ate', style: TextStyle(fontSize: 18)),
                              ),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }
}