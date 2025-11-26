import { useState, useEffect, useRef } from 'react';
import { NativeModules, NativeEventEmitter } from 'react-native';

const { SensorsModule } = NativeModules;

/**
 * React Native hook for accessing sensor data from phone and watch
 * 
 * @returns {Object} Sensor data object with:
 *   - phoneAcc: [x, y, z] accelerometer data from phone
 *   - phoneGyro: [x, y, z] gyroscope data from phone
 *   - phoneMicDB: number - microphone decibel level from phone
 *   - watchAcc: [x, y, z] accelerometer data from watch (or null)
 *   - watchGyro: [x, y, z] gyroscope data from watch (or null)
 *   - watchHR: number - heart rate from watch (or null)
 *   - watchHRV: number - heart rate variability from watch (or null)
 */
export const useSensors = () => {
  // State for sensor values
  const [phoneAcc, setPhoneAcc] = useState([0, 0, 0]);
  const [phoneGyro, setPhoneGyro] = useState([0, 0, 0]);
  const [phoneMicDB, setPhoneMicDB] = useState(-160);
  const [watchAcc, setWatchAcc] = useState(null);
  const [watchGyro, setWatchGyro] = useState(null);
  const [watchHR, setWatchHR] = useState(null);
  const [watchHRV, setWatchHRV] = useState(null);

  // Ref to store the event emitter and subscription
  const eventEmitterRef = useRef(null);
  const subscriptionRef = useRef(null);

  useEffect(() => {
    // Check if SensorsModule is available
    if (!SensorsModule) {
      console.warn('SensorsModule is not available');
      return;
    }

    // Create event emitter
    const eventEmitter = new NativeEventEmitter(SensorsModule);
    eventEmitterRef.current = eventEmitter;

    // Start sensors
    try {
      SensorsModule.startSensors();
    } catch (error) {
      console.error('Error starting sensors:', error);
      return;
    }

    // Subscribe to sensor data events
    const subscription = eventEmitter.addListener('SensorData', (data) => {
      // Parse phone data
      if (data.phone) {
        const phone = data.phone;
        
        // Update phone accelerometer
        if (Array.isArray(phone.acc) && phone.acc.length === 3) {
          setPhoneAcc([phone.acc[0], phone.acc[1], phone.acc[2]]);
        }
        
        // Update phone gyroscope
        if (Array.isArray(phone.gyro) && phone.gyro.length === 3) {
          setPhoneGyro([phone.gyro[0], phone.gyro[1], phone.gyro[2]]);
        }
        
        // Update phone microphone dB
        if (typeof phone.mic_db === 'number') {
          setPhoneMicDB(phone.mic_db);
        }
      }

      // Parse watch data
      if (data.watch) {
        const watch = data.watch;
        
        // Update watch accelerometer
        if (Array.isArray(watch.acc) && watch.acc.length === 3) {
          setWatchAcc([watch.acc[0], watch.acc[1], watch.acc[2]]);
        } else {
          setWatchAcc(null);
        }
        
        // Update watch gyroscope
        if (Array.isArray(watch.gyro) && watch.gyro.length === 3) {
          setWatchGyro([watch.gyro[0], watch.gyro[1], watch.gyro[2]]);
        } else {
          setWatchGyro(null);
        }
        
        // Update watch heart rate
        if (typeof watch.hr === 'number' && watch.hr > 0) {
          setWatchHR(watch.hr);
        } else {
          setWatchHR(null);
        }
        
        // Update watch HRV (may be null)
        if (watch.hrv !== null && watch.hrv !== undefined && typeof watch.hrv === 'number') {
          setWatchHRV(watch.hrv);
        } else {
          setWatchHRV(null);
        }
      } else {
        // No watch data available
        setWatchAcc(null);
        setWatchGyro(null);
        setWatchHR(null);
        setWatchHRV(null);
      }
    });

    subscriptionRef.current = subscription;

    // Cleanup function
    return () => {
      // Remove event listener
      if (subscriptionRef.current) {
        subscriptionRef.current.remove();
        subscriptionRef.current = null;
      }

      // Stop sensors
      try {
        if (SensorsModule && SensorsModule.stopSensors) {
          SensorsModule.stopSensors();
        }
      } catch (error) {
        console.error('Error stopping sensors:', error);
      }

      eventEmitterRef.current = null;
    };
  }, []); // Empty dependency array - only run on mount/unmount

  // Return sensor values
  return {
    phoneAcc,
    phoneGyro,
    phoneMicDB,
    watchAcc,
    watchGyro,
    watchHR,
    watchHRV,
  };
};

