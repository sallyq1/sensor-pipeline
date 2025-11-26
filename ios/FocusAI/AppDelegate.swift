import UIKit

// Note: For React Native projects, this AppDelegate may need to be integrated
// with the existing React Native AppDelegate. This is a standalone version
// that can be used for testing or integrated into the main AppDelegate.

class AppDelegate: UIResponder, UIApplicationDelegate {
    
    var window: UIWindow?
    
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        
        // Check for test harness activation
        let useTestHarness = shouldUseTestHarness()
        
        if useTestHarness {
            // Load test harness as root view controller
            window = UIWindow(frame: UIScreen.main.bounds)
            let testHarness = SensorTestHarnessViewController()
            let navController = UINavigationController(rootViewController: testHarness)
            window?.rootViewController = navController
            window?.makeKeyAndVisible()
            
            print("🔧 Test Harness Activated")
            return true
        }
        
        // Otherwise, proceed with normal React Native initialization
        // React Native will handle the window setup
        return true
    }
    
    // MARK: - Test Harness Activation
    
    private func shouldUseTestHarness() -> Bool {
        // Check environment variable
        if ProcessInfo.processInfo.environment["TEST_HARNESS"] == "1" {
            return true
        }
        
        // Check for "D" key press on physical keyboard
        // This is handled via key commands in the view controller
        return false
    }
    
    // MARK: - Key Commands (for physical keyboard "D" key)
    
    override var keyCommands: [UIKeyCommand]? {
        return [
            UIKeyCommand(
                input: "d",
                modifierFlags: [],
                action: #selector(activateTestHarness),
                discoverabilityTitle: "Activate Test Harness"
            )
        ]
    }
    
    @objc private func activateTestHarness() {
        guard let window = window else { return }
        
        // Only activate if not already showing test harness
        if !(window.rootViewController is UINavigationController) ||
           !((window.rootViewController as? UINavigationController)?.topViewController is SensorTestHarnessViewController) {
            let testHarness = SensorTestHarnessViewController()
            let navController = UINavigationController(rootViewController: testHarness)
            window.rootViewController = navController
            print("🔧 Test Harness Activated via 'D' key")
        }
    }
}

// MARK: - Helper Function for React Native Integration
// If you have an existing React Native AppDelegate, add this function to it:

/*
 func activateTestHarnessIfNeeded() {
     // Check environment variable
     if ProcessInfo.processInfo.environment["TEST_HARNESS"] == "1" {
         let testHarness = SensorTestHarnessViewController()
         let navController = UINavigationController(rootViewController: testHarness)
         self.window?.rootViewController = navController
         print("🔧 Test Harness Activated")
     }
 }
 
 // Call this in didFinishLaunchingWithOptions before React Native setup
 */

