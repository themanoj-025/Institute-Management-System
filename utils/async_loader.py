import threading
from typing import Any, Callable, Optional


class AsyncLoader:
    """Runs a task in a daemon thread and updates UI on completion."""

    @staticmethod
    def run(
        root: Any,
        task_func: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        def worker() -> None:
            try:
                result = task_func()
                root.after(0, lambda: on_success(result))
            except Exception as e:
                import traceback

                traceback.print_exc()
                if on_error:
                    root.after(0, lambda err=e: on_error(err))
                else:
                    print(f"AsyncLoader Error: {e}")

        t = threading.Thread(target=worker, daemon=True)
        t.start()
