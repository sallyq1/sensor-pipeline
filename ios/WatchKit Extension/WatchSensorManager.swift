import Foundation
import CoreMotion
import HealthKit

class WatchSensorManager {
    static let shared = WatchSensorManager()
    
    // Motion manager for accelerometer and gyroscope
    private let motionManager = CMMotionManager()
    
    // HealthKit store
    private let healthStore = HKHealthStore()
    
    // Streaming state
    private var isStreaming = false
    private var streamingCallback: (([String: Any]) -> Void)?
    
    // Current sensor values
    private var currentDeviceMotion: CMDeviceMotion?
    private var currentHeartRate: Int = 0
    private var currentHRV: Double? = nil
    
    // HealthKit queries
    private var heartRateQuery: HKAnchoredObjectQuery?
    private var hrvQuery: HKAnchoredObjectQuery?
    
    // Lock for thread safety
    private let sensorLock = NSLock()
    
    private init() {
        // Initialize motion manager
        motionManager.deviceMotionUpdateInterval = 0.02 // 50Hz (1/50 = 0.02 seconds)
    }
    
    deinit {
        stopStreaming()
    }
    
    // MARK: - HealthKit Setup
    
    private func requestHealthKitPermissions(completion: @escaping (Bool) -> Void) {
        guard HKHealthStore.isHealthDataAvailable() else {
            print("HealthKit is not available on this device")
            completion(false)
            return
        }
        
        let readTypes: Set<HKObjectType> = [
            HKObjectType.quantityType(forIdentifier: .heartRate)!,
            HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN)!
        ]
        
        healthStore.requestAuthorization(toShare: nil, read: readTypes) { success, error in
            if let error = error {
                print("HealthKit authorization error: \(error)")
            }
            DispatchQueue.main.async {
                completion(success)
            }
        }
    }
    
    // MARK: - Heart Rate Streaming
    
    private func startHeartRateStreaming() {
        guard let heartRateType = HKQuantityType.quantityType(forIdentifier: .heartRate) else {
            print("Heart rate type not available")
            return
        }
        
        // Create anchored query for heart rate
        let query = HKAnchoredObjectQuery(
            type: heartRateType,
            predicate: nil,
            anchor: nil,
            limit: HKObjectQueryNoLimit
        ) { [weak self] query, samples, deletedObjects, anchor, error in
            guard let self = self else { return }
            
            if let error = error {
                print("Heart rate query error: \(error)")
                return
            }
            
            if let samples = samples as? [HKQuantitySample] {
                if let mostRecent = samples.last {
                    let heartRateUnit = HKUnit.count().unitDivided(by: HKUnit.minute())
                    let heartRateValue = mostRecent.quantity.doubleValue(for: heartRateUnit)
                    
                    self.sensorLock.lock()
                    self.currentHeartRate = Int(heartRateValue)
                    self.sensorLock.unlock()
                }
            }
        }
        
        // Update handler for continuous updates
        query.updateHandler = { [weak self] query, samples, deletedObjects, anchor, error in
            guard let self = self else { return }
            
            if let error = error {
                print("Heart rate update error: \(error)")
                return
            }
            
            if let samples = samples as? [HKQuantitySample] {
                if let mostRecent = samples.last {
                    let heartRateUnit = HKUnit.count().unitDivided(by: HKUnit.minute())
                    let heartRateValue = mostRecent.quantity.doubleValue(for: heartRateUnit)
                    
                    self.sensorLock.lock()
                    self.currentHeartRate = Int(heartRateValue)
                    self.sensorLock.unlock()
                }
            }
        }
        
        heartRateQuery = query
        healthStore.execute(query)
    }
    
    private func stopHeartRateStreaming() {
        if let query = heartRateQuery {
            healthStore.stop(query)
            heartRateQuery = nil
        }
    }
    
    // MARK: - HRV Streaming
    
    private func startHRVStreaming() {
        guard let hrvType = HKQuantityType.quantityType(forIdentifier: .heartRateVariabilitySDNN) else {
            print("HRV type not available")
            return
        }
        
        // Create anchored query for HRV
        let query = HKAnchoredObjectQuery(
            type: hrvType,
            predicate: nil,
            anchor: nil,
            limit: HKObjectQueryNoLimit
        ) { [weak self] query, samples, deletedObjects, anchor, error in
            guard let self = self else { return }
            
            if let error = error {
                print("HRV query error: \(error)")
                return
            }
            
            if let samples = samples as? [HKQuantitySample] {
                if let mostRecent = samples.last {
                    let hrvUnit = HKUnit.secondUnit(with: .milli)
                    let hrvValue = mostRecent.quantity.doubleValue(for: hrvUnit)
                    
                    self.sensorLock.lock()
                    self.currentHRV = hrvValue
                    self.sensorLock.unlock()
                }
            }
        }
        
        // Update handler for continuous updates
        query.updateHandler = { [weak self] query, samples, deletedObjects, anchor, error in
            guard let self = self else { return }
            
            if let error = error {
                print("HRV update error: \(error)")
                return
            }
            
            if let samples = samples as? [HKQuantitySample] {
                if let mostRecent = samples.last {
                    let hrvUnit = HKUnit.secondUnit(with: .milli)
                    let hrvValue = mostRecent.quantity.doubleValue(for: hrvUnit)
                    
                    self.sensorLock.lock()
                    self.currentHRV = hrvValue
                    self.sensorLock.unlock()
                }
            }
        }
        
        hrvQuery = query
        healthStore.execute(query)
    }
    
    private func stopHRVStreaming() {
        if let query = hrvQuery {
            healthStore.stop(query)
            hrvQuery = nil
        }
    }
    
    // MARK: - Motion Sensors
    
    private func startMotionSensors() {
        guard motionManager.isDeviceMotionAvailable else {
            print("Device motion is not available")
            return
        }
        
        // Start device motion updates at 50Hz
        motionManager.startDeviceMotionUpdates(to: OperationQueue.main) { [weak self] (motion, error) in
            guard let self = self, let motion = motion else {
                if let error = error {
                    print("Device motion error: \(error)")
                }
                return
            }
            
            self.sensorLock.lock()
            self.currentDeviceMotion = motion
            self.sensorLock.unlock()
            
            // Emit data immediately when motion updates (at 50Hz)
            self.collectAndEmitSensorData()
        }
    }
    
    private func stopMotionSensors() {
        motionManager.stopDeviceMotionUpdates()
    }
    
    // MARK: - Public API
    
    func startStreaming(callback: @escaping ([String: Any]) -> Void) {
        guard !isStreaming else {
            print("Already streaming")
            return
        }
        
        isStreaming = true
        streamingCallback = callback
        
        // Start WCSessionManager streaming to iPhone
        WatchWCSessionManager.shared.startStreaming()
        
        // Request HealthKit permissions first
        requestHealthKitPermissions { [weak self] success in
            guard let self = self else { return }
            
            if success {
                // Start HealthKit queries
                self.startHeartRateStreaming()
                self.startHRVStreaming()
            } else {
                print("HealthKit permission denied")
            }
            
            // Start motion sensors regardless of HealthKit status
            self.startMotionSensors()
        }
    }
    
    func stopStreaming() {
        guard isStreaming else { return }
        
        isStreaming = false
        streamingCallback = nil
        
        // Stop WCSessionManager streaming
        WatchWCSessionManager.shared.stopStreaming()
        
        // Stop all sensors
        stopMotionSensors()
        stopHeartRateStreaming()
        stopHRVStreaming()
    }
    
    // MARK: - Data Collection
    
    private func collectAndEmitSensorData() {
        guard isStreaming else { return }
        
        sensorLock.lock()
        
        // Collect accelerometer data from device motion
        var accX: Double = 0.0
        var accY: Double = 0.0
        var accZ: Double = 0.0
        
        if let motion = currentDeviceMotion {
            let acceleration = motion.userAcceleration
            accX = acceleration.x
            accY = acceleration.y
            accZ = acceleration.z
        }
        
        // Collect gyroscope data from device motion
        var gyroX: Double = 0.0
        var gyroY: Double = 0.0
        var gyroZ: Double = 0.0
        
        if let motion = currentDeviceMotion {
            let rotationRate = motion.rotationRate
            gyroX = rotationRate.x
            gyroY = rotationRate.y
            gyroZ = rotationRate.z
        }
        
        // Get heart rate
        let hr = currentHeartRate
        
        // Get HRV (may be nil)
        let hrv = currentHRV
        
        sensorLock.unlock()
        
        // Create watch data dictionary
        var watchData: [String: Any] = [
            "acc": [accX, accY, accZ],
            "gyro": [gyroX, gyroY, gyroZ],
            "hr": hr
        ]
        
        // Add HRV if available
        if let hrvValue = hrv {
            watchData["hrv"] = hrvValue
        } else {
            watchData["hrv"] = NSNull()
        }
        
        // Update WatchWCSessionManager with latest data (will be sent every 100ms)
        WatchWCSessionManager.shared.updateSensorData(watchData)
        
        // Also emit via callback if provided (for local use)
        if let callback = streamingCallback {
            let sensorData: [String: Any] = [
                "watch": watchData
            ]
            callback(sensorData)
        }
    }
}

