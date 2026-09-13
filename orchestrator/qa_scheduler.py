import time
import threading
from datetime import datetime
from typing import Optional
from .subagent_qa import QASentinelAgent

class QAScheduler:
    """
    AUTONOMOUS BACKGROUND QA WATCHDOG SCHEDULER
    - Her 30 dakikada bir (veya qa_agent_config'deki aralikla) tum boru hattini otonom denetler.
    - Hata algilandiginda beklemeden auto_heal() calistirarak arizalari cozer.
    - SIFIR EMOJI KURALI: Loglarda emoji bulunmaz.
    """
    def __init__(self, qa_agent: QASentinelAgent):
        self.qa_agent = qa_agent
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self._is_running = False

    def is_running(self) -> bool:
        return self._is_running and self.thread is not None and self.thread.is_alive()

    def start(self):
        if self.is_running():
            return
        self.stop_event.clear()
        self._is_running = True
        self.thread = threading.Thread(target=self._loop, name="QASchedulerThread", daemon=True)
        self.thread.start()

    def stop(self):
        self._is_running = False
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self.thread = None

    def _loop(self):
        # Initial diagnostic audit on startup after short delay
        time.sleep(3)
        try:
            print("[Subagent 7 - QA Sentinel] Baslangic sistem tani ve saglik denetimi yurutuluyor...")
            self.qa_agent.run_full_diagnostics(auto_heal=True)
        except Exception as e:
            print(f"[Subagent 7 - QA Sentinel] Baslangic denetim hatasi: {e}")

        last_run_time = time.time()

        while not self.stop_event.is_set():
            try:
                status = self.qa_agent.get_status()
                if not status.get("is_autonomous_enabled"):
                    self.stop_event.wait(timeout=30)
                    continue

                interval_minutes = int(status.get("check_interval_minutes", 30))
                interval_seconds = interval_minutes * 60
                now = time.time()

                if now - last_run_time >= interval_seconds:
                    print(f"[Subagent 7 - QA Sentinel] Periyodik otonom saglik ve hata denetimi ({interval_minutes} dk) baslatildi...")
                    self.qa_agent.run_full_diagnostics(auto_heal=bool(status.get("auto_heal_enabled", 1)))
                    last_run_time = now

                # Sleep in short increments for responsive shutdown
                self.stop_event.wait(timeout=60)
            except Exception as e:
                print(f"[Subagent 7 - QA Sentinel] Scheduler dongu hatasi: {e}")
                self.stop_event.wait(timeout=60)
