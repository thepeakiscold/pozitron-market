import time
import threading
from datetime import datetime, timedelta
from .db import get_agent_config, update_agent_config

class InstagramScheduler:
    def __init__(self, agent):
        self.agent = agent
        self.agent.scheduler = self
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        with self._lock:
            if self.is_running():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="InstagramPRScheduler", daemon=True)
            self._thread.start()
            print("🚀 Instagram PR Planlayıcı arka plan iş parçacığı başlatıldı.")

    def stop(self):
        with self._lock:
            if not self.is_running():
                return
            self._stop_event.set()
            if self._thread:
                self._thread.join(timeout=3)
            self._thread = None
            print("🛑 Instagram PR Planlayıcı durduruldu.")

    def trigger_now(self) -> dict:
        """Immediately executes an autonomous cycle."""
        return self.agent.run_autonomous_cycle()

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                config = get_agent_config()
                is_enabled = bool(config.get('is_autonomous_enabled', 0))
                
                if is_enabled:
                    next_run_str = config.get('next_run_at')
                    should_run = False
                    
                    if not next_run_str:
                        should_run = True
                    else:
                        try:
                            next_run_dt = datetime.fromisoformat(next_run_str)
                            if datetime.now() >= next_run_dt:
                                should_run = True
                        except Exception:
                            should_run = True

                    if should_run:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏰ Planlanan saat geldi, otonom paylaşım yapılıyor...")
                        self.agent.run_autonomous_cycle()
                
            except Exception as e:
                print(f"⚠️ Instagram Planlayıcı döngü hatası: {str(e)}")

            # Sleep in 5-second intervals to allow prompt stopping
            for _ in range(12):  # checks every 60s total
                if self._stop_event.is_set():
                    break
                time.sleep(5)
