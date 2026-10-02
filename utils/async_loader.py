import threading
from collections.abc import Callable
from typing import Any


class AsyncLoader:
    """Runs a task in a daemon thread and updates UI on completion."""

    @staticmethod
    def run(
        root: Any,
        task_func: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        def worker() -> None:
            try:
                result = task_func()
                root.after(0, lambda: on_success(result))
            except Exception as e:
                # a failing fetch must reach on_error instead of hanging the
                # UI spinner forever (audit item 8.5). Original traceback is
                # preserved below; tkinter callbacks must never see it.
                import traceback

                traceback.print_exc()
                if on_error:
                    root.after(0, lambda err=e: on_error(err))
                else:
                    print(f"AsyncLoader Error: {e}")

        t = threading.Thread(target=worker, daemon=True)
        t.start()
