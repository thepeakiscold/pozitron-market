"""
Human-voice text utilities for the Instagram PR pipeline.

The catalog/dataset copy and the AI writers historically produced obviously
machine-made text: bracketed labels ("[FREKANS]", "[ONLINE ARAC]"), ALL-CAPS
headlines, "KAYDET ->" mechanics, arrows and AI disclosure markers. This module
normalises that into calm, sentence-case, human-sounding Turkish so posts read
like a person wrote them.
"""
import re

# Domain terms that must stay upper-case (or keep their exact casing) even when
# they appear inside an ALL-CAPS string.
ACRONYMS = {
    'FPV', 'VTX', 'VRX', 'TX', 'RX', 'PID', 'ELRS', 'GPS', 'ESC', 'FC', 'AIO',
    'RPM', 'HD', 'HDZERO', 'WALKSNAIL', 'LIPO', 'LI-ION', 'SBUS', 'CRSF', 'TBS',
    'DJI', 'USB', 'LED', 'BEC', 'UBEC', 'RSSI', 'LQ', 'DVR', 'SMA', 'MMCX',
    'UFL', 'RHCP', 'LHCP', 'KV', 'MAH', 'IMU', 'OSD', 'MSP', 'DFU', 'CLI',
    'UART', 'I2C', 'SPI', 'CAN', 'PWM', 'DSHOT', 'BLHELI', 'BF', 'GPS', 'VTOL',
    'HDMI', 'CP', 'RF', 'PCB', 'CPU', 'RAM', 'USB-C', 'TYPE-C', 'X8', 'M12',
}

# Sentence/line prefixes that look like automated "engagement mechanics".
_MARKER_PATTERNS = [
    r'^\s*KAYDET\s*[-=]>\s*',
    r'^\s*HIZLI\s+OKU\s*:\s*',
    r'^\s*PILOT\s+NOTU\s*:\s*',
    r'^\s*PILOT\s+İPUCU\s*:\s*',
    r'^\s*NOT\s*:\s*',
    r'^\s*ÖNEMLİ\s*:\s*',
]

# Whole blocks / labels that should simply be dropped.
_DROP_LINE_PATTERNS = [
    r'^\s*\[OTOMATIK\s+DM\s+ALARM[Iİ]?\]\s*$',
    r'^\s*\[AI\s+GORSEL\]',
    r'^\s*\[AI\s+GÖRSEL\]',
    r'^\s*\[GORSEL\s+KAYNAK\]',
    r'^\s*\[GÖRSEL\s+KAYNAK\]',
    r'^\s*\[EN\]\s*',
    r'^\s*KAYDIR\s*>',
    r'^\s*SLAYT',
]

_EMOJI_RE = re.compile(r'[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\U0001F000-\U0001FAFF]')
_BRACKET_TAG_RE = re.compile(r'\[[^\]\n]{1,40}\]')
_ARROW_RE = re.compile(r'\s*(?:-{1,2}>|>>|<<|=>|->|[<>])\s*')


def _tr_lower(s: str) -> str:
    """Lowercase that keeps Latin words intact and clears Turkish 'İ' artifacts."""
    return s.lower().replace('\u0307', '')


def _fix_token(tok: str) -> str:
    """Normalises a single whitespace token for sentence-case text."""
    if not tok:
        return tok
    m = re.match(r'^([^\wÇĞİÖŞÜçğıöşü]*)([\wÇĞİÖŞÜçğıöşü\'’\-]+)([^\w]*)$', tok)
    if not m:
        return tok
    pre, core, post = m.group(1), m.group(2), m.group(3)
    letters = [c for c in core if c.isalpha()]
    if not letters:
        return tok
    upper_core = core.upper()
    if upper_core in ACRONYMS or core in ACRONYMS:
        return pre + core + post
    if any(ch.isdigit() for ch in core):
        return pre + core + post
    # Proper nouns we always keep capitalised.
    if core.lower() in ('pozitron', 'pozitronmarket', 'betaflight', 'teknofest', 'dji', 'walksnail'):
        return pre + core.capitalize() + post
    if all(c.isupper() for c in letters) and len(letters) >= 2:
        return pre + _tr_lower(core) + post
    return tok


def _sentence_case(text: str) -> str:
    text = ' '.join(_fix_token(t) for t in text.split())
    if not text:
        return text
    # Capitalise the first alphabetic character.
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1:]
    return text


def _strip_markers(line: str) -> str:
    for pat in _MARKER_PATTERNS:
        line = re.sub(pat, '', line, flags=re.IGNORECASE)
    line = _ARROW_RE.sub(' ', line)
    return line.strip()


def humanize_line(text, max_len: int = None) -> str:
    """Cleans a short label/headline into calm sentence-case human text."""
    if text is None:
        return ''
    s = str(text)
    s = _EMOJI_RE.sub('', s)
    s = _BRACKET_TAG_RE.sub(' ', s)
    s = _strip_markers(s)
    s = _sentence_case(s)
    s = re.sub(r'\s+', ' ', s).strip(' .,-|')
    if max_len and len(s) > max_len:
        s = s[:max_len].rstrip() + '…'
    return s


def humanize_caption(text, max_len: int = 1400) -> str:
    """Cleans a long caption: drops AI markers, fixes ALL-CAPS lines, tidy spacing."""
    if not text:
        return ''
    s = str(text)
    s = _EMOJI_RE.sub('', s)
    s = _BRACKET_TAG_RE.sub(' ', s)
    s = s.replace('[EN]', '').replace('[en]', '')

    out_lines = []
    for raw in s.split('\n'):
        line = raw.rstrip()
        stripped = line.strip()
        if any(re.match(p, stripped, flags=re.IGNORECASE) for p in _DROP_LINE_PATTERNS):
            continue
        line = _strip_markers(line)
        letters = [c for c in line if c.isalpha()]
        if letters and all(c.isupper() for c in letters) and len(letters) >= 4:
            line = _sentence_case(line)
        else:
            line = ' '.join(_fix_token(t) for t in line.split())
        out_lines.append(line)

    # Collapse 3+ blank lines into one, trim.
    s = '\n'.join(out_lines)
    s = re.sub(r'\n{3,}', '\n\n', s).strip()
    if max_len and len(s) > max_len:
        s = s[:max_len].rstrip() + '…'
    return s


def humanize_visual_summary(vs: dict) -> dict:
    """Humanises the on-image text fields of a visual_summary dict in place."""
    if not isinstance(vs, dict):
        return vs
    vs = dict(vs)
    if vs.get('badge'):
        vs['badge'] = humanize_line(vs['badge'], 34)
    if vs.get('headline'):
        vs['headline'] = humanize_line(vs['headline'], 46)
    if vs.get('subhead'):
        vs['subhead'] = humanize_line(vs['subhead'], 60)
    points = vs.get('key_points')
    if isinstance(points, list):
        cleaned = []
        for p in points:
            hp = humanize_line(p, 54)
            # Drop the old "[1] ..." numbering artifacts.
            hp = re.sub(r'^[0-9]{1,2}[\.\)]\s*', '', hp)
            if hp:
                cleaned.append(hp)
        vs['key_points'] = cleaned
    cta = vs.get('cta')
    if isinstance(cta, str):
        vs['cta'] = humanize_line(cta, 48)
    return vs


def humanize_content(content: dict) -> dict:
    """Applies humanization to a generated content dict (title/caption/visual_summary)."""
    if not isinstance(content, dict):
        return content
    if content.get('title'):
        content['title'] = humanize_line(content['title'], 70)
    if content.get('caption'):
        content['caption'] = humanize_caption(content['caption'])
    if content.get('visual_summary'):
        content['visual_summary'] = humanize_visual_summary(content['visual_summary'])
    return content
