# Sensor Pipeline Testing Guide

Complete guide for testing the sensor pipeline on Mac with iPhone and Apple Watch.

## Prerequisites

- Mac with Xcode installed (latest version recommended)
- iPhone with iOS 14+
- Apple Watch (optional, for watch sensor testing)
- USB cable to connect iPhone to Mac

## Quick Start

### Step 1: Open the Project

1. Navigate to the `ios` folder in this project
2. Open `FocusAI.xcworkspace` (or `.xcodeproj` if no workspace) in Xcode
3. Wait for Xcode to finish indexing

### Step 2: Connect Your iPhone

1. Connect your iPhone to your Mac via USB
2. In Xcode, select your iPhone from the device dropdown (top toolbar)
3. If prompted, trust the computer on your iPhone

### Step 3: Enable Test Harness

**Option A: Environment Variable (Recommended)**
1. In Xcode, click on the scheme dropdown (next to the device selector)
2. Click "Edit Scheme..."
3. Select "Run" in the left sidebar
4. Go to the "Arguments" tab
5. Under "Environment Variables", click the "+" button
6. Add:
   - Name: `TEST_HARNESS`
   - Value: `1`
7. Click "Close"

**Option B: Keyboard Shortcut**
- Press the "D" key when the app is running (requires physical keyboard)

### Step 4: Build and Run

1. Press `Cmd + R` or click the Play button in Xcode
2. Wait for the app to build and install on your iPhone
3. The test harness screen should appear automatically

## Setup Checklist

Before you start testing, verify:

- [ ] Xcode is installed and updated
- [ ] Project opens without errors
- [ ] iPhone is connected via USB
- [ ] Device is selected in Xcode (not Simulator)
- [ ] `TEST_HARNESS=1` environment variable is set
- [ ] iPhone Settings → Privacy & Security → Motion & Fitness → Enabled
- [ ] iPhone Settings → Privacy & Security → Microphone → Enabled
- [ ] Apple Watch is paired with iPhone (if testing watch sensors)
- [ ] Watch is on your wrist (for heart rate testing)

## Running the Tests

Once the test harness is running, you'll see 4 sections on screen:

### Section A: Device & Permission Status

Check that all permissions show `[PASS]` in green:
- Motion permission: granted
- Microphone permission: granted
- Proximity enabled: yes
- WCSession activated: yes
- Watch reachable: yes (if watch is available)

If any show `[WAIT]` or `[ERROR]`, grant the necessary permissions in iPhone Settings and restart the app.

### Section B: Phone Sensors

Follow these tests in order:

**Test 1: Tilt Test**
- Tilt your phone left and right
- Expected: Accelerometer X value should change
- Status should show `[PASS]` in green

**Test 2: Rotation Test**
- Rotate your phone
- Expected: Gyroscope Z value should change
- Status should show `[PASS]` in green

**Test 3: Proximity Test**
- Cover the top of your phone with your hand
- Expected: Proximity state should change to `TRUE`
- Status should show `[PASS]` in green

**Test 4: Microphone Test**
- Speak near the microphone
- Expected: Mic decibels should increase (go above -160)
- Status should show `[PASS]` in green

**Test 5: Screen Lock Test**
- Lock your iPhone screen
- Expected: Screen state should show `inactive` or `off`
- Status should show `[PASS]` in green

**Test 6: App Switch Test**
- Open Safari app (or any other app)
- Expected: Foreground app name should show the app name
- Status should show `[PASS]` in green

### Section C: Watch Sensors (If you have an Apple Watch)

**Test 1: Watch IMU Test**
- Rotate your wrist while wearing the watch
- Expected: Watch accelerometer and gyroscope values should update
- Status should show `[PASS]` in green

**Test 2: Heart Rate Test**
- Walk around for 30 seconds
- Expected: Heart rate should update with a number (e.g., "72 bpm")
- Status should show `[PASS]` in green
- Note: Heart rate updates are slower than IMU (every few seconds is normal)

**Test 3: HRV Test**
- Continue wearing the watch
- Expected: HRV may or may not show (depends on watchOS version)
- Status may show `[WAIT]` if HRV is not available (this is normal)

**Test 4: Range Test**
- Move watch away from iPhone (10+ feet)
- Expected: Watch data should stop updating temporarily
- Status may show `[ERROR]` or `[WAIT]` (this is expected)
- Move watch back near iPhone
- Expected: Data should resume updating
- Status should return to `[PASS]`

### Section D: Test Guide

This section displays the test instructions on screen. Follow the numbered list to verify each sensor.

## What to Look For

### Good Signs (Everything Working)
- All statuses show `[PASS]` in green
- Values update smoothly (10 times per second)
- No red `[ERROR]` messages
- Console shows regular data packets

### Warning Signs (Needs Attention)
- Yellow `[WAIT]` status for more than 5 seconds
- Missing sensor data (shows "No data")
- Permission errors

### Error Signs (Needs Fixing)
- Red `[ERROR]` status
- "No updates in Xs" messages
- Console shows error messages

## Console Logging

The Xcode console will show:
- Timestamped sensor data packets
- Any errors or warnings
- Watch connection status

**To view console:**
1. In Xcode, press `Cmd + Shift + Y` to show the debug area
2. Or click the bottom panel icon in Xcode

## Troubleshooting

### Problem: Test harness doesn't appear

**Solution:**
- Make sure `TEST_HARNESS=1` is set in environment variables
- Or press "D" key when app is running
- Check that AppDelegate.swift is included in the build
- Verify the app built successfully (check for build errors)

### Problem: Permissions denied

**Solution:**
1. Go to iPhone Settings → Privacy & Security
2. Grant permissions for:
   - Motion & Fitness
   - Microphone
3. Restart the app

### Problem: Watch data not showing

**Solution:**
- Make sure Apple Watch is paired with iPhone
- Make sure watch app is installed (if applicable)
- Check that WCSession shows "activated: yes" in Section A
- Move watch closer to iPhone
- Wait 10-30 seconds for initial connection
- Check that watch is on your wrist (for heart rate)

### Problem: Sensors not updating

**Solution:**
- Check that all permissions are granted
- Restart the app
- Check Xcode console for error messages
- Verify the app is in foreground (not backgrounded)
- For watch sensors, ensure watch is within Bluetooth range

### Problem: Build errors

**Solution:**
1. Clean build folder: `Cmd + Shift + K`
2. Build again: `Cmd + B`
3. If still errors, check that all Swift files are added to the target
4. Verify all dependencies are properly linked
5. Check Xcode version compatibility

### Problem: App crashes on launch

**Solution:**
- Check Xcode console for crash logs
- Verify all required permissions are requested
- Check that Info.plist has required permission descriptions
- Ensure device is running compatible iOS version

## Tips

- Keep the app in foreground while testing
- Don't lock the screen during sensor tests (except for the screen lock test)
- Watch sensors may take 10-30 seconds to start showing data
- Heart rate updates are slower than IMU (every few seconds is normal)
- Scroll down in the test harness to see all sections
- Values update at 10Hz (10 times per second) for IMU sensors
- Watch heart rate may update every 2-5 seconds (this is normal)

## What to Report Back

Please provide the following information:

### 1. Screenshots

Take screenshots of the test harness screen showing:
- Section A (all permissions status)
- Section B (phone sensors with live values)
- Section C (watch sensors, if applicable)

### 2. Console Output

Copy/paste or screenshot:
- First 20-30 lines of console output after app launch
- Any error messages in red
- Any warning messages

### 3. Test Results

Document:
- Which tests passed (list test numbers)
- Which tests failed (list test numbers)
- Any unexpected behavior
- Any sensors that never showed data

### 4. Device Information

Provide:
- iPhone model (e.g., iPhone 14 Pro)
- iOS version (e.g., iOS 17.2)
- Apple Watch model (if used, e.g., Apple Watch Series 9)
- watchOS version (if used, e.g., watchOS 10.2)
- Xcode version

### 5. Additional Notes

Any other observations:
- Performance issues
- UI problems
- Connection issues
- Anything that seemed unusual

## Project Structure

The project contains:

```
ios/
├── FocusAI/
│   ├── Debug/
│   │   └── SensorTestHarness.swift    (Test UI)
│   ├── Sensors/
│   │   ├── PhoneSensorManager.swift   (Phone sensor collection)
│   │   └── WCSessionManager.swift     (Watch connectivity)
│   ├── SensorsModule.swift             (React Native bridge)
│   └── AppDelegate.swift               (App entry point)
└── WatchKit Extension/
    ├── WatchSensorManager.swift        (Watch sensor collection)
    └── WatchWCSessionManager.swift     (Watch → iPhone communication)
```

## Expected Sensor Data

### Phone Sensors (10Hz updates)
- Accelerometer: [x, y, z] vectors in m/s^2
- Gyroscope: [x, y, z] vectors in rad/s
- Microphone: Decibel level (typically -160 to 0 dB)
- Orientation: portrait, landscape_left, landscape_right, etc.
- Proximity: true/false
- Screen state: on, off, inactive
- Foreground app: App name string

### Watch Sensors
- Accelerometer: [x, y, z] vectors (10Hz updates)
- Gyroscope: [x, y, z] vectors (10Hz updates)
- Heart Rate: bpm integer (updates every 2-5 seconds)
- HRV: milliseconds double (may not always be available)

## Need Help?

If you encounter issues not covered here:
1. Check the Xcode console for detailed error messages
2. Take a screenshot of the error
3. Note what you were doing when the error occurred
4. Review the troubleshooting section above
5. Report back with all the information requested in "What to Report Back"

---
