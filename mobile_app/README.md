

## 🚀 Quick Start Guide

Follow these steps to run the complete stack locally.

### Prerequisites

1. **Flutter SDK** installed and configured in your path.
2. **Python 3.10+** installed.
3. An **Android Virtual Device (AVD)** created via Android Studio.

---

### Step 1: Launch the Android Emulator

Before launching Flutter, start your virtual device:

1. List available emulators in your terminal:
   ```powershell
   flutter emulators
Launch your emulator (replace <EMULATOR_ID> with your emulator's ID, e.g., Pixel_API_35):PowerShellflutter emulators --launch <EMULATOR_ID>
(VS Code Shortcut: Press Ctrl + Shift + P → select Flutter: Launch Emulator)Step 2: Start the FastAPI BackendOpen a terminal window and execute:PowerShell# Navigate to backend directory
cd backend

# Activate your virtual environment
.\venv\Scripts\Activate.ps1

# Run the Uvicorn development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
API Docs: Open http://localhost:8000/docs in your browser.Emulator Network: The Android emulator connects to the host machine at http://10.0.2.2:8000.Step 3: Start the Flutter Mobile ApplicationOpen a second terminal window and run:PowerShell# Navigate to mobile app directory
cd mobile_app

# Install dependencies
flutter pub get

# Run the application on your running emulator
flutter run
🛠️ Key Commands ReferenceActionCommand / KeyList Connected Devicesflutter devicesHot Reload Mobile AppPress r in the Flutter terminalHot Restart Mobile AppPress R in the Flutter terminalStop Server / AppPress Ctrl + C in the respective terminal