import threading
import time
from datetime import datetime, timedelta

class RedditScheduler:
    def __init__(self, agent):
        self.agent = agent
        self.stop_event = threading.Event()
        self.thread = None
        self._is_running = False

    def is_running(self) -> bool:
        return self._is_running and self.thread is not None and self.thread.is_alive()

    def start(self):
        if self.is_running():
            return
        self.stop_event.clear()
        self._is_running = True
        self.thread = threading.Thread(target=self._loop, name="RedditDroneSchedulerThread", daemon=True)
        self.thread.start()

    def stop(self):
        self._is_running = False
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self.thread = None

    def _loop(self):
        # Initial short delay on startup
        if self.stop_event.wait(timeout=3.0):
            return

        while not self.stop_event.is_set():
            try:
                # Reload config
                cfg = self.agent.get_safe_config()
                if not cfg.get("is_autonomous_enabled"):
                    if self.stop_event.wait(timeout=10.0):
                        break
                    continue

                # Run a scan cycle
                interval_minutes = int(cfg.get("scan_interval_minutes", 30))
                now = datetime.now()
                next_run = now + timedelta(minutes=interval_minutes)

                self.agent.update_config({
                    "last_scan_at": now.isoformat(),
                    "next_scan_at": next_run.isoformat()
                })

                self.agent.scan_and_process(autonomous=True)

                # Wait for next interval or stop event
                self.stop_event.wait(timeout=interval_minutes * 60)
            except Exception as e:
                # Sleep on error before retrying
                self.stop_event.wait(timeout=60)
