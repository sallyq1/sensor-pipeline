import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';
import * as Notifications from "expo-notifications";

import { useColorScheme } from '@/hooks/use-color-scheme';
import { Platform } from "react-native";
import { useEffect } from 'react';
import { registerForPushNotificationsAsync } from "../lib/notifications";

export const unstable_settings = {
  anchor: '(tabs)',
};

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export default function RootLayout() {
  const colorScheme = useColorScheme();

  useEffect(() => {
    const initPush = async () => {
      const token = await registerForPushNotificationsAsync();
      if (!token) return;

      try {
        await fetch("http://192.168.1.226:8000/register-rn-token", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            token: token,
          }),
        });
      } catch (e) {
        console.log("Failed to send token to backend:", e);
      }
    };

    initPush();
  }, []);

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="modal" options={{ presentation: 'modal', title: 'Modal' }} />
      </Stack>
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}
