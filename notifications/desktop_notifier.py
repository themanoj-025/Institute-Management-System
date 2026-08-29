import threading

from plyer import notification

from config.constants import APP_NAME


class DesktopNotifier:
    def __init__(self) -> None:
        # Path to app icon if any
        self.icon_path: str | None = None
        # Could point to an .ico file in assets/icons/ if needed

    def notify(self, title: str, message: str, timeout: int = 5) -> None:
        def task() -> None:
            try:
                notification.notify(
                    title=f"{APP_NAME} - {title}",
                    message=message,
                    app_name=APP_NAME,
                    app_icon=self.icon_path,  # Must be .ico on Windows
                    timeout=timeout,
                )
            except OSError as e:
                print(f"Desktop notification failed: {e}")

        threading.Thread(target=task, daemon=True).start()


desktop_notifier = DesktopNotifier()
