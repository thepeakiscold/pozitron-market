"""
Unified LLM client for the whole Pozitron pipeline.

All LLM text/vision usage is routed through the OpenCode provider gateway
(Evren, OpenAI-compatible) using DeepSeek V4.1 Flash with the "high"
reasoning effort ("DeepSeek V4.1 Flash High").

Provider configuration resolution order:
  1. Explicit constructor args
  2. Environment variables: LLM_BASE_URL / LLM_API_KEY / LLM_MODEL / LLM_REASONING_EFFORT
     (also OPENCODE_BASE_URL / OPENCODE_API_KEY / EVREN_API_KEY)
  3. ~/.config/opencode/opencode.json -> providers.evren.settings.{baseURL,apiKey}
  4. Hard-coded Evren defaults

If no credential is available, `is_configured()` returns False and callers may
fall back to their legacy provider.
"""
import os
import json
import urllib.request
import urllib.error

DEFAULT_BASE_URL = "https://evren-llmapi.ssyz.org.tr/v1"
DEFAULT_MODEL = "qwen3.8-flash-next"
DEFAULT_EFFORT = "high"
OPENCODE_CONFIG = os.path.expanduser("~/.config/opencode/opencode.json")

MODEL_ALIASES = {
    "flash-3.8": "qwen3.8-flash-next",
    "gemini-3.8-flash": "qwen3.8-flash-next",
    "gemini-3.8": "qwen3.8-flash-next",
    "flash 3.8": "qwen3.8-flash-next",
    "deepseek-v4.1-flash": "qwen3.8-flash-next",
}


def _read_opencode_provider():
    base, key = "", ""
    try:
        if os.path.exists(OPENCODE_CONFIG):
            with open(OPENCODE_CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            prov = (cfg.get("providers") or {}).get("evren", {})
            settings = prov.get("settings") or {}
            base = settings.get("baseURL") or base
            key = settings.get("apiKey") or key
    except Exception:
        pass
    return base, key


def resolve_config():
    oc_base, oc_key = _read_opencode_provider()
    base = (os.environ.get("LLM_BASE_URL")
            or os.environ.get("OPENCODE_BASE_URL")
            or oc_base
            or DEFAULT_BASE_URL)
    key = (os.environ.get("LLM_API_KEY")
           or os.environ.get("OPENCODE_API_KEY")
           or os.environ.get("EVREN_API_KEY")
           or oc_key
           or "")
    raw_model = os.environ.get("LLM_MODEL") or DEFAULT_MODEL
    model = MODEL_ALIASES.get(raw_model.lower(), raw_model)
    effort = os.environ.get("LLM_REASONING_EFFORT") or DEFAULT_EFFORT
    return base.rstrip("/"), key, model, effort


def _extract_json(text):
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        t = t[start:end + 1]
    try:
        return json.loads(t)
    except Exception:
        return None


class LLMClient:
    def __init__(self, base_url=None, api_key=None, model=None,
                 reasoning_effort=None, timeout=120):
        cfg_base, cfg_key, cfg_model, cfg_effort = resolve_config()
        self.base_url = (base_url or cfg_base).rstrip("/")
        self.api_key = api_key or cfg_key
        raw_m = model or cfg_model
        self.model = MODEL_ALIASES.get(raw_m.lower(), raw_m)
        self.reasoning_effort = reasoning_effort or cfg_effort
        self.timeout = timeout
        self.last_error = None

    def is_configured(self) -> bool:
        # Disable real network LLM calls during automated tests unless explicitly enabled,
        # so the test suite stays hermetic and fast.
        if os.environ.get("POZITRON_DISABLE_LLM", "").lower() in ("1", "true", "yes"):
            return False
        if (os.environ.get("PYTEST_CURRENT_TEST")
                and os.environ.get("POZITRON_ENABLE_LLM_IN_TESTS", "").lower() not in ("1", "true", "yes")):
            return False
        return bool(self.api_key)

    def chat(self, messages, max_tokens=8192, temperature=0.7,
             json_mode=False, reasoning_effort=None, timeout=None):
        """Low-level OpenAI-compatible chat completion with Flash 3.8 primary and auto-fallback."""
        if not self.is_configured():
            self.last_error = "LLM not configured (missing api key)"
            return ""

        models_to_try = [self.model]
        if self.model != "qwen3.8-flash-next":
            models_to_try.append("qwen3.8-flash-next")

        last_err = ""
        for cur_model in models_to_try:
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": cur_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            effort = reasoning_effort or self.reasoning_effort
            if effort:
                payload["reasoning_effort"] = effort
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {self.api_key}"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                msg = (body.get("choices") or [{}])[0].get("message") or {}
                content = msg.get("content")
                if content is None:
                    content = ""
                self.last_error = None
                return content
            except urllib.error.HTTPError as he:
                try:
                    err = he.read().decode("utf-8", errors="ignore")
                except Exception:
                    err = ""
                last_err = f"HTTP {he.code}: {err[:200]}"
                # If 503 capacity error or 404, try next model in list
                if he.code in (503, 404, 429) and cur_model != models_to_try[-1]:
                    continue
                self.last_error = last_err
                return ""
            except Exception as e:
                self.last_error = str(e)
                return ""
        self.last_error = last_err
        return ""

    def generate_text(self, prompt, system=None, max_tokens=8192,
                      temperature=0.7, reasoning_effort=None):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, max_tokens=max_tokens, temperature=temperature,
                         reasoning_effort=reasoning_effort)

    def generate_json(self, prompt, system=None, max_tokens=8192,
                      temperature=0.4, reasoning_effort=None):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        text = self.chat(messages, max_tokens=max_tokens, temperature=temperature,
                         json_mode=True, reasoning_effort=reasoning_effort)
        return _extract_json(text)

    def generate_vision_json(self, prompt, image_path=None, image_bytes=None,
                             mime="image/jpeg", max_tokens=4096, temperature=0.2):
        """Vision request (DeepSeek V4.1 Flash supports vision). Returns parsed JSON."""
        import base64
        b64 = None
        if image_bytes is not None:
            b64 = base64.b64encode(image_bytes).decode("utf-8")
        elif image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
        if not b64:
            return None
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }]
        text = self.chat(messages, max_tokens=max_tokens, temperature=temperature,
                         json_mode=False)
        return _extract_json(text)


_singleton = None


def get_llm() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton
