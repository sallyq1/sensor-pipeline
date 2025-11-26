import UIKit
import CoreMotion
import AVFoundation
import WatchConnectivity

class SensorTestHarnessViewController: UIViewController {
    
    // MARK: - UI Components
    private let scrollView = UIScrollView()
    private let stackView = UIStackView()
    
    // Section containers
    private let sectionA = UIView()
    private let sectionB = UIView()
    private let sectionC = UIView()
    private let sectionD = UIView()
    
    // Section labels
    private let labelA = UILabel()
    private let labelB = UILabel()
    private let labelC = UILabel()
    private let labelD = UILabel()
    
    // Status labels (will be updated dynamically)
    private var statusLabels: [UILabel] = []
    
    // MARK: - Diagnostic State
    private var lastUpdateTimes: [String: Date] = [:]
    private var updateTimer: Timer?
    private var phoneDataCallback: (([String: Any]) -> Void)?
    
    // MARK: - Lifecycle
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        startDiagnostics()
    }
    
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        startSensorStreaming()
    }
    
    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        stopSensorStreaming()
    }
    
    deinit {
        updateTimer?.invalidate()
        PhoneSensorManager.shared.stopStreaming()
    }
    
    // MARK: - UI Setup
    
    private func setupUI() {
        view.backgroundColor = .systemBackground
        
        // Configure scroll view
        scrollView.translatesAutoresizingMaskIntoConstraints = false
        scrollView.showsVerticalScrollIndicator = true
        view.addSubview(scrollView)
        
        // Configure stack view
        stackView.translatesAutoresizingMaskIntoConstraints = false
        stackView.axis = .vertical
        stackView.spacing = 20
        stackView.alignment = .fill
        scrollView.addSubview(stackView)
        
        // Setup sections
        setupSectionA()
        setupSectionB()
        setupSectionC()
        setupSectionD()
        
        // Add sections to stack view
        stackView.addArrangedSubview(sectionA)
        stackView.addArrangedSubview(sectionB)
        stackView.addArrangedSubview(sectionC)
        stackView.addArrangedSubview(sectionD)
        
        // Layout constraints
        NSLayoutConstraint.activate([
            scrollView.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            scrollView.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            scrollView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            scrollView.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            
            stackView.topAnchor.constraint(equalTo: scrollView.topAnchor, constant: 16),
            stackView.leadingAnchor.constraint(equalTo: scrollView.leadingAnchor, constant: 16),
            stackView.trailingAnchor.constraint(equalTo: scrollView.trailingAnchor, constant: -16),
            stackView.bottomAnchor.constraint(equalTo: scrollView.bottomAnchor, constant: -16),
            stackView.widthAnchor.constraint(equalTo: scrollView.widthAnchor, constant: -32)
        ])
    }
    
    private func setupSectionA() {
        sectionA.translatesAutoresizingMaskIntoConstraints = false
        sectionA.backgroundColor = .secondarySystemBackground
        sectionA.layer.cornerRadius = 8
        sectionA.layer.borderWidth = 1
        sectionA.layer.borderColor = UIColor.separator.cgColor
        
        labelA.translatesAutoresizingMaskIntoConstraints = false
        labelA.text = "SECTION A — DEVICE & PERMISSION STATUS"
        labelA.font = .boldSystemFont(ofSize: 16)
        labelA.textColor = .label
        sectionA.addSubview(labelA)
        
        let contentStack = UIStackView()
        contentStack.translatesAutoresizingMaskIntoConstraints = false
        contentStack.axis = .vertical
        contentStack.spacing = 8
        contentStack.alignment = .leading
        sectionA.addSubview(contentStack)
        
        // Status items for Section A
        let items = [
            "Motion permission",
            "Microphone permission",
            "Proximity enabled",
            "WCSession activated",
            "Watch reachable"
        ]
        
        for (index, item) in items.enumerated() {
            let label = createStatusLabel(tag: 100 + index, text: item)
            statusLabels.append(label)
            contentStack.addArrangedSubview(label)
        }
        
        NSLayoutConstraint.activate([
            labelA.topAnchor.constraint(equalTo: sectionA.topAnchor, constant: 12),
            labelA.leadingAnchor.constraint(equalTo: sectionA.leadingAnchor, constant: 12),
            labelA.trailingAnchor.constraint(equalTo: sectionA.trailingAnchor, constant: -12),
            
            contentStack.topAnchor.constraint(equalTo: labelA.bottomAnchor, constant: 12),
            contentStack.leadingAnchor.constraint(equalTo: sectionA.leadingAnchor, constant: 12),
            contentStack.trailingAnchor.constraint(equalTo: sectionA.trailingAnchor, constant: -12),
            contentStack.bottomAnchor.constraint(equalTo: sectionA.bottomAnchor, constant: -12)
        ])
    }
    
    private func setupSectionB() {
        sectionB.translatesAutoresizingMaskIntoConstraints = false
        sectionB.backgroundColor = .secondarySystemBackground
        sectionB.layer.cornerRadius = 8
        sectionB.layer.borderWidth = 1
        sectionB.layer.borderColor = UIColor.separator.cgColor
        
        labelB.translatesAutoresizingMaskIntoConstraints = false
        labelB.text = "SECTION B — PHONE SENSORS (Live values)"
        labelB.font = .boldSystemFont(ofSize: 16)
        labelB.textColor = .label
        sectionB.addSubview(labelB)
        
        let contentStack = UIStackView()
        contentStack.translatesAutoresizingMaskIntoConstraints = false
        contentStack.axis = .vertical
        contentStack.spacing = 8
        contentStack.alignment = .leading
        sectionB.addSubview(contentStack)
        
        let items = [
            "Accelerometer",
            "Gyroscope",
            "Orientation",
            "Proximity state",
            "Mic decibels",
            "Foreground app",
            "Screen state"
        ]
        
        for (index, item) in items.enumerated() {
            let label = createStatusLabel(tag: 200 + index, text: item)
            statusLabels.append(label)
            contentStack.addArrangedSubview(label)
        }
        
        NSLayoutConstraint.activate([
            labelB.topAnchor.constraint(equalTo: sectionB.topAnchor, constant: 12),
            labelB.leadingAnchor.constraint(equalTo: sectionB.leadingAnchor, constant: 12),
            labelB.trailingAnchor.constraint(equalTo: sectionB.trailingAnchor, constant: -12),
            
            contentStack.topAnchor.constraint(equalTo: labelB.bottomAnchor, constant: 12),
            contentStack.leadingAnchor.constraint(equalTo: sectionB.leadingAnchor, constant: 12),
            contentStack.trailingAnchor.constraint(equalTo: sectionB.trailingAnchor, constant: -12),
            contentStack.bottomAnchor.constraint(equalTo: sectionB.bottomAnchor, constant: -12)
        ])
    }
    
    private func setupSectionC() {
        sectionC.translatesAutoresizingMaskIntoConstraints = false
        sectionC.backgroundColor = .secondarySystemBackground
        sectionC.layer.cornerRadius = 8
        sectionC.layer.borderWidth = 1
        sectionC.layer.borderColor = UIColor.separator.cgColor
        
        labelC.translatesAutoresizingMaskIntoConstraints = false
        labelC.text = "SECTION C — WATCH SENSORS (Live values via WCSession)"
        labelC.font = .boldSystemFont(ofSize: 16)
        labelC.textColor = .label
        sectionC.addSubview(labelC)
        
        let contentStack = UIStackView()
        contentStack.translatesAutoresizingMaskIntoConstraints = false
        contentStack.axis = .vertical
        contentStack.spacing = 8
        contentStack.alignment = .leading
        sectionC.addSubview(contentStack)
        
        let items = [
            "Watch accelerometer",
            "Watch gyroscope",
            "Heart rate",
            "HRV"
        ]
        
        for (index, item) in items.enumerated() {
            let label = createStatusLabel(tag: 300 + index, text: item)
            statusLabels.append(label)
            contentStack.addArrangedSubview(label)
        }
        
        NSLayoutConstraint.activate([
            labelC.topAnchor.constraint(equalTo: sectionC.topAnchor, constant: 12),
            labelC.leadingAnchor.constraint(equalTo: sectionC.leadingAnchor, constant: 12),
            labelC.trailingAnchor.constraint(equalTo: sectionC.trailingAnchor, constant: -12),
            
            contentStack.topAnchor.constraint(equalTo: labelC.bottomAnchor, constant: 12),
            contentStack.leadingAnchor.constraint(equalTo: sectionC.leadingAnchor, constant: 12),
            contentStack.trailingAnchor.constraint(equalTo: sectionC.trailingAnchor, constant: -12),
            contentStack.bottomAnchor.constraint(equalTo: sectionC.bottomAnchor, constant: -12)
        ])
    }
    
    private func setupSectionD() {
        sectionD.translatesAutoresizingMaskIntoConstraints = false
        sectionD.backgroundColor = .secondarySystemBackground
        sectionD.layer.cornerRadius = 8
        sectionD.layer.borderWidth = 1
        sectionD.layer.borderColor = UIColor.separator.cgColor
        
        labelD.translatesAutoresizingMaskIntoConstraints = false
        labelD.text = "SECTION D — TEST GUIDE (Instructions)"
        labelD.font = .boldSystemFont(ofSize: 16)
        labelD.textColor = .label
        sectionD.addSubview(labelD)
        
        let contentStack = UIStackView()
        contentStack.translatesAutoresizingMaskIntoConstraints = false
        contentStack.axis = .vertical
        contentStack.spacing = 8
        contentStack.alignment = .leading
        sectionD.addSubview(contentStack)
        
        let instructions = [
            "1. Tilt the phone left/right — accelerometer X should change",
            "2. Rotate phone — gyro Z should change",
            "3. Cover the top of the phone — proximity should turn TRUE",
            "4. Speak near microphone — mic_db should increase",
            "5. Rotate wrist while wearing the watch — watch IMU updates should appear",
            "6. Walk around — HR should update",
            "7. Lock iPhone screen — screen state should show 'inactive'",
            "8. Open Safari — foreground app name should show Safari",
            "9. Move watch out of range — watch data should stop temporarily (expected)",
            "10. Return watch near iPhone — WCSession should reconnect"
        ]
        
        for instruction in instructions {
            let label = UILabel()
            label.translatesAutoresizingMaskIntoConstraints = false
            label.text = instruction
            label.font = .monospacedSystemFont(ofSize: 12, weight: .regular)
            label.textColor = .secondaryLabel
            label.numberOfLines = 0
            contentStack.addArrangedSubview(label)
        }
        
        NSLayoutConstraint.activate([
            labelD.topAnchor.constraint(equalTo: sectionD.topAnchor, constant: 12),
            labelD.leadingAnchor.constraint(equalTo: sectionD.leadingAnchor, constant: 12),
            labelD.trailingAnchor.constraint(equalTo: sectionD.trailingAnchor, constant: -12),
            
            contentStack.topAnchor.constraint(equalTo: labelD.bottomAnchor, constant: 12),
            contentStack.leadingAnchor.constraint(equalTo: sectionD.leadingAnchor, constant: 12),
            contentStack.trailingAnchor.constraint(equalTo: sectionD.trailingAnchor, constant: -12),
            contentStack.bottomAnchor.constraint(equalTo: sectionD.bottomAnchor, constant: -12)
        ])
    }
    
    private func createStatusLabel(tag: Int, text: String) -> UILabel {
        let label = UILabel()
        label.tag = tag
        label.text = "[WAIT] \(text): —"
        label.font = .monospacedSystemFont(ofSize: 12, weight: .regular)
        label.textColor = .systemYellow
        label.numberOfLines = 0
        return label
    }
    
    // MARK: - Sensor Streaming
    
    private func startSensorStreaming() {
        // Start phone sensor streaming
        PhoneSensorManager.shared.startStreaming { [weak self] data in
            self?.handlePhoneData(data)
        }
        
        // Set up watch data callback
        WCSessionManager.shared.setWatchDataCallback { [weak self] watchData in
            self?.handleWatchData(watchData)
        }
        
        // Also check for latest watch data periodically
        Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            if let watchData = WCSessionManager.shared.lastPacket {
                self?.handleWatchData(watchData)
            }
        }
    }
    
    private func stopSensorStreaming() {
        PhoneSensorManager.shared.stopStreaming()
    }
    
    // MARK: - Data Handling
    
    private func handlePhoneData(_ data: [String: Any]) {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            
            // Log to console
            let timestamp = DateFormatter.logFormatter.string(from: Date())
            print("[\(timestamp)] Phone Data: \(data)")
            
            // Update last update time
            self.lastUpdateTimes["phone"] = Date()
            
            // Parse and update UI
            if let phone = data["phone"] as? [String: Any] {
                self.updatePhoneSensors(phone)
            } else {
                print("[\(timestamp)] ⚠️ Phone data missing 'phone' key. Keys: \(data.keys)")
            }
            
            // Also check for watch data in the combined packet
            if let watch = data["watch"] as? [String: Any] {
                self.handleWatchData(watch)
            }
        }
    }
    
    private func handleWatchData(_ data: [String: Any]) {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            
            // Log to console
            let timestamp = DateFormatter.logFormatter.string(from: Date())
            print("[\(timestamp)] Watch Data: \(data)")
            
            // Update last update time
            self.lastUpdateTimes["watch"] = Date()
            
            // Check if data has the expected structure
            if data.isEmpty {
                print("[\(timestamp)] ⚠️ Watch data is empty")
                return
            }
            
            // Update watch sensors
            self.updateWatchSensors(data)
        }
    }
    
    // MARK: - UI Updates
    
    private func updatePhoneSensors(_ phone: [String: Any]) {
        // Accelerometer
        if let acc = phone["acc"] as? [Double], acc.count == 3 {
            updateLabel(tag: 200, status: .pass, text: "Accelerometer: [\(formatDouble(acc[0])), \(formatDouble(acc[1])), \(formatDouble(acc[2]))]")
            lastUpdateTimes["phone_acc"] = Date()
        } else {
            updateLabel(tag: 200, status: .error, text: "Accelerometer: No data")
        }
        
        // Gyroscope
        if let gyro = phone["gyro"] as? [Double], gyro.count == 3 {
            updateLabel(tag: 201, status: .pass, text: "Gyroscope: [\(formatDouble(gyro[0])), \(formatDouble(gyro[1])), \(formatDouble(gyro[2]))]")
            lastUpdateTimes["phone_gyro"] = Date()
        } else {
            updateLabel(tag: 201, status: .error, text: "Gyroscope: No data")
        }
        
        // Orientation
        if let orientation = phone["orientation"] as? String {
            updateLabel(tag: 202, status: .pass, text: "Orientation: \(orientation)")
        } else {
            updateLabel(tag: 202, status: .wait, text: "Orientation: —")
        }
        
        // Proximity
        if let proximity = phone["proximity"] as? Bool {
            updateLabel(tag: 203, status: .pass, text: "Proximity state: \(proximity ? "TRUE" : "FALSE")")
        } else {
            updateLabel(tag: 203, status: .wait, text: "Proximity state: —")
        }
        
        // Mic dB
        if let micDB = phone["mic_db"] as? Double {
            updateLabel(tag: 204, status: .pass, text: "Mic decibels: \(formatDouble(micDB)) dB")
            lastUpdateTimes["phone_mic"] = Date()
        } else {
            updateLabel(tag: 204, status: .wait, text: "Mic decibels: —")
        }
        
        // Foreground app
        if let appName = phone["foreground_app"] as? String {
            updateLabel(tag: 205, status: .pass, text: "Foreground app: \(appName)")
        } else {
            updateLabel(tag: 205, status: .wait, text: "Foreground app: —")
        }
        
        // Screen state
        if let screenState = phone["screen_state"] as? String {
            updateLabel(tag: 206, status: .pass, text: "Screen state: \(screenState)")
        } else {
            updateLabel(tag: 206, status: .wait, text: "Screen state: —")
        }
    }
    
    private func updateWatchSensors(_ watch: [String: Any]) {
        // Watch accelerometer
        if let acc = watch["acc"] as? [Double], acc.count == 3 {
            updateLabel(tag: 300, status: .pass, text: "Watch accelerometer: [\(formatDouble(acc[0])), \(formatDouble(acc[1])), \(formatDouble(acc[2]))]")
            lastUpdateTimes["watch_acc"] = Date()
        } else {
            updateLabel(tag: 300, status: .wait, text: "Watch accelerometer: No data")
        }
        
        // Watch gyroscope
        if let gyro = watch["gyro"] as? [Double], gyro.count == 3 {
            updateLabel(tag: 301, status: .pass, text: "Watch gyroscope: [\(formatDouble(gyro[0])), \(formatDouble(gyro[1])), \(formatDouble(gyro[2]))]")
            lastUpdateTimes["watch_gyro"] = Date()
        } else {
            updateLabel(tag: 301, status: .wait, text: "Watch gyroscope: No data")
        }
        
        // Heart rate
        if let hr = watch["hr"] as? Int, hr > 0 {
            updateLabel(tag: 302, status: .pass, text: "Heart rate: \(hr) bpm")
            lastUpdateTimes["watch_hr"] = Date()
        } else if watch["hr"] != nil {
            updateLabel(tag: 302, status: .wait, text: "Heart rate: —")
        } else {
            updateLabel(tag: 302, status: .wait, text: "Heart rate: No data")
        }
        
        // HRV
        if let hrv = watch["hrv"] as? Double {
            updateLabel(tag: 303, status: .pass, text: "HRV: \(formatDouble(hrv)) ms")
            lastUpdateTimes["watch_hrv"] = Date()
        } else if watch["hrv"] is NSNull {
            updateLabel(tag: 303, status: .wait, text: "HRV: Not available")
        } else {
            updateLabel(tag: 303, status: .wait, text: "HRV: No data")
        }
    }
    
    private func formatDouble(_ value: Double) -> String {
        return String(format: "%.3f", value)
    }
    
    // MARK: - Diagnostics
    
    private func startDiagnostics() {
        updateTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            self?.updateDiagnostics()
        }
    }
    
    private func updateDiagnostics() {
        // Update Section A - Permissions & Status
        updatePermissionStatus()
        
        // Check for stale updates
        checkStaleUpdates()
        
        // Auto-scroll to bottom
        let bottomOffset = CGPoint(x: 0, y: scrollView.contentSize.height - scrollView.bounds.height + scrollView.contentInset.bottom)
        if bottomOffset.y > 0 {
            scrollView.setContentOffset(bottomOffset, animated: true)
        }
    }
    
    private func updatePermissionStatus() {
        // Motion permission (always available on iOS, but check if active)
        let motionActive = CMMotionManager().isAccelerometerAvailable || CMMotionManager().isGyroAvailable
        updateLabel(tag: 100, status: motionActive ? .pass : .error, text: "Motion permission: \(motionActive ? "granted" : "denied")")
        
        // Microphone permission
        let micStatus = AVAudioSession.sharedInstance().recordPermission
        let micGranted = micStatus == .granted
        updateLabel(tag: 101, status: micGranted ? .pass : (micStatus == .denied ? .error : .wait), text: "Microphone permission: \(micStatus == .granted ? "granted" : micStatus == .denied ? "denied" : "not determined")")
        
        // Proximity enabled
        let proximityEnabled = UIDevice.current.isProximityMonitoringEnabled
        updateLabel(tag: 102, status: proximityEnabled ? .pass : .wait, text: "Proximity enabled: \(proximityEnabled ? "yes" : "no")")
        
        // WCSession activated
        var wcActivated = false
        if WCSession.isSupported() {
            let session = WCSession.default
            wcActivated = session.activationState == .activated
        }
        updateLabel(tag: 103, status: wcActivated ? .pass : .wait, text: "WCSession activated: \(wcActivated ? "yes" : "no")")
        
        // Watch reachable
        let watchReachable = WCSessionManager.shared.isWatchReachable()
        updateLabel(tag: 104, status: watchReachable ? .pass : .wait, text: "Watch reachable: \(watchReachable ? "yes" : "no")")
    }
    
    private func checkStaleUpdates() {
        let now = Date()
        let staleThreshold: TimeInterval = 1.0 // 1 second
        
        // Check phone sensors
        if let lastUpdate = lastUpdateTimes["phone_acc"], now.timeIntervalSince(lastUpdate) > staleThreshold {
            updateLabel(tag: 200, status: .error, text: "Accelerometer: No updates in \(Int(now.timeIntervalSince(lastUpdate)))s")
        }
        
        if let lastUpdate = lastUpdateTimes["phone_gyro"], now.timeIntervalSince(lastUpdate) > staleThreshold {
            updateLabel(tag: 201, status: .error, text: "Gyroscope: No updates in \(Int(now.timeIntervalSince(lastUpdate)))s")
        }
        
        if let lastUpdate = lastUpdateTimes["phone_mic"], now.timeIntervalSince(lastUpdate) > staleThreshold {
            updateLabel(tag: 204, status: .error, text: "Mic decibels: No updates in \(Int(now.timeIntervalSince(lastUpdate)))s")
        }
        
        // Check watch sensors
        if let lastUpdate = lastUpdateTimes["watch"], now.timeIntervalSince(lastUpdate) > staleThreshold {
            updateLabel(tag: 300, status: .error, text: "Watch accelerometer: No updates in \(Int(now.timeIntervalSince(lastUpdate)))s")
            updateLabel(tag: 301, status: .error, text: "Watch gyroscope: No updates in \(Int(now.timeIntervalSince(lastUpdate)))s")
        }
        
        if let lastUpdate = lastUpdateTimes["watch_hr"], now.timeIntervalSince(lastUpdate) > 3.0 {
            updateLabel(tag: 302, status: .error, text: "Heart rate: No updates in \(Int(now.timeIntervalSince(lastUpdate)))s")
        }
    }
    
    private enum Status {
        case pass
        case wait
        case error
    }
    
    private func updateLabel(tag: Int, status: Status, text: String) {
        guard let label = view.viewWithTag(tag) as? UILabel else { return }
        
        let prefix: String
        let color: UIColor
        
        switch status {
        case .pass:
            prefix = "[PASS]"
            color = .systemGreen
        case .wait:
            prefix = "[WAIT]"
            color = .systemYellow
        case .error:
            prefix = "[ERROR]"
            color = .systemRed
        }
        
        label.text = "\(prefix) \(text)"
        label.textColor = color
    }
}

// MARK: - DateFormatter Extension

extension DateFormatter {
    static let logFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm:ss.SSS"
        return formatter
    }()
}

