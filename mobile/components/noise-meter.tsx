import { useEffect, useRef, useState } from "react";
import { View } from "react-native";
import { Audio, InterruptionModeIOS } from "expo-av";
import { ThemedText } from "./themed-text";

const NOISE_THRESHOLD_DB = -30;
const POLL_INTERVAL_MS = 200;

export function NoiseMeter() {
    const [permission, requestPermission] = Audio.usePermissions();
    const [metering, setMetering] = useState<number | null>(null);
    const [isNoisy, setIsNoisy] = useState(false);

    const recordingRef = useRef<Audio.Recording | null>(null);
    const intervalRef = useRef<number | null>(null);

    useEffect(() => {
        let cancelled = false;

        const start = async () => {
            if (!permission || permission.status !== "granted") {
                const res = await requestPermission();
                if (!res || res.status !== "granted") {
                    console.warn("Microphone permission not granted");
                    return;
                }
            }

            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
                staysActiveInBackground: false,
                interruptionModeIOS: InterruptionModeIOS.DuckOthers,
            });

            const recording = new Audio.Recording();

            await recording.prepareToRecordAsync({
                ...Audio.RecordingOptionsPresets.LOW_QUALITY,
                isMeteringEnabled: true,
            } as any);

            await recording.startAsync();
            recordingRef.current = recording;

            intervalRef.current = setInterval(async () => {
                if (!recordingRef.current || cancelled) return;

                const status = await recordingRef.current.getStatusAsync();

                if (!status.isRecording) return;

                const m = (status as any).metering as number | undefined;

                if (typeof m === "number") {
                    setMetering(m);
                    setIsNoisy(m > NOISE_THRESHOLD_DB);
                }
            }, POLL_INTERVAL_MS);
        };

        start()
            .catch((e) => {
                console.error("Failed to start noise meter:", e);
            });

        return () => {
            cancelled = true;

            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }

            if (recordingRef.current) {
                recordingRef.current
                .stopAndUnloadAsync()
                .catch(() => {})
                .finally(() => {
                    recordingRef.current = null;
                });
            }
        };
    }, []);

  return (
    <View>
        <ThemedText>Noise meter</ThemedText>
        <ThemedText>
            Level: {metering !== null ? metering.toFixed(1) : "N/A"} dB (relative)
        </ThemedText>
        <ThemedText>
            {isNoisy ? "Noisy" : "Quiet"}
        </ThemedText>
    </View>
  );
}