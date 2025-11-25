import { Accelerometer } from "expo-sensors";
import { useEffect, useState } from "react";
import { View } from "react-native";
import { ThemedText } from "./themed-text";

export function AccelerometerDisplay() {
    const [{ x, y, z }, setData] = useState<any>({
        x: 0,
        y: 0,
        z: 0,
    });
    const [subscription, setSubscription] = useState<any>(null);

    const _subscribe = () => {
        const subscription = Accelerometer.addListener(setData);

        setSubscription(subscription);
    };

    const _unsubscribe = () => {
        subscription && subscription.remove();
        setSubscription(null);
    };

    useEffect(() => {
        Accelerometer.setUpdateInterval(100);

        _subscribe();

        return () => {
            _unsubscribe();
        };
    }, []);

    return (
        <View>
            <ThemedText>Accelerometer Data</ThemedText>
            <ThemedText>x: {x.toFixed(3)}</ThemedText>
            <ThemedText>y: {y.toFixed(3)}</ThemedText>
            <ThemedText>z: {z.toFixed(3)}</ThemedText>
        </View>
    );
}