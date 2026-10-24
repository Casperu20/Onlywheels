"""
Push notifications (phase 3, Android + web push) via Firebase Cloud Messaging.

Plan:
- Add `fcm-django`; it provides an `FCMDevice` model (token per browser/phone).
- Frontend registers the token after the user allows notifications
  (`frontend/src/lib/native/push.ts`: Web Push in browsers, @capacitor/push-notifications on Android)
  and POSTs it to `/api/v1/notifications/devices/`.
- `send_push` is called next to the email tasks in `tasks.py` (order paid, shipped,
  ready for fitting, AI photo ready).
"""


def send_push(user, title: str, body: str, data: dict | None = None) -> None:
    raise NotImplementedError("Push notifications are planned for phase 3 (see module docstring).")
