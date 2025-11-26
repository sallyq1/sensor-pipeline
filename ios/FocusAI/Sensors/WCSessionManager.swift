import Foundation
import WatchConnectivity

class WCSessionManager: NSObject {
    static let shared = WCSessionManager()
    
    private var session: WCSession?
    private var watchDataCallback: (([String: Any]) -> Void)?
    private var latestWatchData: [String: Any]?
    private let dataLock = NSLock()
    
    private override init() {
        super.init()
        activateSession()
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
    
    /// Sets a callback to receive watch data packets
    /// The callback will be called whenever new watch data is received
    func setWatchDataCallback(_ callback: @escaping ([String: Any]) -> Void) {
        dataLock.lock()
        watchDataCallback = callback
        dataLock.unlock()
    }
    
    /// Gets the latest watch data (if available)
    func getLatestWatchData() -> [String: Any]? {
        dataLock.lock()
        let data = latestWatchData
        dataLock.unlock()
        return data
    }
    
    /// Public property to access latest watch data packet
    var lastPacket: [String: Any]? {
        get {
            dataLock.lock()
            let data = latestWatchData
            dataLock.unlock()
            return data
        }
    }
    
    /// Public property to access latest watch data (alias for lastPacket)
    var watchData: [String: Any]? {
        get {
            return lastPacket
        }
    }
    
    /// Checks if watch is reachable
    func isWatchReachable() -> Bool {
        return session?.isReachable ?? false
    }
    
    /// Checks if watch app is installed
    func isWatchAppInstalled() -> Bool {
        return session?.isWatchAppInstalled ?? false
    }
}

// MARK: - WCSessionDelegate

extension WCSessionManager: WCSessionDelegate {
    func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {
        if let error = error {
            print("WCSession activation failed: \(error.localizedDescription)")
        } else {
            print("WCSession activated with state: \(activationState.rawValue)")
        }
    }
    
    func sessionDidBecomeInactive(_ session: WCSession) {
        print("WCSession became inactive")
    }
    
    func sessionDidDeactivate(_ session: WCSession) {
        print("WCSession deactivated")
        // Reactivate session
        session.activate()
    }
    
    // MARK: - Message Reception
    
    func session(_ session: WCSession, didReceiveMessage message: [String : Any]) {
        handleWatchData(message)
    }
    
    func session(_ session: WCSession, didReceiveMessage message: [String : Any], replyHandler: @escaping ([String : Any]) -> Void) {
        handleWatchData(message)
        // Send empty reply
        replyHandler([:])
    }
    
    // MARK: - Application Context Reception
    
    func session(_ session: WCSession, didReceiveApplicationContext applicationContext: [String : Any]) {
        handleWatchData(applicationContext)
    }
    
    // MARK: - User Info Reception
    
    func session(_ session: WCSession, didReceiveUserInfo userInfo: [String : Any] = [:]) {
        handleWatchData(userInfo)
    }
    
    // MARK: - File Transfer Reception
    
    func session(_ session: WCSession, didReceive file: WCSessionFile) {
        // Handle file transfer if needed
        print("Received file: \(file.fileURL)")
    }
    
    // MARK: - Helper Methods
    
    private func handleWatchData(_ data: [String: Any]) {
        // Extract watch data from the message
        if let watchData = data["watch"] as? [String: Any] {
            dataLock.lock()
            latestWatchData = watchData
            dataLock.unlock()
            
            // Notify callback
            dataLock.lock()
            if let callback = watchDataCallback {
                dataLock.unlock()
                callback(watchData)
            } else {
                dataLock.unlock()
            }
        } else if data.keys.contains("watch") {
            // Handle case where watch data might be at root level
            dataLock.lock()
            latestWatchData = data
            dataLock.unlock()
            
            dataLock.lock()
            if let callback = watchDataCallback {
                dataLock.unlock()
                callback(data)
            } else {
                dataLock.unlock()
            }
        }
    }
}

