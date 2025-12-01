// lib/notifications.ts
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";

export async function registerForPushNotificationsAsync() {
  // Push notifications only work on real devices
  if (!Device.isDevice) {
    console.log("Push notifications require a physical device.");
    return null;
  }

  // Check current notification permission
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  // Request permission if not granted yet
  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  // If permission is still not granted
  if (finalStatus !== "granted") {
    console.log("Notification permission not granted.");
    return null;
  }

  // Get Expo push token (iOS)
  const tokenData = await Notifications.getExpoPushTokenAsync();
  const expoPushToken = tokenData.data;

  console.log("Expo push token:", expoPushToken);

  return expoPushToken;
}
