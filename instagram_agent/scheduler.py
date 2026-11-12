import time
import threading
from datetime import datetime, timedelta
from .db import get_agent_config, update_agent_config

def is_in_rest_window(dt: datetime = None) -> bool:
    """
    Returns True if datetime falls within the night rest window (23:30 - 08:30 local TRT).
    During this window, real humans sleep, so automated bot posting and engagement are paused
    to protect the account from heuristic spam flags.
    """
    if dt is None:
        dt = datetime.now()
    hour_val = dt.hour + (dt.minute / 60.0)
    return hour_val >= 23.5 or hour_val < 8.5


def calculate_next_peak_window(from_dt: datetime = None) -> datetime:
    """
    Calculates the next optimal posting timestamp targeting Turkish FPV drone community peak engagement:
    - Weekdays (Mon-Fri): Evening 19:30 - 22:00 TRT (UTC+3)
    - Weekends (Sat-Sun): Midday 11:00 - 14:00 TRT (UTC+3) & Evening 19:30 - 22:00 TRT
    """
    if from_dt is None:
        from_dt = datetime.now()

    min_future = from_dt + timedelta(minutes=15)
    candidates = []

    for day_offset in range(8):
        check_date = (from_dt + timedelta(days=day_offset)).date()
        is_weekend = check_date.weekday() in (5, 6)

        # Evening window: 20:00 (19:30 - 22:00)
        evening_target = datetime(check_date.year, check_date.month, check_date.day, 20, 0, 0)
        if evening_target > min_future:
            candidates.append(evening_target)

        # Weekend midday window: 12:30 (11:00 - 14:00)
        if is_weekend:
            midday_target = datetime(check_date.year, check_date.month, check_date.day, 12, 30, 0)
            if midday_target > min_future:
                candidates.append(midday_target)

    candidates.sort()
    return candidates[0] if candidates else (from_dt + timedelta(hours=6))

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
            print("[BASLATILDI] Instagram PR Planlayici arka plan is parcacigi baslatildi.")

    def stop(self):
        with self._lock:
            if not self.is_running():
                return
            self._stop_event.set()
            if self._thread:
                self._thread.join(timeout=3)
            self._thread = None
            print("[DURDURULDU] Instagram PR Planlayici durduruldu.")

    def trigger_now(self) -> dict:
        """Immediately executes an autonomous cycle."""
        return self.agent.run_autonomous_cycle()

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                config = get_agent_config()
                is_enabled = bool(config.get('is_autonomous_enabled', 0))
                
                if is_enabled:
                    # Respect night rest window (23:30 - 08:30)
                    if is_in_rest_window():
                        next_run_str = config.get('next_run_at')
                        if next_run_str:
                            try:
                                next_run_dt = datetime.fromisoformat(next_run_str)
                                if datetime.now() >= next_run_dt:
                                    now = datetime.now()
                                    target_date = (now + timedelta(days=1)).date() if now.hour >= 23 else now.date()
                                    morning_target = datetime(target_date.year, target_date.month, target_date.day, 9, 30, 0)
                                    update_agent_config({'next_run_at': morning_target.isoformat()})
                                    print(f"[{now.strftime('%H:%M:%S')}] [DİNLENME MODU] Gece dinlenme penceresi (23:30 - 08:30) aktif. Planlanan otonom aksiyon 09:30 sabahina ertelendi.")
                            except Exception:
                                pass
                        for _ in range(12):
                            if self._stop_event.is_set():
                                break
                            time.sleep(5)
                        continue

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
                        # Cross-instance coordination: check if a live post was already published recently on Meta API
                        if not config.get('dry_run_mode', 0) and hasattr(self.agent, 'sync_live_media_to_db'):
                            try:
                                sync_info = self.agent.sync_live_media_to_db(limit=10)
                                latest_live = sync_info.get('latest_published_at')
                                if latest_live:
                                    latest_dt = datetime.fromisoformat(latest_live)
                                    freq_h = float(config.get('posting_frequency_hours', 8) or 8)
                                    elapsed_h = (datetime.now() - latest_dt).total_seconds() / 3600.0
                                    if 0 <= elapsed_h < max(2.0, freq_h * 0.75):
                                        deferred_next = self.agent.calculate_next_run(from_dt=latest_dt)
                                        update_agent_config({
                                            'last_run_at': latest_live,
                                            'last_post_at': latest_live,
                                            'next_run_at': deferred_next,
                                            'next_post_at': deferred_next
                                        })
                                        print(f"[{datetime.now().strftime('%H:%M:%S')}] [SENKRON KORUMA] Instagram hesabinda {elapsed_h:.1f} saat once canli paylasim tespit edildi. Cift paylasimi onlemek icin sonraki plan: {deferred_next}")
                                        should_run = False
                            except Exception:
                                pass

                    if should_run:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] [OTONOM TETİKLEME] Planlanan saat geldi, otonom paylasim yapiliyor...")
                        self.agent.run_autonomous_cycle()
                
            except Exception as e:
                print(f"[UYARI] Instagram Planlayici dongu hatasi: {str(e)}")

            # Sleep in 5-second intervals to allow prompt stopping
            for _ in range(12):  # checks every 60s total
                if self._stop_event.is_set():
                    break
                time.sleep(5)
