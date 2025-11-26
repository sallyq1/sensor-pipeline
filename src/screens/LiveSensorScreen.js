import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { useSensors } from '../hooks/useSensors';

const LiveSensorScreen = () => {
  const {
    phoneAcc,
    phoneGyro,
    phoneMicDB,
    watchAcc,
    watchGyro,
    watchHR,
    watchHRV,
  } = useSensors();

  // Store latest packet for JSON display
  const [latestPacket, setLatestPacket] = useState(null);

  // Update latest packet whenever sensor data changes
  useEffect(() => {
    const packet = {
      phone: {
        acc: phoneAcc,
        gyro: phoneGyro,
        mic_db: phoneMicDB,
      },
      watch: watchAcc
        ? {
            acc: watchAcc,
            gyro: watchGyro,
            hr: watchHR,
            hrv: watchHRV,
          }
        : null,
      timestamp: new Date().toISOString(),
    };
    setLatestPacket(packet);
  }, [phoneAcc, phoneGyro, phoneMicDB, watchAcc, watchGyro, watchHR, watchHRV]);

  // Format vector for display
  const formatVector = (vector) => {
    if (!vector || !Array.isArray(vector)) return 'N/A';
    return `[${vector[0].toFixed(3)}, ${vector[1].toFixed(3)}, ${vector[2].toFixed(3)}]`;
  };

  // Format JSON with proper indentation
  const formatJSON = (obj) => {
    try {
      return JSON.stringify(obj, null, 2);
    } catch (error) {
      return 'Error formatting JSON';
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Live Sensor Data</Text>

      {/* Phone IMU Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Phone IMU</Text>
        <View style={styles.dataRow}>
          <Text style={styles.label}>Accelerometer:</Text>
          <Text style={styles.value}>{formatVector(phoneAcc)}</Text>
        </View>
        <View style={styles.dataRow}>
          <Text style={styles.label}>Gyroscope:</Text>
          <Text style={styles.value}>{formatVector(phoneGyro)}</Text>
        </View>
        <View style={styles.dataRow}>
          <Text style={styles.label}>Microphone (dB):</Text>
          <Text style={styles.value}>{phoneMicDB.toFixed(2)} dB</Text>
        </View>
      </View>

      {/* Watch IMU Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Watch IMU</Text>
        <View style={styles.dataRow}>
          <Text style={styles.label}>Accelerometer:</Text>
          <Text style={styles.value}>
            {watchAcc ? formatVector(watchAcc) : 'N/A'}
          </Text>
        </View>
        <View style={styles.dataRow}>
          <Text style={styles.label}>Gyroscope:</Text>
          <Text style={styles.value}>
            {watchGyro ? formatVector(watchGyro) : 'N/A'}
          </Text>
        </View>
      </View>

      {/* Watch Health Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Watch Health</Text>
        <View style={styles.dataRow}>
          <Text style={styles.label}>Heart Rate:</Text>
          <Text style={styles.value}>
            {watchHR ? `${watchHR} bpm` : 'N/A'}
          </Text>
        </View>
        <View style={styles.dataRow}>
          <Text style={styles.label}>HRV (SDNN):</Text>
          <Text style={styles.value}>
            {watchHRV ? `${watchHRV.toFixed(2)} ms` : 'N/A'}
          </Text>
        </View>
      </View>

      {/* JSON Packet Display */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Latest JSON Packet</Text>
        <ScrollView
          style={styles.jsonContainer}
          nestedScrollEnabled={true}
          showsVerticalScrollIndicator={true}>
          <Text style={styles.jsonText}>
            {latestPacket ? formatJSON(latestPacket) : 'No data yet...'}
          </Text>
        </ScrollView>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    color: '#333',
    textAlign: 'center',
  },
  section: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
    color: '#2196F3',
  },
  dataRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
    paddingVertical: 4,
  },
  label: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500',
    flex: 1,
  },
  value: {
    fontSize: 14,
    color: '#333',
    fontFamily: 'monospace',
    flex: 2,
    textAlign: 'right',
  },
  jsonContainer: {
    backgroundColor: '#1e1e1e',
    borderRadius: 8,
    padding: 12,
    maxHeight: 400,
    marginTop: 8,
  },
  jsonText: {
    color: '#d4d4d4',
    fontSize: 12,
    fontFamily: 'monospace',
    lineHeight: 18,
  },
});

export default LiveSensorScreen;

