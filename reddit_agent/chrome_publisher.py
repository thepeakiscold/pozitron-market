import os
import json
import subprocess
import tempfile
from .chrome_session import extract_chrome_reddit_session

def publish_via_chrome(post_url: str, reply_text: str) -> dict:
    """
    Publishes a comment to a Reddit post using the stealth Puppeteer Chrome session.
    """
    if not post_url:
        return {"success": False, "error": "Geçerli bir Reddit gönderi bağlantısı (URL) bulunamadı."}

    # Extract current Chrome cookies
    session_res = extract_chrome_reddit_session()
    if not session_res.get("success") or not session_res.get("cookies"):
        return {"success": False, "error": session_res.get("error", "Chrome oturum çerezleri okunamadı.")}

    # Format cookies for Puppeteer
    puppeteer_cookies = []
    for name, val in session_res["cookies"].items():
        if val:
            puppeteer_cookies.append({
                "name": name,
                "value": val,
                "domain": ".reddit.com",
                "path": "/"
            })

    cookie_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False)
    text_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False, encoding="utf-8")

    try:
        json.dump(puppeteer_cookies, cookie_file)
        cookie_file.close()

        text_file.write(reply_text)
        text_file.close()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        poster_script = os.path.join(script_dir, "chrome_poster.js")
        project_root = os.path.dirname(script_dir)

        cmd = [
            "node",
            poster_script,
            "--url", post_url,
            "--text-file", text_file.name,
            "--cookies", cookie_file.name
        ]

        proc = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=90
        )

        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        # Parse JSON from stdout
        try:
            lines = stdout.splitlines()
            result = None
            for line in reversed(lines):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    result = json.loads(line)
                    break

            if result:
                return result
            else:
                return {"success": False, "error": f"Chrome poster beklenmeyen çıktı verdi: {stdout or stderr}"}
        except Exception as e:
            return {"success": False, "error": f"Çıktı çözümlenemedi: {stdout} ({str(e)})"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Chrome gönderim işlemi zaman aşımına uğradı (90s)."}
    except Exception as e:
        return {"success": False, "error": f"Gönderim hatası: {str(e)}"}
    finally:
        if os.path.exists(cookie_file.name):
            try:
                os.remove(cookie_file.name)
            except Exception:
                pass
        if os.path.exists(text_file.name):
            try:
                os.remove(text_file.name)
            except Exception:
                pass
