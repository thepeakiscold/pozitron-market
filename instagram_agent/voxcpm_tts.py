"""
VoxCPM2 Text-to-Speech & Voiceover Engine for Pozitron Instagram Pipeline.

Generates realistic, studio-quality Turkish female voice narration for Instagram Reels
and video posts using OpenBMB's VoxCPM2 model on GPU.
"""

import os
import sys
import re
import json
import logging
import subprocess
import tempfile
import urllib.request
from pathlib import Path

logger = logging.getLogger("voxcpm_tts")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICEOVERS_DIR = os.path.join(BASE_DIR, "assets", "instagram", "voiceovers")
os.makedirs(VOICEOVERS_DIR, exist_ok=True)

# Path to Python 3.12 environment containing torch + cuda + voxcpm
VENV_PYTHON = "/home/eyup/Desktop/FLUX/ComfyUI/venv/bin/python"

# Default realistic Turkish female voice design prompt
DEFAULT_FEMALE_PROMPT = (
    "A natural, warm, clear, professional Turkish young female voice, "
    "energetic, friendly, fluent Turkish pronunciation with studio clarity."
)

# Technical FPV, Rehber engineering, and e-commerce phonetic expansions for fluent Turkish speech
PHONETIC_REPLACEMENTS = [
    (r"\bFPV\b", "fe pe ve"),
    (r"\bVTX\b", "ve te iks"),
    (r"\bVRX\b", "ve re iks"),
    (r"\bESC\b", "e se ce"),
    (r"\bFC\b", "fe ce"),
    (r"\bAIO\b", "a iyi o"),
    (r"\bELRS\b", "e le re se"),
    (r"\bExpressLRS\b", "Ekspres e le re se"),
    (r"\bGPS\b", "ce pe se"),
    (r"\bUART\b", "yu art"),
    (r"\bDMA\b", "de me a"),
    (r"\bCRSF\b", "ce re se fe"),
    (r"\bPWM\b", "pe ve me"),
    (r"\bPID\b", "pi ay di"),
    (r"\bBEC\b", "bek"),
    (r"\bOSD\b", "o se de"),
    (r"\bRTH\b", "eve dönüş"),
    (r"\bLQ\b", "bağlantı kalitesi"),
    (r"\bRSSI\b", "sinyal gücü"),
    (r"\bESR\b", "e se re"),
    (r"\bRPM\b", "ar pi em"),
    (r"\bTPU\b", "te pe u"),
    (r"\bPETG\b", "pet ge"),
    (r"\bPLA\b", "pe le a"),
    (r"\bSTL\b", "se te le"),
    (r"\bSTEP\b", "step"),
    (r"\bRHCP\b", "sağ polarize"),
    (r"\bLHCP\b", "sol polarize"),
    (r"\bMMCX\b", "em em ce iks"),
    (r"\bU\.FL\b", "u fe le"),
    (r"\bSMA\b", "se me a"),
    (r"\bXT60\b", "iks te altmış"),
    (r"\bXT30\b", "iks te otuz"),
    (r"\bSTM32F405\b", "es ti em otuz iki ef dört yüz beş"),
    (r"\bSTM32F722\b", "es ti em otuz iki ef yedi yüz yirmi iki"),
    (r"\bSTM32H743\b", "es ti em otuz iki eyç yedi yüz kırk üç"),
    (r"\bSTM32H7\b", "es ti em otuz iki eyç yedi"),
    (r"\bF405\b", "ef dört yüz beş"),
    (r"\bF722\b", "ef yedi yüz yirmi iki"),
    (r"\bH743\b", "eyç yedi yüz kırk üç"),
    (r"\b95A\b", "doksan beş A"),
    (r"\b55A\b", "elli beş amper"),
    (r"\b60A\b", "altmış amper"),
    (r"\b45A\b", "kırk beş amper"),
    (r"\bDShot600\b", "di şat altı yüz"),
    (r"\bDSHOT600\b", "di şat altı yüz"),
    (r"\bDShot300\b", "di şat üç yüz"),
    (r"\bDSHOT300\b", "di şat üç yüz"),
    (r"\bDShot\b", "di şat"),
    (r"\bBLHeli_32\b", "bi el heli otuz iki"),
    (r"\bBLHeli\b", "bi el heli"),
    (r"\bBluejay\b", "Blu cey"),
    (r"\bEdgeTX\b", "Ec ti iks"),
    (r"\bCrossfire\b", "Kros fayır"),
    (r"\bSmoke Stopper\b", "duman önleyici"),
    (r"\bLoRa\b", "lora"),
    (r"\bLiPo\b", "lipo"),
    (r"\bLIPO\b", "lipo"),
    (r"\bLi-ion\b", "lityum iyon"),
    (r"\bLi-Ion\b", "lityum iyon"),
    (r"\bLI-ION\b", "lityum iyon"),
    (r"\bBetaflight\b", "Betaflayt"),
    (r"\bBetaFlight\b", "Betaflayt"),
    (r"\bHDZero\b", "Eyc Di Zero"),
    (r"\bWalksnail\b", "Vok sneyl"),
    (r"\bDJI\b", "Di Cey Ay"),
    (r"\bO3\b", "O üç"),
    (r"\bGoPro\b", "Go Pro"),
    (r"\bUSB-C\b", "yusbi si"),
    (r"\bType-C\b", "tayp si"),
    (r"\b3D\b", "üç de"),
    (r"\b63/37\b", "altmış üçe otuz yedi"),
    (r"\bpozitronmarket\.com/rehber\b", "pozitron market nokta com bölü rehber"),
    (r"\bpozitronmarket\.com\b", "pozitron market nokta com"),
    (r"\bpozitronmarket\b", "pozitron market"),
    (r"@pozitronmarket\b", "Pozitron Market"),
    (r"%(\d+)", r"yüzde \1"),
    (r"(\d+)\s*°C\b", r"\1 derece"),
    (r"(\d+(?:[.,]\d+)?)\s*GHz\b", r"\1 gigahertz"),
    (r"(\d+(?:[.,]\d+)?)\s*MHz\b", r"\1 megahertz"),
    (r"(\d+(?:[.,]\d+)?)\s*kHz\b", r"\1 kilohertz"),
    (r"(\d+(?:[.,]\d+)?)\s*dBi\b", r"\1 desibel"),
    (r"(\d+(?:[.,]\d+)?)\s*dB\b", r"\1 desibel"),
    (r"(\d+(?:[.,]\d+)?)\s*mW\b", r"\1 milivat"),
    (r"(\d+(?:[.,]\d+)?)\s*uF\b", r"\1 mikrofarad"),
    (r"(\d+(?:[.,]\d+)?)\s*V\b", r"\1 volt"),
    (r"(\d+)\s*C\b", r"\1 ce"),
    (r"(\d+)\s*TL\b", r"\1 Türk Lirası"),
    (r"(\d+)\s*tl\b", r"\1 Türk Lirası"),
    (r"(\d+)\s*\"\b", r"\1 inç"),
    (r"(\d+)\s*''\b", r"\1 inç"),
    (r"(\d+)\s*kv\b", r"\1 ke ve"),
    (r"(\d+)\s*KV\b", r"\1 ke ve"),
    (r"(\d+)\s*mah\b", r"\1 miliamper saat"),
    (r"(\d+)\s*mAh\b", r"\1 miliamper saat"),
    (r"(\d+)\s*MAH\b", r"\1 miliamper saat"),
    (r"(\d+)\s*S\b", r"\1 S"),
]


def build_subtitle_chunks(display_text: str, duration: float, words_per_chunk: int = 3) -> list:
    """
    Splits spoken text into high-retention 2-to-4 word dynamic subtitle chunks
    with exact start/end timestamps across `duration` (weighted by character length
    and punctuation cadence). Used to burn Hormozi/TikTok-style synchronized captions
    into every Pozitron Reel.
    """
    if not display_text or duration <= 0:
        return []

    # Clean bracket tags, URLs, hashtags while keeping readable technical display tokens
    clean_disp = re.sub(r"https?://\S+", "", display_text)
    clean_disp = re.sub(r"#\w+", "", clean_disp)
    clean_disp = re.sub(r"\[[^\]]*\]", "", clean_disp)
    clean_disp = re.sub(r"[*_`~]", "", clean_disp)
    clean_disp = re.sub(r"\s+", " ", clean_disp).strip()
    if not clean_disp:
        return []

    words = clean_disp.split()
    if not words:
        return []

    raw_chunks = []
    current = []
    for w in words:
        current.append(w)
        ends_sentence = w.endswith((".", "!", "?", ":", ";", ","))
        if len(current) >= words_per_chunk or (ends_sentence and len(current) >= 2):
            raw_chunks.append(current)
            current = []
    if current:
        if raw_chunks and len(current) == 1 and len(raw_chunks[-1]) < 4:
            raw_chunks[-1].extend(current)
        else:
            raw_chunks.append(current)

    # Compute weights proportional to spoken length + pause bonus for punctuation
    weights = []
    for ch in raw_chunks:
        joined = " ".join(ch)
        char_weight = max(4, sum(len(w) for w in ch))
        if joined.endswith((".", "!", "?")):
            char_weight += 4
        elif joined.endswith((",", ":", ";")):
            char_weight += 2
        weights.append(float(char_weight))

    total_w = sum(weights) or 1.0
    usable_dur = max(1.0, float(duration) - 0.15)
    cursor_t = 0.08
    timed_chunks = []
    for ch, w in zip(raw_chunks, weights):
        seg_dur = usable_dur * (w / total_w)
        start_t = round(cursor_t, 2)
        end_t = round(min(duration, cursor_t + seg_dur), 2)
        cursor_t += seg_dur
        # Pick the longest / most impactful word in the chunk to highlight in neon cyan/amber
        best_word = max(ch, key=lambda tok: len(re.sub(r"\W+", "", tok)))
        timed_chunks.append({
            "text": " ".join(ch),
            "words": ch,
            "highlight": best_word.strip(".,!?:;"),
            "start": start_t,
            "end": end_t,
        })
    return timed_chunks


def clean_text_for_speech(text: str) -> str:
    """
    Cleans raw caption/markdown text into fluent, human spoken Turkish:
    - Strips bracketed tags like [REELS], [STOK], [KUPON]
    - Strips URLs, hashtags, and social media handles
    - Strips emojis and asterisks
    - Expands domain acronyms into natural Turkish pronunciations
    - Normalizes punctuation and spacing for natural TTS phrasing
    """
    if not text:
        return ""

    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)

    # Remove hashtags and mentions
    text = re.sub(r"#\w+", "", text)

    # Remove bracketed and parenthesized metadata markers (e.g. [REELS], [KUPON])
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"【[^】]*】", "", text)

    # Remove markdown formatting (*, _, `, ~, #)
    text = re.sub(r"[*_`~#]", "", text)

    # Remove emojis
    emoji_re = re.compile(
        r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\U0001F000-\U0001FAFF]"
    )
    text = emoji_re.sub("", text)

    # Remove common engagement copy artifacts
    text = re.sub(r"\b(KAYDET|HIZLI OKU|PILOT NOTU|BEĞEN|PAYLAŞ)\s*[-=:>]+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[-=]>", "", text)
    text = re.sub(r"[»«><|]", "", text)

    # Apply phonetic domain expansions
    for pattern, replacement in PHONETIC_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)

    # Clean multiple spaces and newlines
    text = re.sub(r"\s+", " ", text).strip()

    # Ensure final punctuation exists for natural prosodic cadence
    if text and text[-1] not in ".!?":
        text += "."

    return text


def free_comfyui_vram():
    """Tells ComfyUI server to offload models and free VRAM if running."""
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8188/free",
            data=json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass


class VoxCPMTTS:
    """
    High-level TTS engine using VoxCPM2.
    Can run directly if voxcpm is installed in the current Python environment,
    or smoothly delegates to the dedicated Python 3.12 venv.
    """

    def __init__(self, venv_python: str = None, female_prompt: str = None):
        self.venv_python = venv_python or VENV_PYTHON
        self.female_prompt = female_prompt or DEFAULT_FEMALE_PROMPT
        self._direct_model = None

    def _get_direct_model(self):
        """Loads VoxCPM model in-process if torch and voxcpm are available."""
        if self._direct_model is None:
            try:
                from voxcpm import VoxCPM
                self._direct_model = VoxCPM.from_pretrained(
                    "openbmb/VoxCPM2",
                    load_denoiser=False,
                    local_files_only=True,
                    optimize=False,
                )
            except Exception as e:
                logger.warning("Direct VoxCPM import failed: %s. Using venv subprocess.", e)
                self._direct_model = False
        return self._direct_model if self._direct_model is not False else None

    def synthesize(
        self,
        text: str,
        output_wav_path: str,
        prompt_instruction: str = None,
        reference_audio_path: str = None,
        cfg_value: float = 2.0,
        inference_timesteps: int = 10,
        normalize_loudness: bool = True,
    ) -> bool:
        """
        Synthesizes realistic female speech and saves to output_wav_path.

        Args:
            text: Clean spoken Turkish text.
            output_wav_path: Target .wav file path.
            prompt_instruction: Voice design prompt (defaults to realistic female voice).
            reference_audio_path: Optional reference audio for zero-shot voice cloning.
            cfg_value: Guidance scale (default 2.0).
            inference_timesteps: Sampling steps (default 10).
            normalize_loudness: Normalizes audio to -14 LUFS using ffmpeg.
        """
        clean_text = clean_text_for_speech(text)
        if not clean_text:
            logger.error("No valid text to synthesize after cleaning.")
            return False

        # Free ComfyUI VRAM if running so GPU has full capacity for VoxCPM2
        free_comfyui_vram()

        os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
        control = prompt_instruction or self.female_prompt

        # Check for optional reference audio
        ref_audio = reference_audio_path
        if not ref_audio:
            candidate_ref = os.path.join(BASE_DIR, "assets", "instagram", "audio", "female_reference.wav")
            if os.path.exists(candidate_ref):
                ref_audio = candidate_ref

        direct_model = self._get_direct_model()
        raw_output_path = output_wav_path if not normalize_loudness else output_wav_path + ".raw.wav"

        success = False
        if direct_model is not None:
            try:
                import soundfile as sf
                full_text = f"({control}) {clean_text}" if control else clean_text
                kwargs = {
                    "text": full_text,
                    "inference_timesteps": inference_timesteps,
                    "cfg_value": cfg_value,
                }
                if ref_audio and os.path.exists(ref_audio):
                    kwargs["reference_wav_path"] = ref_audio

                wav = direct_model.generate(**kwargs)
                sf.write(raw_output_path, wav, direct_model.tts_model.sample_rate)
                success = os.path.exists(raw_output_path) and os.path.getsize(raw_output_path) > 1000
            except Exception as e:
                logger.error("Direct synthesis error: %s. Falling back to subprocess.", e)
                success = False

        if not success:
            # Delegate to isolated Python 3.12 environment
            success = self._run_subprocess(
                clean_text,
                raw_output_path,
                control=control,
                ref_audio=ref_audio,
                cfg_value=cfg_value,
                inference_timesteps=inference_timesteps,
            )

        if not success or not os.path.exists(raw_output_path):
            logger.error("Synthesis failed to produce output at %s", raw_output_path)
            return False

        # Post-processing: Normalize loudness to -14 LUFS for Reels standard
        if normalize_loudness:
            try:
                norm_cmd = [
                    "ffmpeg", "-i", raw_output_path,
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=7",
                    "-c:a", "pcm_s16le", "-ar", "48000",
                    output_wav_path, "-y", "-loglevel", "error"
                ]
                res = subprocess.run(norm_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
                if res.returncode == 0 and os.path.exists(output_wav_path):
                    try:
                        os.unlink(raw_output_path)
                    except OSError:
                        pass
                    return True
                else:
                    logger.warning("loudnorm failed (%s), keeping raw audio.", res.stderr)
                    os.replace(raw_output_path, output_wav_path)
                    return True
            except Exception as e:
                logger.warning("Loudness normalization exception: %s", e)
                os.replace(raw_output_path, output_wav_path)
                return True

        return True

    def _run_subprocess(
        self,
        clean_text: str,
        output_path: str,
        control: str = None,
        ref_audio: str = None,
        cfg_value: float = 2.0,
        inference_timesteps: int = 10,
    ) -> bool:
        """Executes synthesis in the dedicated venv Python process."""
        python_bin = self.venv_python if os.path.exists(self.venv_python) else "python3"
        safe_text = json.dumps(clean_text)
        safe_control = json.dumps(control or "")
        safe_output = json.dumps(output_path)
        safe_ref = json.dumps(ref_audio) if (ref_audio and os.path.exists(ref_audio)) else "None"
        cfg_float = float(cfg_value)
        steps_int = int(inference_timesteps)

        script_code = f"""
import sys
import torch
import soundfile as sf
from voxcpm import VoxCPM

text = {safe_text}
control = {safe_control}
out_path = {safe_output}
ref_path = {safe_ref}
cfg = {cfg_float}
steps = {steps_int}

prompt = f"({{control}}) {{text}}" if control else text

use_device = "cpu"
if torch.cuda.is_available():
    try:
        free_b, total_b = torch.cuda.mem_get_info()
        if free_b >= int(5.5 * (1024 ** 3)):
            use_device = "cuda"
    except Exception:
        use_device = "cuda"

wav = None
sample_rate = 48000
for dev in ([use_device, "cpu"] if use_device == "cuda" else ["cpu"]):
    try:
        cur_steps = steps if dev == "cuda" else min(steps, 6)
        model = VoxCPM.from_pretrained(
            "openbmb/VoxCPM2",
            load_denoiser=False,
            local_files_only=True,
            optimize=False,
            device=dev,
        )
        kwargs = {{
            "text": prompt,
            "inference_timesteps": cur_steps,
            "cfg_value": cfg,
        }}
        if ref_path is not None:
            kwargs["reference_wav_path"] = ref_path
        wav = model.generate(**kwargs)
        sample_rate = model.tts_model.sample_rate
        break
    except Exception as err:
        if dev == "cuda":
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass
            continue
        raise err

if wav is None:
    sys.exit(1)

sf.write(out_path, wav, sample_rate)
print("SUCCESS")
"""
        try:
            custom_env = dict(os.environ)
            custom_env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
            res = subprocess.run(
                [python_bin, "-c", script_code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=180,
                env=custom_env,
            )
            if res.returncode == 0 and "SUCCESS" in res.stdout:
                return True
            logger.error("Subprocess TTS error (code %d): %s", res.returncode, res.stderr[-400:])
            return False
        except Exception as e:
            logger.error("Subprocess execution exception: %s", e)
            return False

    def generate_voiceover_for_post(self, post_data: dict, output_path: str = None) -> str:
        """
        High-level helper for Instagram post / Reel:
        - Resolves or generates the voiceover script.
        - Synthesizes realistic Turkish female voice.
        - Updates post_data with voiceover metadata.
        - Returns relative path to the generated voiceover file.
        """
        post_id = post_data.get("id") or "post_reels_preview"
        filename = f"{post_id}_voiceover.wav"
        abs_output = output_path or os.path.join(VOICEOVERS_DIR, filename)

        # Retrieve or construct the spoken voiceover script
        speech_text = post_data.get("voiceover_text") or post_data.get("speech_text")
        if not speech_text:
            from .content_generator import ContentGenerator
            cg = ContentGenerator()
            speech_text = cg.generate_reels_voiceover_script(post_data)
            post_data["voiceover_text"] = speech_text

        display_script = post_data.get("voiceover_display_text") or speech_text

        # Use natural, energetic female voice instruction
        hook_tone = post_data.get("hook_tone", "energetic")
        tone_descriptor = (
            "cheerful, energetic, fast-paced and engaging"
            if hook_tone in ("urgency", "hype", "energetic", "bold", "challenge", "warning", "question")
            else "warm, friendly, confident and professional"
        )
        voice_prompt = (
            f"A natural, {tone_descriptor} Turkish young female voice, "
            "clear articulation, fluent Turkish pronunciation with studio clarity."
        )

        ok = self.synthesize(
            text=speech_text,
            output_wav_path=abs_output,
            prompt_instruction=voice_prompt,
        )
        if not ok or not os.path.exists(abs_output) or os.path.getsize(abs_output) <= 1000:
            # Automatic 2nd attempt after freeing GPU memory to guarantee every Reel is voiced
            free_comfyui_vram()
            ok = self.synthesize(
                text=speech_text,
                output_wav_path=abs_output,
                prompt_instruction=voice_prompt,
                inference_timesteps=8,
            )

        if ok and os.path.exists(abs_output) and os.path.getsize(abs_output) > 1000:
            rel_path = f"./assets/instagram/voiceovers/{filename}"
            post_data["voiceover_path"] = rel_path
            post_data["has_voiceover"] = True
            post_data["voiceover_engine"] = "VoxCPM2 (Doğal Türkçe Kadın Sesi)"
            post_data["voiceover_prompt"] = voice_prompt

            # Probe duration and compute synchronized subtitle chunks
            dur = 0.0
            try:
                probe_cmd = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", abs_output
                ]
                pres = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
                dur = float((pres.stdout or "").strip() or 0.0)
                if dur > 0:
                    post_data["voiceover_duration"] = round(dur, 2)
            except Exception:
                pass

            if dur <= 0:
                dur = 10.0
                post_data["voiceover_duration"] = dur

            post_data["voiceover_chunks"] = build_subtitle_chunks(display_script, dur)
            return rel_path

        return ""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="VoxCPM2 Turkish Female Voiceover Generator")
    parser.add_argument("--text", "-t", type=str, default="Pozitron Market'ten günün FPV fırsatı! En iyi drone parçaları şimdi stokta.")
    parser.add_argument("--output", "-o", type=str, default="/tmp/voxcpm2_test_voice.wav")
    parser.add_argument("--prompt", "-p", type=str, default=DEFAULT_FEMALE_PROMPT)
    parser.add_argument("--test", action="store_true", help="Run a quick test synthesis")

    args = parser.parse_args()

    tts = VoxCPMTTS()
    print(f"Generating realistic female voice for: {args.text}")
    success = tts.synthesize(args.text, args.output, prompt_instruction=args.prompt)
    if success:
        print(f"Voiceover successfully generated and saved to: {args.output}")
    else:
        print("Failed to generate voiceover.")
        sys.exit(1)
