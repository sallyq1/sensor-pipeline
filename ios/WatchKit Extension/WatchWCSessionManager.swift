import Foundation
import WatchConnectivity

class WatchWCSessionManager: NSObject {
    static let shared = WatchWCSessionManager()
    
    private var session: WCSession?
    private var isStreaming = false
    private var streamingTimer: Timer?
    private var latestSensorData: [String: Any]?
    private let dataLock = NSLock()
    
    private override init() {
        super.init()
        activateSession()
    }
    
    deinit {
        stopStreaming()
    }
    
    // MARK: - WCSession Activation
    
    private func activateSession() {
        guard WCSession.isSupported() else {
            print("WCSession is not supported on this device")
            return
        }
        
        session = WCSession.default
        session?.delegate = self
        session?.activate()
    }
    
    // MARK: - Public API
    
    /// Starts streaming sensor data to iPhone every 100ms (10 times/sec)
    func startStreaming() {
        guard !isStreaming else {
            print("Already streaming to iPhone")
            return
        }
        
        isStreaming = true
        
        // Start timer to send data every 100ms (10 times/sec)
        // Will only send if iPhone is reachable (checked in sendLatestData)
        streamingTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            self?.sendLatestData()
        }
    }
    
    /// Stops streaming sensor data to iPhone
    func stopStreaming() {
        guard isStreaming else { return }
        
        isStreaming = false
        streamingTimer?.invalidate()
        streamingTimer = nil
    }
    
    /// Updates the latest sensor data (called by WatchSensorManager)
    func updateSensorData(_ data: [String: Any]) {
        dataLock.lock()
        latestSensorData = data
        dataLock.unlock()
    }
    
    /// Checks if iPhone is reachable
    func isPhoneReachable() -> Bool {
        return session?.isReachable ?? false
    }
    
    // MARK: - Data Sending
    
    private func sendLatestData() {
        guard isStreaming else { return }
        guard session?.isReachable ?? false else { return }
        
        dataLock.lock()
        guard let sensorData = latestSensorData else {
            dataLock.unlock()
            return
        }
        dataLock.unlock()
        
        // Create payload with watch data
        let payload: [String: Any] = [
            "watch": sensorData
        ]
        
        // Check payload size (must be < 40KB)
        if let jsonData = try? JSONSerialization.data(withJSONObject: payload) {
            let sizeInBytes = jsonData.count
            let sizeInKB = Double(sizeInBytes) / 1024.0
            
            if sizeInKB >= 40.0 {
                print("Warning: Payload size (\(sizeInKB) KB) exceeds 40KB limit")
                // Could implement data compression or splitting here if needed
                return
            }
            
            // Send message to iPhone
            session?.sendMessage(payload, replyHandler: nil) { error in
                if let error = error {
                    print("Error sending message to iPhone: \(error.localizedDescription)")
                }
            }
        } else {
            print("Error: Failed to serialize payload to JSON")
        }
    }
}

// MARK: - WCSessionDelegate

extension WatchWCSessionManager: WCSessionDelegate {
    func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {
        if let error = error {
            print("WCSession activation failed: \(error.localizedDescription)")
        } else {
            print("WCSession activated with state: \(activationState.rawValue)")
            
            // Check if iPhone is reachable
            if session.isReachable {
                print("iPhone is reachable")
            } else {
                print("iPhone is not reachable")
            }
        }
    }
    
    func sessionReachabilityDidChange(_ session: WCSession) {
        if session.isReachable {
            print("iPhone became reachable")
            // Optionally restart streaming if it was stopped due to unreachability
            if !isStreaming {
                startStreaming()
            }
        } else {
            print("iPhone became unreachable")
        }
    }
}

