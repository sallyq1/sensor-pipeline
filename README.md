# Sensor Pipeline - Testing Package

This package contains a complete sensor data collection system for iOS and watchOS, with a built-in test harness for validation.

## Quick Start

1. Open `ios/FocusAI.xcworkspace` (or `.xcodeproj`) in Xcode
2. Connect iPhone via USB
3. Enable test mode: Edit Scheme → Run → Arguments → Environment Variables → Add `TEST_HARNESS=1`
4. Press `Cmd + R` to build and run
5. Follow the on-screen test guide

For complete instructions, see [TESTING_GUIDE.md](./TESTING_GUIDE.md)

## What's Included

- Phone Sensors: Accelerometer, Gyroscope, Microphone, Proximity, Orientation, Screen State
- Watch Sensors: Accelerometer, Gyroscope, Heart Rate, HRV (via Apple Watch)
- Data Streaming: Real-time sensor data at 10Hz (10 updates per second)
- Test Harness: Built-in debug UI for testing all sensors

## Requirements

- Mac with Xcode installed
- iPhone with iOS 14+ and USB connection
- Apple Watch (optional, for watch sensor testing)

## Project Structure

```
ios/
├── FocusAI/
│   ├── Debug/
│   │   └── SensorTestHarness.swift    (Test UI)
│   ├── Sensors/
│   │   ├── PhoneSensorManager.swift   (Phone sensor collection)
│   │   └── WCSessionManager.swift     (Watch connectivity)
│   ├── SensorsModule.swift             (React Native bridge)
│   └── AppDelegate.swift              (App entry point)
└── WatchKit Extension/
    ├── WatchSensorManager.swift       (Watch sensor collection)
    └── WatchWCSessionManager.swift    (Watch → iPhone communication)
```

## Permissions Required

- Motion & Fitness (for accelerometer/gyroscope)
- Microphone (for audio level detection)
- HealthKit (for watch heart rate/HRV - watch app only)

## Expected Sensor Data

### Phone Sensors (10Hz updates)
- Accelerometer: [x, y, z] vectors
- Gyroscope: [x, y, z] vectors
- Microphone: Decibel level
- Orientation: portrait/landscape/etc
- Proximity: true/false
- Screen state: on/off
- Foreground app: App name

### Watch Sensors
- Accelerometer: [x, y, z] vectors (10Hz)
- Gyroscope: [x, y, z] vectors (10Hz)
- Heart Rate: bpm (updates every 2-5 seconds)
- HRV: milliseconds (may not always be available)

## Documentation

- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Complete testing instructions with troubleshooting

## Architecture

- PhoneSensorManager: Singleton managing all phone sensors
- WatchSensorManager: Singleton managing watch sensors
- WCSessionManager: Handles Watch ↔ iPhone communication
- SensorsModule: React Native bridge for JS access
- SensorTestHarness: Debug UI for validation

## Data Flow

```
Phone Sensors → PhoneSensorManager → SensorsModule → React Native
Watch Sensors → WatchSensorManager → WatchWCSessionManager → WCSession → Phone → SensorsModule → React Native
```
