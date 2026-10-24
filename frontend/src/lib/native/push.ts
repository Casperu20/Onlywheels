/**
 * Push notifications (phase 3). Web: Notification permission + Firebase Web Push token;
 * Android: @capacitor/push-notifications. The token is sent to the backend
 * (see backend/apps/notifications/push.py).
 */
export async function requestPushPermission(): Promise<boolean> {
  if (!("Notification" in window)) return false;
  const result = await Notification.requestPermission();
  return result === "granted";
}
