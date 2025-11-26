import Foundation
import CoreMotion
import AVFoundation
import UIKit

class PhoneSensorManager {
    static let shared = PhoneSensorManager()
    
    // Motion manager for accelerometer and gyroscope
    private let motionManager = CMMotionManager()
    
    // Audio recorder for microphone
    private var audioRecorder: AVAudioRecorder?
    private var audioSession: AVAudioSession?
    
    // Device
    private let device = UIDevice.current
    
    // Streaming state
    private var isStreaming = false
    private var streamingCallback: (([String: Any]) -> Void)?
    private var streamingTimer: Timer?
    
    // Current sensor values
    private var currentAccelerometerData: CMAccelerometerData?
    private var currentGyroData: CMGyroData?
    private var currentOrientation: UIDeviceOrientation = .unknown
    private var currentProximityState: Bool = false
    private var currentMicAmplitude: Double = 0.0
    private var currentMicDB: Double = -160.0 // Default to minimum dB
    private var screenState: String = "unknown"
    private var foregroundAppName: String = "unknown"
    
    // Lock for thread safety
    private let sensorLock = NSLock()
    
    private init() {
        setupAudioSession()
        setupDeviceObservers()
        setupApplicationObservers()
    }
    
    deinit {
        stopStreaming()
        removeObservers()
    }
    
    // MARK: - Setup Methods
    
    private func setupAudioSession() {
        audioSession = AVAudioSession.sharedInstance()
        
        do {
            try audioSession?.setCategory(.record, mode: .measurement, options: [])
            try audioSession?.setActive(true)
        } catch {
            print("Failed to setup audio session: \(error)")
        }
    }
    
    private func setupDeviceObservers() {
        // Enable orientation monitoring
        device.beginGeneratingDeviceOrientationNotifications()
        
        // Enable proximity monitoring
        device.isProximityMonitoringEnabled = true
        
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(orientationDidChange),
            name: UIDevice.orientationDidChangeNotification,
            object: nil
        )
        
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(proximityStateDidChange),
            name: UIDevice.proximityStateDidChangeNotification,
            object: nil
        )
        
        // Initialize current values
        currentOrientation = device.orientation
        currentProximityState = device.proximityState
    }
    
    private func setupApplicationObservers() {
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(applicationDidBecomeActive),
            name: UIApplication.didBecomeActiveNotification,
            object: nil
        )
        
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(applicationWillResignActive),
            name: UIApplication.willResignActiveNotification,
            object: nil
        )
        
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(applicationDidEnterBackground),
            name: UIApplication.didEnterBackgroundNotification,
            object: nil
        )
        
        // Initialize screen state
        if UIApplication.shared.applicationState == .active {
            screenState = "on"
        } else {
            screenState = "off"
        }
        
        updateForegroundAppName()
    }
    
    private func removeObservers() {
        NotificationCenter.default.removeObserver(self)
        device.endGeneratingDeviceOrientationNotifications()
        device.isProximityMonitoringEnabled = false
    }
    
    // MARK: - Notification Handlers
    
    @objc private func orientationDidChange() {
        sensorLock.lock()
        currentOrientation = device.orientation
        sensorLock.unlock()
    }
    
    @objc private func proximityStateDidChange() {
        sensorLock.lock()
        currentProximityState = device.proximityState
        sensorLock.unlock()
    }
    
    @objc private func applicationDidBecomeActive() {
        sensorLock.lock()
        screenState = "on"
        sensorLock.unlock()
        updateForegroundAppName()
    }
    
    @objc private func applicationWillResignActive() {
        sensorLock.lock()
        screenState = "off"
        sensorLock.unlock()
    }
    
    @objc private func applicationDidEnterBackground() {
        sensorLock.lock()
        screenState = "off"
        sensorLock.unlock()
    }
    
    private func updateForegroundAppName() {
        // Get foreground app name from UIApplication
        // Note: iOS doesn't provide direct API for app name, but we can use bundle name
        if let appName = Bundle.main.infoDictionary?["CFBundleName"] as? String {
            sensorLock.lock()
            foregroundAppName = appName
            sensorLock.unlock()
        } else if let appDisplayName = Bundle.main.infoDictionary?["CFBundleDisplayName"] as? String {
            sensorLock.lock()
            foregroundAppName = appDisplayName
            sensorLock.unlock()
        }
    }
    
    // MARK: - Motion Sensors
    
    private func startMotionSensors() {
        // Configure motion manager for 50Hz (0.02 seconds interval)
        motionManager.accelerometerUpdateInterval = 0.02 // 50Hz
        motionManager.gyroUpdateInterval = 0.02 // 50Hz
        
        // Start accelerometer updates
        if motionManager.isAccelerometerAvailable {
            motionManager.startAccelerometerUpdates(to: OperationQueue.main) { [weak self] (data, error) in
                guard let self = self, let data = data else { return }
                self.sensorLock.lock()
                self.currentAccelerometerData = data
                self.sensorLock.unlock()
            }
        }
        
        // Start gyroscope updates
        if motionManager.isGyroAvailable {
            motionManager.startGyroUpdates(to: OperationQueue.main) { [weak self] (data, error) in
                guard let self = self, let data = data else { return }
                self.sensorLock.lock()
                self.currentGyroData = data
                self.sensorLock.unlock()
            }
        }
    }
    
    private func stopMotionSensors() {
        motionManager.stopAccelerometerUpdates()
        motionManager.stopGyroUpdates()
    }
    
    // MARK: - Microphone
    
    private func startMicrophone() {
        guard let audioSession = audioSession else { return }
        
        // Request microphone permission
        audioSession.requestRecordPermission { [weak self] granted in
            guard let self = self, granted else {
                print("Microphone permission denied")
                return
            }
            
            DispatchQueue.main.async {
                self.setupAudioRecorder()
            }
        }
    }
    
    private func setupAudioRecorder() {
        let audioSettings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatLinearPCM),
            AVSampleRateKey: 44100.0,
            AVNumberOfChannelsKey: 1,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsBigEndianKey: false,
            AVLinearPCMIsFloatKey: false
        ]
        
        let tempURL = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("temp_recording.wav")
        
        do {
            audioRecorder = try AVAudioRecorder(url: tempURL, settings: audioSettings)
            audioRecorder?.isMeteringEnabled = true
            audioRecorder?.record()
            
            // Start monitoring audio levels
            startAudioLevelMonitoring()
        } catch {
            print("Failed to setup audio recorder: \(error)")
        }
    }
    
    private func startAudioLevelMonitoring() {
        Timer.scheduledTimer(withTimeInterval: 0.01, repeats: true) { [weak self] timer in
            guard let self = self, self.isStreaming else {
                timer.invalidate()
                return
            }
            
            self.audioRecorder?.updateMeters()
            
            if let recorder = self.audioRecorder {
                // Get average power in decibels
                let averagePower = recorder.averagePower(forChannel: 0)
                
                // Convert to linear amplitude (0.0 to 1.0)
                let linearAmplitude = pow(10.0, averagePower / 20.0)
                
                self.sensorLock.lock()
                self.currentMicAmplitude = linearAmplitude
                self.currentMicDB = averagePower
                self.sensorLock.unlock()
            }
        }
    }
    
    private func stopMicrophone() {
        audioRecorder?.stop()
        audioRecorder = nil
    }
    
    // MARK: - Public API
    
    func startStreaming(callback: @escaping ([String: Any]) -> Void) {
        guard !isStreaming else {
            print("Already streaming")
            return
        }
        
        isStreaming = true
        streamingCallback = callback
        
        // Set up WCSessionManager to receive watch data
        WCSessionManager.shared.setWatchDataCallback { [weak self] watchData in
            // When watch data arrives, trigger a combined data emission
            self?.collectAndEmitSensorData()
        }
        
        // Start all sensors
        startMotionSensors()
        startMicrophone()
        updateForegroundAppName()
        
        // Start timer to combine all sensor values every 100ms
        streamingTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            self?.collectAndEmitSensorData()
        }
    }
    
    func stopStreaming() {
        guard isStreaming else { return }
        
        isStreaming = false
        streamingTimer?.invalidate()
        streamingTimer = nil
        streamingCallback = nil
        
        // Stop all sensors
        stopMotionSensors()
        stopMicrophone()
    }
    
    // MARK: - Data Collection
    
    private func collectAndEmitSensorData() {
        sensorLock.lock()
        
        // Collect accelerometer data
        var accX: Double = 0.0
        var accY: Double = 0.0
        var accZ: Double = 0.0
        
        if let accData = currentAccelerometerData {
            accX = accData.acceleration.x
            accY = accData.acceleration.y
            accZ = accData.acceleration.z
        }
        
        // Collect gyroscope data
        var gyroX: Double = 0.0
        var gyroY: Double = 0.0
        var gyroZ: Double = 0.0
        
        if let gyroData = currentGyroData {
            gyroX = gyroData.rotationRate.x
            gyroY = gyroData.rotationRate.y
            gyroZ = gyroData.rotationRate.z
        }
        
        // Get orientation string
        let orientationString = orientationToString(currentOrientation)
        
        // Get proximity state
        let proximity = currentProximityState
        
        // Get microphone data
        let micDB = currentMicDB
        
        // Get screen state
        let screen = screenState
        
        // Get foreground app
        let appName = foregroundAppName
        
        sensorLock.unlock()
        
        // Create phone data dictionary
        var sensorData: [String: Any] = [
            "phone": [
                "acc": [accX, accY, accZ],
                "gyro": [gyroX, gyroY, gyroZ],
                "orientation": orientationString,
                "proximity": proximity,
                "mic_db": micDB,
                "screen_state": screen,
                "foreground_app": appName
            ]
        ]
        
        // Merge watch data from WCSessionManager if available
        if let watchData = WCSessionManager.shared.getLatestWatchData() {
            sensorData["watch"] = watchData
        }
        
        // Emit via callback
        streamingCallback?(sensorData)
    }
    
    private func orientationToString(_ orientation: UIDeviceOrientation) -> String {
        switch orientation {
        case .portrait:
            return "portrait"
        case .portraitUpsideDown:
            return "portrait_upside_down"
        case .landscapeLeft:
            return "landscape_left"
        case .landscapeRight:
            return "landscape_right"
        case .faceUp:
            return "face_up"
        case .faceDown:
            return "face_down"
        default:
            return "unknown"
        }
    }
}

