"""
Synthesizes a royalty-free cyberpunk / electronic FPV drone audio loop (8 seconds, 130 BPM).
Uses pure Python standard library (wave, math, struct, random). Zero external dependencies.
"""

import math
import os
import random
import struct
import wave

def generate_default_beat(output_wav_path: str, duration_sec: float = 8.0):
    sample_rate = 44100
    total_samples = int(sample_rate * duration_sec)
    bpm = 128.0
    beat_sec = 60.0 / bpm
    samples_per_beat = int(sample_rate * beat_sec)

    left_channel = [0.0] * total_samples
    right_channel = [0.0] * total_samples

    # 1. Four-on-the-floor Kick Drum
    kick_len = int(sample_rate * 0.28)
    for b in range(int(duration_sec / beat_sec) + 1):
        start = b * samples_per_beat
        for i in range(kick_len):
            idx = start + i
            if idx >= total_samples:
                break
            t = i / sample_rate
            env = math.exp(-14.0 * t)
            freq = 45.0 + 130.0 * math.exp(-32.0 * t)
            sample = math.sin(2.0 * math.pi * freq * t) * env * 0.75
            left_channel[idx] += sample
            right_channel[idx] += sample

    # 2. Snare / Clap on beats 2 and 4 of each 4-beat bar
    snare_len = int(sample_rate * 0.22)
    for b in range(int(duration_sec / beat_sec) + 1):
        if b % 2 == 1:
            start = b * samples_per_beat
            for i in range(snare_len):
                idx = start + i
                if idx >= total_samples:
                    break
                t = i / sample_rate
                env = math.exp(-16.0 * t)
                noise = (random.random() * 2.0 - 1.0) * 0.45
                tone = math.sin(2.0 * math.pi * 190.0 * t) * 0.25
                sample = (noise + tone) * env
                left_channel[idx] += sample * 0.85
                right_channel[idx] += sample * 0.85

    # 3. Fast 1/8 note Hi-hats
    hh_len = int(sample_rate * 0.06)
    eighth_samples = samples_per_beat // 2
    for e in range(int(total_samples / eighth_samples)):
        start = e * eighth_samples + eighth_samples // 2
        for i in range(hh_len):
            idx = start + i
            if idx >= total_samples:
                break
            t = i / sample_rate
            env = math.exp(-40.0 * t)
            noise = (random.random() * 2.0 - 1.0) * 0.22
            left_channel[idx] += noise * env * 0.9
            right_channel[idx] += noise * env * 0.7

    # 4. Melodic Cyberpunk Sub-Bass & Synth Arp
    # Notes in D minor (D2, F2, G2, A2) -> (73.42Hz, 87.31Hz, 98.00Hz, 110.00Hz)
    bass_notes = [73.42, 73.42, 87.31, 73.42, 98.00, 87.31, 110.00, 98.00]
    note_len = samples_per_beat
    for n_idx in range(int(total_samples / note_len)):
        freq = bass_notes[n_idx % len(bass_notes)]
        start = n_idx * note_len
        for i in range(note_len):
            idx = start + i
            if idx >= total_samples:
                break
            t = i / sample_rate
            env = math.exp(-2.5 * (t / beat_sec))
            # Sawtooth approximation with sine harmonics
            saw = (
                math.sin(2.0 * math.pi * freq * t) +
                0.5 * math.sin(2.0 * math.pi * freq * 2 * t) +
                0.25 * math.sin(2.0 * math.pi * freq * 3 * t)
            ) * 0.28 * env
            left_channel[idx] += saw
            right_channel[idx] += saw

    # Master limiter & clipping protection
    max_amp = 0.001
    for s in left_channel + right_channel:
        if abs(s) > max_amp:
            max_amp = abs(s)

    gain = 0.88 / max_amp if max_amp > 0.88 else 1.0

    os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
    with wave.open(output_wav_path, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        packed_frames = bytearray()
        for i in range(total_samples):
            # Fade out last 0.8 seconds to avoid pop
            if i > total_samples - int(sample_rate * 0.8):
                fade_pos = (total_samples - i) / (sample_rate * 0.8)
            else:
                fade_pos = 1.0

            l_val = int(max(-32767, min(32767, left_channel[i] * gain * fade_pos * 32767)))
            r_val = int(max(-32767, min(32767, right_channel[i] * gain * fade_pos * 32767)))
            packed_frames.extend(struct.pack('<hh', l_val, r_val))
        wf.writeframes(packed_frames)

    return output_wav_path

if __name__ == '__main__':
    out = os.path.join(os.path.dirname(__file__), '..', 'assets', 'instagram', 'audio', 'fpv_beat_default.wav')
    generate_default_beat(os.path.abspath(out))
    print(f"Generated default beat at {out}")
