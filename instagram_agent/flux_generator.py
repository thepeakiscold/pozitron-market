"""
Local FLUX.1 [dev] image generation bridge (ComfyUI) for the Instagram pipeline.

Connects to a running ComfyUI server (default http://127.0.0.1:8188) in the
FLUX folder under the user's home and generates photorealistic backgrounds for
Instagram posts, giving the feed genuinely varied, AI-made visuals.

The ComfyUI API workflow (flux_dev_gguf_api.json) is reused as-is; we only inject
prompt text, seed and resolution.
"""
import os
import io
import json
import time
import uuid
import subprocess
import urllib.parse
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_FLUX_DIR = os.environ.get("FLUX_DIR", "/home/eyup/Desktop/FLUX")
DEFAULT_SERVER = os.environ.get("COMFYUI_SERVER", "http://127.0.0.1:8188")

_last_start_attempt = 0.0


# Content pillar -> English photographic subject for FLUX.
FLUX_SUBJECTS = {
    "product_spotlight": "a premium FPV drone component on a dark reflective studio surface",
    "drone_build_showcase": "a disassembled 5-inch FPV drone build spread on a carbon-fiber workbench",
    "community_quiz": "an FPV pilot holding a radio controller at a mountain launch point at sunset",
    "hardware_battle": "two FPV drone components side by side on a tech comparison table",
    "mistake_breakdown": "a crashed FPV drone with a burnt ESC on a repair mat, dramatic close-up",
    "pilot_tip": "an FPV pilot's hands soldering a flight controller under bright workshop light",
    "myth_buster": "a laboratory bench with FPV electronics and oscilloscope probes, cool lighting",
    "maintenance_checklist": "an organized FPV maintenance kit with tools and spare parts on a bench",
    "beginner_roadmap": "a beginner setting up their first FPV drone on a bright desk",
    "spot_guide": "a breathtaking drone aerial view of a Turkish mountain valley at golden hour",
    "flight_weather_radar": "a moody sky with clouds over a flying field, cinematic weather",
    "deal_drop": "a glowing FPV product hero shot with dramatic rim light and dark background",
    "tool_showcase": "a sleek laptop showing an engineering design tool beside FPV parts",
    "review_highlight": "a satisfied FPV pilot with goggles and a drone in hand, outdoor portrait",
    "carousel_guide": "an FPV engineering concept flat-lay with carbon fiber and circuitry",
}

# Visual style presets (kept consistent with the reel style presets).
FLUX_STYLES = [
    "dark high-tech studio, neon cyan and amber rim lighting, macro detail, shallow depth of field",
    "golden-hour outdoor field, warm sunlight, dynamic low angle, cinematic bokeh",
    "clean white product stage, soft studio softbox light, elegant reflections",
    "moody industrial workshop, warm tungsten light, gritty realistic texture",
    "misty mountain landscape at dawn, volumetric light, aerial perspective",
    "night rooftop with city bokeh, cool teal highlights, cinematic",
]

NEGATIVE_PROMPT = "text, watermark, logo, letters, signature, low quality, blurry, distorted, extra limbs"


class FluxGenerator:
    def __init__(self, server: str = None, workflow_path: str = None,
                 flux_dir: str = None, timeout: int = 300):
        self.flux_dir = flux_dir or DEFAULT_FLUX_DIR
        self.server = (server or DEFAULT_SERVER).rstrip("/")
        self.workflow_path = workflow_path or os.environ.get(
            "COMFY_WORKFLOW", os.path.join(self.flux_dir, "flux_dev_gguf_api.json")
        )
        self.timeout = timeout
        self.output_dir = os.path.join(BASE_DIR, "assets", "instagram", "posts")
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        # Never hit the local GPU during automated tests.
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return False
        if os.environ.get("POZITRON_DISABLE_FLUX", "").lower() in ("1", "true", "yes"):
            return False
        try:
            with urllib.request.urlopen(self.server + "/system_stats", timeout=4) as r:
                return r.status == 200
        except Exception:
            return False

    def ensure_server(self, wait_seconds: int = 180) -> bool:
        """
        Returns True if ComfyUI is available. If not, and FLUX_AUTOSTART is enabled
        (default on), launches run_comfyui.sh once and waits for it to come up.
        Never raises.
        """
        if self.is_available():
            return True
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return False
        if os.environ.get("FLUX_AUTOSTART", "1").lower() not in ("1", "true", "yes"):
            return False
        global _last_start_attempt
        now = time.time()
        if now - _last_start_attempt < 600:  # avoid restart storms (10 min cooldown)
            return False
        _last_start_attempt = now
        script = os.path.join(self.flux_dir, "run_comfyui.sh")
        if not os.path.exists(script):
            return False
        try:
            log = open("/tmp/opencode/comfyui_autostart.log", "a")
            subprocess.Popen([script], stdout=log, stderr=log, start_new_session=True)
            print("[FLUX] ComfyUI baslatiliyor (run_comfyui.sh)...")
        except Exception as e:
            print(f"[FLUX] ComfyUI baslatilamadi: {e}")
            return False
        for _ in range(max(1, wait_seconds // 3)):
            if self.is_available():
                print("[FLUX] ComfyUI hazir.")
                return True
            time.sleep(3)
        return False

    # ------------------------------------------------------------------
    def build_flux_prompt(self, post_data: dict) -> str:
        content_type = (post_data or {}).get("content_type", "product_spotlight")
        visual = (post_data or {}).get("visual_summary") or {}
        prod = (post_data or {}).get("product_data") or {}
        prod_name = prod.get("name_tr") or prod.get("name")
        subject = FLUX_SUBJECTS.get(content_type, FLUX_SUBJECTS["product_spotlight"])
        if prod_name and content_type in ("product_spotlight", "deal_drop", "review_highlight", "hardware_battle"):
            subject = f"{subject} featuring {prod_name}"

        style = (post_data or {}).get("visual_style") or None
        if not style:
            import random
            style = random.choice(FLUX_STYLES)

        headline = visual.get("headline") or ""
        topic = f" Topic: {headline}." if headline else ""
        return (
            f"Photorealistic commercial photograph, {subject}.{topic} {style}. "
            f"FPV drone technology brand aesthetic, ultra detailed, 8k, professional product photography, no text"
        )

    # ------------------------------------------------------------------
    def _api(self, path, payload=None, timeout=60):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            self.server + path, data=data,
            headers={"Content-Type": "application/json"} if data else {},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return json.loads(body) if body else {}

    def generate(self, prompt: str, width: int = 1024, height: int = 1024,
                 steps: int = 20, seed: int = None, timeout: int = None,
                 save_path: str = None) -> str:
        """
        Runs one FLUX generation and returns the absolute path to the saved image
        (empty string on failure).
        """
        timeout = timeout or self.timeout
        try:
            with open(self.workflow_path, "r", encoding="utf-8") as f:
                wf = json.load(f)
        except Exception as e:
            print(f"[FLUX] Workflow okunamadi ({self.workflow_path}): {e}")
            return ""

        seed = int(seed if seed is not None else (time.time_ns() % 2_147_483_647))
        try:
            wf["4"]["inputs"]["text"] = prompt
            wf["8"]["inputs"]["seed"] = seed
            wf["8"]["inputs"]["steps"] = int(steps)
            if "7" in wf and "EmptyLatentImage" in str(wf.get("7", {}).get("class_type", "")):
                wf["7"]["inputs"]["width"] = int(width)
                wf["7"]["inputs"]["height"] = int(height)
            if "6" in wf:  # negative prompt
                wf["6"]["inputs"]["text"] = NEGATIVE_PROMPT
        except Exception as e:
            print(f"[FLUX] Workflow parametreleri uygulanamadi: {e}")
            return ""

        client_id = "pozitron-" + uuid.uuid4().hex[:8]
        try:
            resp = self._api("/prompt", {"prompt": wf, "client_id": client_id}, timeout=30)
            pid = resp.get("prompt_id")
            if not pid:
                print(f"[FLUX] prompt_id alinamadi: {str(resp)[:200]}")
                return ""
        except Exception as e:
            print(f"[FLUX] Kuyruga eklenemedi: {e}")
            return ""

        # Poll history
        deadline = time.time() + timeout
        image_info = None
        while time.time() < deadline:
            try:
                hist = self._api(f"/history/{pid}", timeout=20)
            except Exception:
                time.sleep(2)
                continue
            if pid in hist:
                entry = hist[pid]
                status = entry.get("status", {}) or {}
                if status.get("status_str") == "error":
                    print(f"[FLUX] Uretim hatasi: {json.dumps(status)[:300]}")
                    return ""
                outputs = entry.get("outputs", {}) or {}
                # Find the first image in any SaveImage node
                for node_out in outputs.values():
                    imgs = (node_out or {}).get("images") or []
                    if imgs:
                        image_info = imgs[0]
                        break
                if image_info is not None:
                    break
            time.sleep(2)

        if not image_info:
            print("[FLUX] Zaman asimi / gorsel cikti bulunamadi.")
            return ""

        # Download image via /view
        try:
            q = urllib.parse.urlencode({
                "filename": image_info.get("filename", ""),
                "subfolder": image_info.get("subfolder", ""),
                "type": image_info.get("type", "output"),
            })
            with urllib.request.urlopen(self.server + "/view?" + q, timeout=60) as r:
                raw = r.read()
            if len(raw) < 3000:
                print("[FLUX] Gorsel verisi cok kucuk, iptal edildi.")
                return ""
        except Exception as e:
            print(f"[FLUX] Gorsel indirilemedi: {e}")
            return ""

        if not save_path:
            save_path = os.path.join(self.output_dir, f"flux_{uuid.uuid4().hex[:10]}.png")
        try:
            with open(save_path, "wb") as f:
                f.write(raw)
        except Exception as e:
            print(f"[FLUX] Gorsel kaydedilemedi: {e}")
            return ""

        print(f"[FLUX] Gorsel uretildi: {os.path.basename(save_path)} ({len(raw)//1024} KB, seed={seed})")
        return save_path

    # ------------------------------------------------------------------
    def generate_for_post(self, post_data: dict, post_id: str,
                          width: int = 1024, height: int = 1024,
                          steps: int = 20) -> dict:
        """Convenience: build a prompt, generate, save under the repo and return info."""
        prompt = self.build_flux_prompt(post_data)
        save_path = os.path.join(self.output_dir, f"{post_id}_flux_raw.png")
        path = self.generate(prompt, width=width, height=height, steps=steps, save_path=save_path)
        return {"path": path, "prompt": prompt}
