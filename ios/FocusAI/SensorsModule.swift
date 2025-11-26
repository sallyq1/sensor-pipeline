import Foundation

@objc(SensorsModule)
class SensorsModule: RCTEventEmitter {
    
    override static func requiresMainQueueSetup() -> Bool {
        return true
    }
    
    override func supportedEvents() -> [String]! {
        return ["SensorData"]
    }
    
    @objc
    func startSensors() {
        PhoneSensorManager.shared.startStreaming { [weak self] phoneData in
            guard let self = self else { return }
            
            // Extract phone data from the dictionary
            // phoneData is ["phone": [...]], so we extract the phone part
            var phoneDict: [String: Any] = [:]
            if let phone = phoneData["phone"] as? [String: Any] {
                phoneDict = phone
            } else {
                // Fallback: use the whole dictionary if structure is different
                phoneDict = phoneData
            }
            
            // Get watch data from WCSessionManager
            let watchData = WCSessionManager.shared.lastPacket
            
            // Combine phone and watch data
            var combined: [String: Any] = [
                "phone": phoneDict
            ]
            
            if let watch = watchData {
                combined["watch"] = watch
            }
            
            // Send event to React Native
            self.sendEvent(withName: "SensorData", body: combined)
        }
    }
    
    @objc
    func stopSensors() {
        PhoneSensorManager.shared.stopStreaming()
    }
}

// MARK: - React Native Module Export

RCT_EXPORT_MODULE()

RCT_EXPORT_METHOD(startSensors) {
    // Methods are automatically exported via @objc annotation
    // This explicit export is for clarity
}

RCT_EXPORT_METHOD(stopSensors) {
    // Methods are automatically exported via @objc annotation
    // This explicit export is for clarity
}

