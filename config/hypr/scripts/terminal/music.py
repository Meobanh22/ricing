#!/usr/bin/env python3
# music.py — Unified Terminal Music Visualizer & Synced Lyrics with Serena Wine theme.

import os
import sys
import time
import json
import re
import select
import socket
import shutil
import signal
import termios
import tty
import atexit
import threading
import urllib.request
import urllib.parse
import urllib.error
import subprocess
import math
import hashlib
import html
from difflib import SequenceMatcher
import tempfile
import unicodedata
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "system"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from palette import PALETTE, SUNSET_STOPS
from music_idle import IdleBackdrop, TerminalInput
from music_layout import visualizer_regions
from music_focus import MusicFocus
try:
    from music_lyrics import LyricsCanvas
except ImportError:
    LyricsCanvas = None
try:
    from music_spectrum import SpectrumCanvas
except ImportError:
    SpectrumCanvas = None
try:
    import yaml
except ImportError:
    yaml = None

# === COLOR TOKENS (Serena Wine Palette) ===
def hex_to_rgb(hex_code):
    h = hex_code.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def fg(hex_code):
    r, g, b = hex_to_rgb(hex_code)
    return f"\x1b[38;2;{r};{g};{b}m"

def bg(hex_code):
    r, g, b = hex_to_rgb(hex_code)
    return f"\x1b[48;2;{r};{g};{b}m"

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
ITALIC = "\x1b[3m"

CREAM_WHITE = PALETTE["cream_white"]
SOFT_PINK = PALETTE["soft_pink"]
MUTED_PINK = PALETTE["muted_pink"]
C_LYRIC_HIGHLIGHT = PALETTE["light_red"]
DARK_WINE = PALETTE["dark_wine"]

RENDER_FPS = 60
SPECTRUM_GAIN = 2.0
LINE_FADE_IN = 0.16
LINE_FADE_OUT = 0.10

# Use the generated token palette, or the source tokens when running in the repo.
GRADIENT_STOPS = SUNSET_STOPS
_tokens_path = Path(__file__).resolve().parents[3] / "theme" / "tokens.json"
if _tokens_path.is_file():
    _gradient = json.loads(_tokens_path.read_text(encoding="utf-8"))["gradient"]
    GRADIENT_STOPS = [
        (float(position) / 100, color)
        for color, position in re.findall(r"(#[0-9a-fA-F]{6})\s+(\d+(?:\.\d+)?)%", _gradient)
    ]

ANSI_STYLE = re.compile(r"\x1b\[[0-9;]*m")


def cell_width(char):
    if unicodedata.category(char) in ("Mn", "Me", "Cf"):
        return 0
    return 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1


def clip_line(line, width):
    """Clip styled text in terminal cells, keeping control text out of frames."""
    parts = []
    cells = 0
    index = 0
    while index < len(line):
        match = ANSI_STYLE.match(line, index)
        if match:
            parts.append(match.group())
            index = match.end()
            continue
        char = line[index]
        index += 1
        if unicodedata.category(char) == "Cc":
            continue
        size = cell_width(char)
        if cells + size > width:
            break
        parts.append(char)
        cells += size
    return "".join(parts) + RESET


def text_width(text):
    return sum(cell_width(char) for char in text)


def lyric_spans(text, width):
    """Wrap a lyric in terminal cells while retaining its character offsets."""
    spans = []
    start = 0
    while start < len(text):
        end = start
        cells = 0
        space = None
        while end < len(text) and cells + cell_width(text[end]) <= width:
            cells += cell_width(text[end])
            if text[end].isspace():
                space = end
            end += 1
        if end < len(text) and space is not None and space > start:
            end = space
        end = max(start + 1, end)
        spans.append((start, end))
        start = end
        while start < len(text) and text[start].isspace():
            start += 1
    return spans or [(0, 0)]


def karaoke_progress(text, position, start, end, cues=()):
    """Use word cues when present; otherwise estimate within the timed line."""
    if not text or position < start:
        return 0
    if not cues:
        words = list(re.finditer(r"\S+", text))
        if not words:
            return 0
        duration = max(0.1, end - start)
        cues = [(start + index * duration / len(words), word.start())
                for index, word in enumerate(words)]
    anchors = list(cues)
    if anchors[-1][1] < len(text):
        anchors.append((max(end, anchors[-1][0] + 0.1), len(text)))
    if position < anchors[0][0]:
        return 0
    prefix = len(text)
    for (left_time, left_index), (right_time, right_index) in zip(anchors, anchors[1:]):
        if position < right_time:
            progress = max(0.0, min(1.0, (position - left_time) / max(0.001, right_time - left_time)))
            prefix = left_index + progress * (right_index - left_index)
            break
    return max(0, min(len(text), prefix))


def karaoke_prefix(text, position, start, end, cues=()):
    prefix = int(karaoke_progress(text, position, start, end, cues))
    while prefix < len(text) and unicodedata.combining(text[prefix]):
        prefix += 1
    return prefix


def ease(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def mix_color(left, right, amount):
    amount = max(0.0, min(1.0, amount))
    rgb = (round(a + (b - a) * amount) for a, b in zip(hex_to_rgb(left), hex_to_rgb(right)))
    return "#" + "".join(f"{value:02x}" for value in rgb)


def line_visibility(position, start, end):
    return min(ease((position - start) / LINE_FADE_IN), ease((end - position) / LINE_FADE_OUT))


def karaoke_text(text, prefix, scale, visibility=1.0):
    """Keep glyph boundaries stable and blend the active character continuously."""
    parts = []
    clusters = []
    for index, char in enumerate(text):
        if clusters and unicodedata.combining(char):
            clusters[-1][1] += char
        else:
            clusters.append([index, char])
    parts.append(BOLD)
    previous_color = None
    for index, content in clusters:
        coverage = ease((prefix - index) / len(content))
        color = mix_color(DARK_WINE, mix_color(CREAM_WHITE, C_LYRIC_HIGHLIGHT, coverage), visibility)
        if color != previous_color:
            parts.append(fg(color))
            previous_color = color
        parts.append(f"\x1b]66;s={scale};{content}\x07" if scale > 1 else content)
    return "".join(parts) + RESET


def lyric_text(text, scale, visibility=1.0):
    color = mix_color(SOFT_PINK, PALETTE["pure_white"], visibility)
    content = f"\x1b]66;s={scale};{text}\x07" if scale > 1 else text
    return BOLD + fg(color) + bg(DARK_WINE) + content + RESET


@lru_cache(maxsize=256)
def gradient_color(fraction):
    fraction = max(0.0, min(1.0, fraction))
    for (start, left), (end, right) in zip(GRADIENT_STOPS, GRADIENT_STOPS[1:]):
        if fraction <= end:
            mix = max(0.0, (fraction - start) / (end - start))
            rgb = [round(a + (b - a) * mix) for a, b in zip(hex_to_rgb(left), hex_to_rgb(right))]
            return "#" + "".join(f"{value:02x}" for value in rgb)
    return GRADIENT_STOPS[-1][1]


def resample_bars(values, count):
    """Average frequency bins into visible bars without dropping narrow peaks."""
    if not values:
        return [0.0] * count
    result = []
    scale = len(values) / count
    for index in range(count):
        start, end = index * scale, (index + 1) * scale
        total = 0.0
        for source in range(math.floor(start), min(len(values), math.ceil(end))):
            overlap = min(end, source + 1) - max(start, source)
            total += max(0.0, min(100.0, values[source])) * overlap
        result.append(total / scale)
    return result


def mirrored_bars(values, count):
    """Mirror frequency detail with a small contribution from live RMS energy."""
    half = resample_bars(values, (count + 1) // 2)
    if values:
        energy = math.sqrt(sum(max(0.0, min(100.0, value)) ** 2 for value in values) / len(values))
        half = [0.7 * value + 0.3 * energy for value in half]
    return half[::-1] + half[count % 2:]


CACHE_DIR = os.path.expanduser("~/.cache/serena_lyrics")


def video_identity(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname in ("www.youtube.com", "youtube.com", "music.youtube.com", "m.youtube.com"):
        return urllib.parse.parse_qs(parsed.query).get("v", [url])[0]
    if parsed.hostname == "youtu.be":
        return parsed.path.strip("/")
    return url


def sync_key(title, artist, url=""):
    identity = video_identity(url) or json.dumps([clean_track_name(title), artist], ensure_ascii=False)
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def load_sync_offset(key):
    try:
        data = json.loads((Path(CACHE_DIR) / "sync.json").read_text(encoding="utf-8"))
        value = float(data.get(key, 0.0))
        return value if math.isfinite(value) else 0.0
    except (OSError, ValueError, TypeError, AttributeError):
        return 0.0


def save_sync_offset(key, offset):
    if not key:
        return
    path = Path(CACHE_DIR) / "sync.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data[key] = offset
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        pass

# === TERMINAL STATE MANAGEMENT ===
old_termios = None
terminal_active = False

def init_terminal():
    global old_termios, terminal_active
    if sys.stdin.isatty():
        old_termios = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    # Enter alternate buffer, hide cursor, clear screen
    terminal_active = True
    sys.stdout.write("\x1b[?2026l\x1b[?1049h\x1b[?25l\x1b[2J")
    sys.stdout.flush()

def cleanup_terminal():
    global old_termios, terminal_active
    if not terminal_active:
        return
    terminal_active = False
    # Show cursor, leave alternate buffer, reset styles
    sys.stdout.write("\x1b[?2026l\x1b[?25h\x1b[?1049l\x1b[0m\n")
    sys.stdout.flush()
    if old_termios and sys.stdin.isatty():
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_termios)
        except Exception:
            pass

atexit.register(cleanup_terminal)

def signal_handler(sig, frame):
    sys.exit(0)

# === LYRICS FETCHER & PARSER ===
def clean_track_name(text):
    text = unicodedata.normalize("NFC", html.unescape(text or ""))
    text = re.sub(r"^\(\d+\)\s*", "", text)
    text = re.sub(r"[\(\[\{「][^\)\]\}」]*(?:\bofficial\b|\bmv\b|\bvideo\b|\baudio\b|\blyrics?\b|\bvisuali[sz]er\b|\bfrom\b|\bvietsub\b)[^\)\]\}」]*[\)\]\}」]", "", text, flags=re.I)
    # A pipe can separate artist and song, not only a trailing video label.
    # Keeping both names prevents unrelated tracks by one artist matching.
    decoration = r'(?:official|music|video|mv|audio|lyrics?|visuali[sz]er|hd|4k|1080p|lofi|remix)'
    parts = re.split(r'\s*[|｜]\s*', text)
    if len(parts) > 1:
        parts = [part.strip() for part in parts
                 if part.strip() and not re.fullmatch(rf'(?:{decoration}\s*)+', part.strip(), re.I)]
        text = ' - '.join(parts)
    text = re.sub(r"\s+(?:official(?:\s+music)?\s*(?:video|audio|mv)?|lyrics?\s*(?:video)?|visuali[sz]er)\s*$", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" -_|•")


def match_key(text):
    text = unicodedata.normalize("NFKD", html.unescape(text or "").casefold().replace("đ", "d"))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join("".join(char if char.isalnum() else " " for char in text).split())


def artist_forms(artist):
    artist = re.sub(r"\s*(?:-\s*)?(?:topic|official(?:\s+music)?|vevo)\s*$", "", artist or "", flags=re.I).strip()
    pieces = [artist] + re.split(r"[,;&/]|\b(?:feat(?:uring)?|ft|và|x)\b\.?", artist, flags=re.I)
    forms = set()
    for piece in pieces:
        for variant in (piece, re.sub(r"\([^)]*\)", "", piece)):
            key = match_key(variant).replace(" ", "")
            if key:
                forms.add(key)
    return forms


def version_markers(title):
    key = match_key(title)
    markers = {name for name in ("instrumental", "karaoke", "live", "acoustic", "remix", "cover", "lofi")
               if re.search(r"\b" + name + r"\b", key)}
    if "khong loi" in key:
        markers.add("instrumental")
    if re.search(r"\b(?:sped up|spedup|speed up|speedup|nightcore)\b", key):
        markers.add("sped-up")
    if re.search(r"\b(?:slowed|slow reverb)\b", key):
        markers.add("slowed")
    return markers


class TrackCandidates(list):
    def __init__(self, candidates, versions):
        super().__init__(candidates)
        self.versions = versions


def track_candidates(title, artist=""):
    versions = version_markers(title)
    title = clean_track_name(title)
    candidates = []
    # YouTube titles use both "Artist - Track" and "Track - Artist".
    parts = re.split(r"\s+[-–—/]\s+", title, maxsplit=1)
    if len(parts) == 2 and all(parts):
        candidates.extend(((parts[0], parts[1]), (parts[1], parts[0])))
    known_performer = artist_forms(artist)
    candidates.sort(key=lambda pair: not bool(known_performer & artist_forms(pair[1])))
    candidates.append((title, artist.strip()))
    seen = set()
    unique = []
    for track, singer in candidates:
        key = (match_key(track), match_key(singer))
        if key[0] and key not in seen:
            seen.add(key)
            unique.append((track, singer))
    return TrackCandidates(unique, versions)


def clean_query(title, artist=""):
    return list(dict.fromkeys(f"{track} {singer}".strip() for track, singer in track_candidates(title, artist)))


def record_match_score(item, candidates, duration=None):
    if not isinstance(item, dict) or not (item.get("syncedLyrics") or item.get("plainLyrics") or (item.get("hasWordSync") and item.get("lyricsfile"))):
        return None
    if item.get("instrumental"):
        return None
    expected_version = getattr(candidates, "versions", set())
    if version_markers(item.get("trackName") or item.get("name") or "") != expected_version:
        return None
    name = clean_track_name(item.get("trackName") or item.get("name") or "")
    singers = artist_forms(item.get("artistName") or "")
    titles = {match_key(name), match_key(re.sub(r"\([^)]*\)", "", name))}
    split = re.split(r"\s+[-–—/]\s+", name, maxsplit=1)
    if len(split) == 2:
        # Some records put the performer inside trackName instead of artistName.
        for track, singer in ((split[0], split[1]), (split[1], split[0])):
            titles.add(match_key(track))
            singers.update(artist_forms(singer))
    titles.discard("")
    best = None
    for track, singer in candidates:
        expected = match_key(track)
        expected_forms = artist_forms(singer)
        if expected_forms and not (expected_forms & singers):
            continue
        title_score = 0.0
        for actual in titles:
            if actual.replace(" ", "") == expected.replace(" ", ""):
                title_score = 1.0
                break
            overlap = len(set(actual.split()) & set(expected.split())) / max(1, len(set(actual.split()) | set(expected.split())))
            ratio = SequenceMatcher(None, expected, actual).ratio()
            if overlap >= 0.8 and ratio >= 0.92:
                title_score = max(title_score, ratio)
        if title_score == 0:
            continue
        # A bare, ambiguous title without performer information is insufficient.
        if not expected_forms and (len(expected.split()) < 3 or len(expected) < 10):
            continue
        score = title_score * 100 + (10 if expected_forms else 0)
        try:
            record_duration = float(item.get("duration") or 0)
            difference = abs(record_duration - duration) if duration and record_duration else None
        except (TypeError, ValueError):
            difference = None
        if difference is not None:
            # Music videos may include an intro/outro absent from the recording.
            if difference > max(90, duration * 0.35):
                continue
            score += max(0, 10 - difference / 6)
        score += 1 if item.get("syncedLyrics") else 0
        score += 8 if item.get("hasWordSync") and item.get("lyricsfile") else 0
        best = score if best is None else max(best, score)
    return best


def select_lyrics(records, candidates, duration=None):
    ranked = [(score, item) for item in records
              if (score := record_match_score(item, candidates, duration)) is not None]
    return max(ranked, key=lambda entry: entry[0])[1] if ranked else None


def local_lrc_path(media_url):
    if not media_url:
        return None
    parsed = urllib.parse.urlparse(media_url)
    if parsed.scheme not in ("", "file"):
        return None
    raw_path = urllib.parse.unquote(parsed.path)
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        return None
    lrc = path.with_suffix(".lrc")
    return lrc if lrc.is_file() else None


def load_local_lyrics(media_url):
    lrc = local_lrc_path(media_url)
    if lrc is None:
        return None
    try:
        text = lrc.read_text(encoding="utf-8-sig")
    except OSError:
        return None
    lines, _ = parse_lyrics(text)
    if lines:
        return {"syncedLyrics": text, "plainLyrics": "\n".join(line for _, line in lines if line)}
    plain = text.strip()
    return {"syncedLyrics": None, "plainLyrics": plain} if plain else None


def lyrics_cache_path(title, artist, duration=None):
    identity = json.dumps([unicodedata.normalize("NFC", title).casefold(),
                           unicodedata.normalize("NFC", artist).casefold(),
                           round(duration or 0)], ensure_ascii=False).encode("utf-8")
    return Path(CACHE_DIR) / ("v3_" + hashlib.sha256(identity).hexdigest() + ".json")


def fetch_lrclib(title, artist="", duration=None):
    candidates = track_candidates(title, artist)
    if not candidates:
        return None
    cache_file = lyrics_cache_path(title, artist, duration)
    cached = []
    # Validate all cached records too: older versions could save an unrelated hit.
    paths = [cache_file] + list(Path(CACHE_DIR).glob("*.json"))
    for path in dict.fromkeys(paths):
        try:
            cached.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    best = select_lyrics(cached, candidates, duration)
    fallback = best
    if best is not None and (best.get("hasWordSync") or best.get("_lookup_version", 0) >= 3):
        return best

    searches = []
    for track, singer in candidates:
        params = {"track_name": track}
        if singer:
            singer = re.split(r"\b(?:feat(?:uring)?|ft)\b\.?", singer, maxsplit=1, flags=re.I)[0]
            params["artist_name"] = re.sub(r"\s*(?:-\s*)?(?:topic|official|vevo)\s*$", "", singer, flags=re.I).strip()
        searches.append(params)
    searches.extend({"track_name": track} for track, _ in candidates)
    seen = set()
    for params in searches:
        query = urllib.parse.urlencode(params)
        if query in seen:
            continue
        if seen:
            time.sleep(0.25)
        seen.add(query)
        try:
            req = urllib.request.Request("https://lrclib.net/api/search?" + query,
                                         headers={"User-Agent": "SerenaLyrics/2.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.load(response)
            if not isinstance(data, list):
                continue
            best = select_lyrics(data, candidates, duration)
            if best is None:
                continue
            best = dict(best, _lookup_version=3)
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                temporary = cache_file.with_suffix(f".{threading.get_ident()}.tmp")
                temporary.write_text(json.dumps(best, ensure_ascii=False), encoding="utf-8")
                os.replace(temporary, cache_file)
            except OSError:
                pass
            return best
        except urllib.error.HTTPError as error:
            if error.code in (429, 503):
                # Stop this lookup rather than retrying during a server cooldown.
                return fallback
        except (OSError, ValueError):
            continue
    return fallback


def parse_lyrics(lrc_text):
    """Parse ordinary/enhanced LRC, repeated line tags and a global offset."""
    if not lrc_text:
        return [], {}
    stamp = r"(\d+):(\d+(?:\.\d+)?)"
    line_tags = re.compile(r"^(?P<tags>(?:\[" + stamp + r"\])+)(?P<body>.*)$")
    word_tags = re.compile(r"<" + stamp + r">")
    offset_match = re.search(r"\[offset:([+-]?\d+)\]", lrc_text, re.I)
    offset = int(offset_match.group(1)) / 1000 if offset_match else 0.0
    lines, word_cues = [], {}
    for raw in unicodedata.normalize("NFC", lrc_text).splitlines():
        raw = "".join(char for char in raw if unicodedata.category(char) not in ("Cc", "Cs"))
        match = line_tags.match(raw.strip())
        if not match:
            continue
        times = [int(minutes) * 60 + float(seconds)
                 for minutes, seconds in re.findall(r"\[" + stamp + r"\]", match["tags"])]
        body = match["body"]
        parts, cues = [], []
        previous_end = 0
        length = 0
        for tag in word_tags.finditer(body):
            part = body[previous_end:tag.start()]
            parts.append(part)
            length += len(part)
            cues.append((int(tag[1]) * 60 + float(tag[2]), length))
            previous_end = tag.end()
        parts.append(body[previous_end:])
        text = "".join(parts)
        leading = len(text) - len(text.lstrip())
        text = text.strip()
        for timestamp in times:
            start = max(0.0, timestamp + offset)
            lines.append((start, text))
            if cues:
                shift = timestamp - times[0] + offset
                word_cues[start] = sorted((max(0.0, time + shift), min(len(text), max(0, index - leading)))
                                          for time, index in cues)
    lines.sort(key=lambda line: line[0])
    return lines, word_cues


def parse_lrc(lrc_text):
    return parse_lyrics(lrc_text)[0]


def parse_lyrics_record(record):
    """Prefer Lyricsfile word timing to the line-only LRC representation."""
    fallback = parse_lyrics(record.get("syncedLyrics"))
    if yaml is None or not record.get("hasWordSync") or not record.get("lyricsfile"):
        return fallback
    try:
        document = yaml.load(record["lyricsfile"], Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
        if not isinstance(document, dict):
            return fallback
        lines, timings = [], {}
        for line in document.get("lines", []):
            start = float(line["start_ms"]) / 1000
            end = float(line.get("end_ms") or line["start_ms"]) / 1000
            text = unicodedata.normalize("NFC", str(line.get("text") or "")).strip()
            if not math.isfinite(start) or not math.isfinite(end):
                continue
            lines.append((start, text))
            anchors = []
            cursor = 0
            for word in line.get("words") or []:
                content = unicodedata.normalize("NFC", str(word.get("text") or "")).strip()
                position = text.find(content, cursor) if content else -1
                if position < 0:
                    anchors = []
                    break
                stamp = float(word["start_ms"]) / 1000
                if not math.isfinite(stamp):
                    anchors = []
                    break
                anchors.append((stamp, position))
                cursor = position + len(content)
                if word.get("end_ms") is not None:
                    word_end = float(word["end_ms"]) / 1000
                    if math.isfinite(word_end) and word_end > stamp:
                        anchors.append((word_end, cursor))
            if anchors:
                if end > anchors[-1][0]:
                    anchors.append((end, len(text)))
                timings[start] = sorted(anchors)
        lines.sort(key=lambda entry: entry[0])
        return (lines, timings) if lines and timings else fallback
    except (yaml.YAMLError, KeyError, TypeError, ValueError, AttributeError):
        return fallback

# === CAVA AUDIO CAPTURE THREAD ===
NUM_BARS = 128
cava_raw_targets = [0.0] * NUM_BARS
cava_active = True
cava_proc = None

def cava_worker():
    global cava_raw_targets, cava_active, cava_proc
    config_dir = tempfile.TemporaryDirectory(prefix="serena-music-")
    conf_path = os.path.join(config_dir.name, "cava.conf")
    conf_content = f"""[general]
bars = {NUM_BARS}
framerate = {RENDER_FPS}
autosens = 1
lower_cutoff_freq = 50
higher_cutoff_freq = 12000

[input]
method = pipewire
source = auto

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 100
channels = mono

[smoothing]
monstercat = 0
waves = 0
noise_reduction = 64
"""
    try:
        with open(conf_path, "w", encoding="utf-8") as f:
            f.write(conf_content)
    except Exception:
        pass

    while cava_active:
        try:
            cava_proc = subprocess.Popen(
                ["cava", "-p", conf_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            while cava_active and cava_proc.poll() is None:
                line = cava_proc.stdout.readline()
                if not line:
                    break
                parts = [float(p) for p in line.strip().split(';') if p.isdigit()]
                if len(parts) >= NUM_BARS:
                    cava_raw_targets = parts[:NUM_BARS]
        except Exception:
            time.sleep(1)
        finally:
            if cava_proc:
                try:
                    cava_proc.terminate()
                    cava_proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    cava_proc.kill()
                    cava_proc.wait()
                except OSError:
                    pass
                if cava_proc.stdout:
                    cava_proc.stdout.close()
            cava_raw_targets = [0.0] * NUM_BARS
        if cava_active:
            time.sleep(0.5)
    config_dir.cleanup()


# === HYPRLAND VISIBILITY WATCHER ===
class HyprlandVisibilityWatcher:
    """Monitors active workspaces via Hyprland IPC to pause visualizer rendering when off-screen."""

    def __init__(self):
        self.sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        uid = os.getuid()
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{uid}")
        if self.sig:
            self.cmd_socket_path = os.path.join(runtime_dir, "hypr", self.sig, ".socket.sock")
            self.event_socket_path = os.path.join(runtime_dir, "hypr", self.sig, ".socket2.sock")
        else:
            self.cmd_socket_path = None
            self.event_socket_path = None
        self.event_sock = None
        self.window_address = None
        self.window_workspace_id = None
        self.active_workspaces = set()
        self.last_full_check = 0.0
        self.is_visible = True
        self._init_connection()

    def _init_connection(self):
        if not self.event_socket_path or not os.path.exists(self.event_socket_path):
            return
        try:
            self.event_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.event_sock.connect(self.event_socket_path)
            self.event_sock.setblocking(False)
            self.refresh_full()
        except Exception:
            self.event_sock = None
            self.is_visible = True

    def query_hyprland(self, cmd: str):
        if not self.cmd_socket_path or not os.path.exists(self.cmd_socket_path):
            return None
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                s.connect(self.cmd_socket_path)
                s.sendall(cmd.encode("utf-8"))
                data = b""
                while True:
                    chunk = s.recv(8192)
                    if not chunk:
                        break
                    data += chunk
                return json.loads(data.decode("utf-8", errors="ignore"))
        except Exception:
            return None

    def refresh_full(self):
        self.last_full_check = time.monotonic()
        if not self.cmd_socket_path:
            self.is_visible = True
            return

        monitors = self.query_hyprland("j/monitors")
        if monitors and isinstance(monitors, list):
            self.active_workspaces = {
                m.get("activeWorkspace", {}).get("id")
                for m in monitors
                if "activeWorkspace" in m and "id" in m["activeWorkspace"]
            }
            for m in monitors:
                sp = m.get("specialWorkspace", {}).get("id")
                if sp:
                    self.active_workspaces.add(sp)

        clients = self.query_hyprland("j/clients")
        if clients and isinstance(clients, list):
            my_pid = os.getpid()
            pids = {my_pid}
            p = my_pid
            while p > 1:
                try:
                    with open(f"/proc/{p}/stat", "r") as f:
                        ppid = int(f.read().split()[3])
                        p = ppid
                        pids.add(p)
                except Exception:
                    break

            for c in clients:
                cls = c.get("class", "")
                title = c.get("title", "")
                in_title = c.get("initialTitle", "")
                if c.get("pid") in pids or cls == "music-vis" or in_title == "Serena Music" or "Serena Music" in title:
                    self.window_address = c.get("address")
                    self.window_workspace_id = c.get("workspace", {}).get("id")
                    if c.get("pinned", False):
                        self.is_visible = True
                        return
                    break

        if self.window_workspace_id is not None and self.active_workspaces:
            self.is_visible = (self.window_workspace_id in self.active_workspaces)
        else:
            self.is_visible = True

    def handle_events(self):
        if not self.event_sock:
            return
        needs_refresh = False
        try:
            while True:
                data = self.event_sock.recv(4096)
                if not data:
                    break
                text = data.decode("utf-8", errors="ignore")
                for line in text.split("\n"):
                    if not line:
                        continue
                    if ">>" in line:
                        event, _ = line.split(">>", 1)
                        if event in ("workspace", "workspacev2", "focusedmon", "movewindow", "movewindowv2", "fullscreen"):
                            needs_refresh = True
        except (BlockingIOError, InterruptedError):
            pass
        except Exception:
            try:
                self.event_sock.close()
            except Exception:
                pass
            self.event_sock = None

        if needs_refresh or (time.monotonic() - self.last_full_check > 5.0):
            self.refresh_full()

    def get_socket_fd(self):
        return self.event_sock

    def close(self):
        if self.event_sock:
            try:
                self.event_sock.close()
            except Exception:
                pass
            self.event_sock = None

    def __del__(self):
        self.close()


# === LYRICS APPLICATION ===
class LyricsApp:
    def __init__(self, local_player=None):
        self.local_player = local_player
        self.mode_requested = None
        self.running = True
        self.sync_offset = 0.0  # seconds

        # Spectrum heights are stored independently of terminal row count.
        self.num_bars = NUM_BARS
        self.bars = [0.0] * self.num_bars
        self.last_frame_time = time.monotonic()
        self.mpris_thread = None

        # MPRIS State
        self.status = "Stopped"
        self.title = ""
        self.artist = ""
        self.album = ""
        self.media_url = ""
        self.sync_track_key = ""
        self.position = 0.0
        self.length = 0.0
        self.last_sync_time = time.monotonic()
        self.clock_track_key = None
        self.last_position_report = 0.0
        self.position_report_changed_at = self.last_sync_time
        self.position_is_estimated = False
        self.clock_correction = 0.0
        self.pending_rewind = None
        self.last_lyrics_lookup_key = None

        # Lyrics State
        self.current_track_key = ""
        self.synced_lyrics = []
        self.word_cues = {}
        self.lyrics_request = None
        self.lyrics_duration = 0.0
        self.plain_lyrics = []
        self.is_synced = False
        self.loading_lyrics = False
        self.lyrics_found = False
        self.scaled_lyrics = bool(os.environ.get("KITTY_WINDOW_ID") or os.environ.get("TERM") == "xterm-kitty") and not os.environ.get("TMUX")
        self.lyrics_canvas = LyricsCanvas(PALETTE) if self.scaled_lyrics and LyricsCanvas is not None else None
        self.spectrum_canvas = SpectrumCanvas(GRADIENT_STOPS) if self.scaled_lyrics and SpectrumCanvas is not None else None
        self.focus_mode = MusicFocus(enabled=bool(os.environ.get('WAYLAND_DISPLAY'))
                                    and self.scaled_lyrics and LyricsCanvas is not None and SpectrumCanvas is not None)
        self.focus_frame_size = None
        self.graphics_frame_size = None
        self.idle_backdrop = IdleBackdrop(DARK_WINE, enabled=self.scaled_lyrics, native=True, normal_opacity=0.94)
        self.terminal_input = TerminalInput()
        self.visibility_watcher = HyprlandVisibilityWatcher()

        # Start CAVA thread
        self.cava_thread = threading.Thread(target=cava_worker, daemon=True)
        self.cava_thread.start()

    def update_mpris(self):
        try:
            if self.local_player is not None:
                with self.local_player.lock:
                    player = self.local_player
                    track = player.track
                    parts = [player.status, str(round(player.position * 1_000_000)),
                             str(round(player.duration * 1_000_000)),
                             track.title if track else '', track.artist if track else '',
                             track.album if track else '', track.path.as_uri() if track else '']
            else:
                cmd = ['playerctl', 'metadata', '--format',
                       '{{status}}\t{{position}}\t{{mpris:length}}\t{{title}}\t{{artist}}\t{{album}}\t{{xesam:url}}']
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=1).rstrip('\r\n')
                parts = out.split('\t')
            if len(parts) < 4:
                return
            raw_pos = float(parts[1]) if parts[1].replace('.', '', 1).isdigit() else 0.0
            raw_len = float(parts[2]) if parts[2].replace('.', '', 1).isdigit() else 0.0
            title = parts[3].strip()
            artist = parts[4].strip() if len(parts) > 4 else ""
            album = parts[5] if len(parts) > 5 else ""
            url = parts[6].strip() if len(parts) > 6 else ""
            same_title = match_key(clean_track_name(title)) == match_key(clean_track_name(self.title))
            same_artist = not artist or not self.artist or bool(artist_forms(artist) & artist_forms(self.artist))
            same_metadata = same_title and same_artist
            # An omitted URL/artist is common during a browser metadata refresh.
            # Keep the current media identity until a different track is known.
            if not title:
                title, artist, album, url = self.title, self.artist, self.album, self.media_url
            elif same_metadata:
                url = url or self.media_url
                artist = artist or self.artist
                album = album or self.album
            lookup_key = (match_key(clean_track_name(title)), tuple(sorted(artist_forms(artist))))
            track_key = ("url:" + video_identity(url)) if url else ("metadata:" + repr(lookup_key))
            if url and not self.media_url and same_metadata and self.current_track_key:
                # Attach a late URL to this track without restarting its clock.
                self.clock_track_key = track_key
                self.current_track_key = track_key
                self.sync_track_key = sync_key(title, artist, url)
                if self.sync_offset:
                    save_sync_offset(self.sync_track_key, self.sync_offset)
                else:
                    self.sync_offset = load_sync_offset(self.sync_track_key)
            self.title, self.artist, self.album, self.media_url = title, artist, album, url
            if raw_len > 0 or track_key != self.current_track_key:
                self.length = raw_len / 1_000_000.0
            self.sync_playback(parts[0], raw_pos / 1_000_000.0, track_key)
            if self.local_player is not None:
                # The owned engine reports its actual clock, including deliberate
                # seeks; it does not need the external-player rewind heuristic.
                self.position = raw_pos / 1_000_000.0
                self.last_sync_time = time.monotonic()
                self.clock_correction = 0.0
                self.position_is_estimated = False
                self.pending_rewind = None
        except Exception:
            self.status = "No Player"
            return
        track_changed = track_key != self.current_track_key
        if track_changed and self.title:
            self.current_track_key = track_key
            self.sync_track_key = sync_key(self.title, self.artist, self.media_url)
            self.sync_offset = load_sync_offset(self.sync_track_key)
        if self.title and (track_changed or lookup_key != self.last_lyrics_lookup_key):
            self.last_lyrics_lookup_key = lookup_key
            self.load_lyrics_async(self.title, self.artist, self.length, self.media_url)

    def confirm_rewind(self, status, reported_position, now):
        """Require a progressing new timeline before accepting a backward jump."""
        pending = self.pending_rewind
        if pending is None:
            self.pending_rewind = (reported_position, now, reported_position, 0)
            return False
        anchor, started, previous, evidence = pending
        elapsed = max(0.0, now - started) if status == "Playing" else 0.0
        consistent = abs(reported_position - anchor - elapsed) <= 0.8
        if not consistent or reported_position < previous - 0.05:
            self.pending_rewind = (reported_position, now, reported_position, 0)
            return False
        if reported_position > previous + 0.05 or status != "Playing":
            evidence += 1
        self.pending_rewind = (anchor, started, reported_position, evidence)
        return evidence >= 2

    def sync_playback(self, status, reported_position, track_key):
        """Keep an elapsed clock when a player reports a missing/frozen position."""
        now = time.monotonic()
        reported_position = max(0.0, reported_position)
        usable = reported_position >= 0.01
        if track_key != self.clock_track_key:
            self.position = reported_position
            self.clock_correction = 0.0
            self.position_report_changed_at = now
            self.position_is_estimated = not usable
            self.clock_track_key = track_key
            self.pending_rewind = None
        else:
            predicted = self.elapsed_position(now)
            changed = abs(reported_position - self.last_position_report) > 0.05
            backward = usable and reported_position < predicted - 0.75
            accepted = usable and changed
            if backward:
                accepted = self.confirm_rewind(status, reported_position, now)
            else:
                self.pending_rewind = None
            if accepted:
                error = reported_position - predicted
                if self.status == status == "Playing" and not self.position_is_estimated and abs(error) < 0.75:
                    # Correct small timing jitter over several frames without
                    # stepping the highlight backwards on each metadata poll.
                    self.position = predicted
                    self.clock_correction = max(-0.15, min(0.15, error))
                else:
                    self.position = reported_position
                    self.clock_correction = 0.0
                self.position_report_changed_at = now
                self.position_is_estimated = False
                self.pending_rewind = None
            else:
                self.position = predicted
                self.clock_correction = 0.0
                self.position_is_estimated = self.position_is_estimated or now - self.position_report_changed_at > 1.5
        self.status = status
        self.last_sync_time = now
        self.last_position_report = reported_position

    def load_lyrics_async(self, title, artist, length, media_url=None):
        request = object()
        url = self.media_url if media_url is None else media_url
        self.lyrics_request = request
        self.loading_lyrics = True
        self.synced_lyrics = []
        self.word_cues = {}
        self.plain_lyrics = []
        self.lyrics_duration = 0.0
        self.is_synced = False
        self.lyrics_found = False

        def worker():
            try:
                data = load_local_lyrics(url) or fetch_lrclib(title, artist, length)
                lines, cues = parse_lyrics_record(data) if data else ([], {})
                plain = [line.strip() for line in (data.get("plainLyrics") or "").splitlines()
                         if line.strip()] if data else []
                duration = float(data.get("duration") or 0.0) if data else 0.0
            except Exception:
                lines, cues, plain = [], {}, []
                duration = 0.0
            if self.lyrics_request is not request:
                return
            self.synced_lyrics = lines
            self.word_cues = cues
            self.plain_lyrics = plain
            self.lyrics_duration = duration
            self.is_synced = bool(lines)
            self.lyrics_found = bool(lines or plain)
            self.loading_lyrics = False

        threading.Thread(target=worker, daemon=True).start()

    def elapsed_position(self, now):
        pos = self.position
        if self.status == "Playing":
            elapsed = max(0.0, now - self.last_sync_time)
            pos += elapsed + self.clock_correction * (1 - math.exp(-elapsed / 0.30))
        return pos

    def get_interpolated_pos(self):
        pos = self.elapsed_position(time.monotonic())
        return max(0.0, pos + self.sync_offset)

    def format_time(self, seconds):
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins:02d}:{secs:02d}"

    def render(self):
        cols, rows = shutil.get_terminal_size((80, 24))
        cur_pos = self.get_interpolated_pos()
        previous, current, upcoming = "", "", ""
        visibility = 1.0
        lyric_lines = []
        index = 0
        synced = self.synced_lyrics
        plain = self.plain_lyrics
        if self.is_synced and synced:
            lyric_lines = synced
            index = 0
            for candidate, (timestamp, _) in enumerate(synced):
                if timestamp > cur_pos:
                    break
                index = candidate
            start, current = synced[index]
            previous = synced[index - 1][1] if index > 0 else ""
            upcoming = synced[index + 1][1] if index + 1 < len(synced) else ""
            transition_end = synced[index + 1][0] if index + 1 < len(synced) else math.inf
            visibility = line_visibility(cur_pos, start, transition_end)
        elif self.lyrics_found and plain:
            duration = self.length or self.lyrics_duration
            lyric_lines = [(duration * line / len(plain), text) for line, text in enumerate(plain)]
            index = min(len(plain) - 1, int(cur_pos / max(1.0, duration) * len(plain)))
            previous = plain[index - 1] if index > 0 else ""
            current = plain[index]
            upcoming = plain[index + 1] if index + 1 < len(plain) else ""
            if duration > 0:
                start = duration * index / len(plain)
                end = duration * (index + 1) / len(plain)
                visibility = line_visibility(cur_pos, start, end)

        focus_active = self.focus_mode.active
        self.idle_backdrop.forced = focus_active
        if focus_active:
            _, _, spectrum_top = visualizer_regions(rows)
            self.render_spectrum(cols, max(0, rows - spectrum_top), draw=False)
            self.focus_mode.update(lyric_lines, index, self.current_track_key,
                                   self.bars, SPECTRUM_GAIN, GRADIENT_STOPS)
            if self.focus_mode.ready:
                self.graphics_frame_size = None
                # The overlay draws the foreground above all desktop surfaces.
                # Clear Kitty's copy so it cannot show through the dim layer.
                frame = [self.idle_backdrop.update()]
                if self.focus_frame_size != (cols, rows):
                    frame.extend(f'\x1b[{row + 1};1H\x1b[K' for row in range(rows))
                    if self.lyrics_canvas is not None:
                        frame.append(self.lyrics_canvas.clear())
                    if self.spectrum_canvas is not None:
                        frame.append(self.spectrum_canvas.clear())
                    self.focus_frame_size = (cols, rows)
                command = ''.join(frame)
                if command:
                    sys.stdout.write('\x1b[?2026h' + command + '\x1b[?2026l')
                    sys.stdout.flush()
                return

        self.focus_frame_size = None
        # Clear before drawing: erasing a lower row of Kitty's enlarged text
        # would erase the whole glyph. All lyric and spectrum regions stay apart.
        frame = ["\x1b[?2026h", self.idle_backdrop.update()]
        # Use one scale for the waveform even while lyrics load or are missing.
        lyric_top, lyric_rows, spectrum_start = visualizer_regions(rows)
        use_canvas = self.lyrics_canvas is not None and rows >= 12 and cols >= 24 and bool(lyric_lines)
        graphics_only = self.spectrum_canvas is not None and (use_canvas or not any((previous, current, upcoming)))
        # Image placements replace themselves. Erasing every terminal row at
        # 60 FPS only adds terminal work while both regions use graphics.
        if not graphics_only or self.graphics_frame_size != (cols, rows):
            frame.extend(f"\x1b[{row + 1};1H\x1b[K" for row in range(rows))
        self.graphics_frame_size = (cols, rows) if graphics_only else None
        if use_canvas:
            spectrum_start, image_frame = self.lyrics_canvas.render(lyric_lines, index, cols, rows, self.current_track_key)
            frame.append(image_frame)
        elif rows >= 2 and any((previous, current, upcoming)):
            if self.lyrics_canvas is not None:
                frame.append(self.lyrics_canvas.clear())
            scale = 2 if self.scaled_lyrics and cols >= 24 and rows >= 12 else 1
            width = max(1, (cols - 4) // scale) if cols >= 8 else cols
            spans = lyric_spans(current, width)
            max_lines = 2 if rows >= 16 else 1
            block_height = max_lines * scale
            if len(spans) * scale > block_height and scale > 1:
                scale = 1
                width = max(1, cols - 4)
                spans = lyric_spans(current, width)
            block_height = min(lyric_rows, max(block_height, len(spans) * scale))
            visible = spans[:max(1, block_height // scale)]
            top = lyric_top + (lyric_rows - block_height) // 2
            text_top = top + (block_height - len(visible) * scale) // 2

            for offset, (start, end) in enumerate(visible):
                text = current[start:end]
                # OSC payloads contain plain text only.
                text = "".join(char for char in text if unicodedata.category(char) not in ("Cc", "Cs"))
                text = ANSI_STYLE.sub("", clip_line(text, width))
                padding = max(0, (cols - text_width(text) * scale) // 2)
                row = text_top + offset * scale
                frame.append(f"\x1b[{row + 1};1H" + " " * padding + lyric_text(text, scale, visibility))

            if rows >= 10:
                for text, row in ((previous, top - 2), (upcoming, top + block_height + 1)):
                    if text and 0 <= row < spectrum_start:
                        text = ANSI_STYLE.sub("", clip_line(text, max(1, cols - 4)))
                        padding = max(0, (cols - text_width(text)) // 2)
                        frame.append(f"\x1b[{row + 1};1H" + " " * padding + fg(SOFT_PINK) + bg(DARK_WINE) + text + RESET)
        elif self.lyrics_canvas is not None:
            frame.append(self.lyrics_canvas.clear())

        spectrum = self.render_spectrum(cols, max(0, rows - spectrum_start), draw=self.spectrum_canvas is None)
        if self.spectrum_canvas is not None:
            frame.append(self.spectrum_canvas.render(self.bars, cols, rows, spectrum_start, gain=SPECTRUM_GAIN))
        else:
            for offset, line in enumerate(spectrum):
                frame.append(f"\x1b[{spectrum_start + offset + 1};1H{clip_line(line, cols)}")
        frame.append("\x1b[?2026l")
        sys.stdout.write("".join(frame))
        sys.stdout.flush()

    def render_spectrum(self, cols, height, draw=True):
        if cols <= 0 or height <= 0:
            return []

        # Keep every bar two cells wide. Center the one or two spare cells
        # at the edges instead of widening individual bars after a resize.
        count = max(1, (cols + 1) // 3)
        bar_width = min(2, cols)
        gap = 1 if count > 1 else 0
        spare = cols - (count * bar_width + gap * (count - 1))
        left_padding = " " * (spare // 2)
        right_padding = " " * (spare - spare // 2)
        targets = mirrored_bars(cava_raw_targets, count)
        if len(self.bars) != count:
            self.bars = resample_bars(self.bars, count)
        self.num_bars = count

        now = time.monotonic()
        elapsed = min(0.1, max(0.0, now - self.last_frame_time))
        self.last_frame_time = now
        for index, target in enumerate(targets):
            # Light frequency smoothing softens isolated spikes without making
            # adjacent bars identical. Time-based envelopes survive slower frames.
            left = targets[max(0, index - 1)]
            right = targets[min(count - 1, index + 1)]
            target = 0.2 * left + 0.6 * target + 0.2 * right
            tau = 0.055 if target > self.bars[index] else 0.20
            self.bars[index] += (target - self.bars[index]) * (1 - math.exp(-elapsed / tau))

        if not draw:
            return []
        levels = [min(height * 8, max(0, round(value / 100 * SPECTRUM_GAIN * height * 8)))
                  for value in self.bars]
        blocks = " ▁▂▃▄▅▆▇█"
        lines = []
        for row in reversed(range(height)):
            # Fit the complete token gradient to each bar, including short bars.
            cells = []
            previous_color = None
            for level in levels:
                block = blocks[min(8, max(0, level - row * 8))]
                if block != ' ':
                    top = (level - 1) // 8
                    fraction = (top - row) / top if top else 0.5
                    color = gradient_color(fraction)
                    if color != previous_color:
                        cells.append(fg(color))
                        previous_color = color
                cells.append(block * bar_width)
                cells.append(' ' * gap)
            if gap:
                cells.pop()
            lines.append(left_padding + ''.join(cells) + RESET + right_padding)
        return lines

    def handle_key(self, key):
        if key in ('\t', 'v', 'V') and self.local_player is not None:
            self.mode_requested = 'library'
            self.running = False
        elif key in ('q', 'Q', '\x03'):  # 'q' or Ctrl+C
            self.running = False
            if self.local_player is not None:
                self.local_player.exit_requested = True
        elif key in ('d', 'D'):
            self.focus_mode.toggle()
            self.idle_backdrop.forced = self.focus_mode.active
            self.idle_backdrop.interact()
        elif key == ' ':
            if self.local_player is not None:
                self.local_player.toggle()
            else:
                subprocess.run(['playerctl', 'play-pause'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif key in ('n', 'N'):
            if self.local_player is not None:
                self.local_player.next()
            else:
                subprocess.run(['playerctl', 'next'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif key in ('p', 'P'):
            if self.local_player is not None:
                self.local_player.previous()
            else:
                subprocess.run(['playerctl', 'previous'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif key in ('h', 'l') and self.local_player is not None:
            self.local_player.seek(-5 if key == 'h' else 5)
        elif key == '\x1b[D' or key == '-':  # Delay lyrics by 0.5s.
            self.sync_offset -= 0.5
            save_sync_offset(self.sync_track_key, self.sync_offset)
        elif key == '\x1b[C' or key == '+' or key == '=':  # Advance lyrics by 0.5s.
            self.sync_offset += 0.5
            save_sync_offset(self.sync_track_key, self.sync_offset)
        elif key == '0':  # Reset offset
            self.sync_offset = 0.0
            save_sync_offset(self.sync_track_key, self.sync_offset)

    def run(self):
        global cava_active, cava_proc
        try:
            init_terminal()
            sys.stdout.write(self.idle_backdrop.start())
            sys.stdout.flush()
            last_mpris_poll = 0
            next_frame = 0
            was_hidden = False
            while self.running and not (self.local_player is not None and self.local_player.exit_requested):
                now = time.monotonic()
                is_playing = (self.status == "Playing")
                is_visible = self.visibility_watcher.is_visible

                # Throttle MPRIS updates when hidden or paused
                mpris_interval = 0.4 if (is_playing and is_visible) else 1.5
                if now - last_mpris_poll > mpris_interval and (self.mpris_thread is None or not self.mpris_thread.is_alive()):
                    self.mpris_thread = threading.Thread(target=self.update_mpris, daemon=True)
                    self.mpris_thread.start()
                    last_mpris_poll = now

                if is_visible:
                    if was_hidden:
                        # Synchronize immediately upon becoming visible again
                        was_hidden = False
                        next_frame = 0
                        self.last_frame_time = time.monotonic()
                        if self.mpris_thread is None or not self.mpris_thread.is_alive():
                            self.mpris_thread = threading.Thread(target=self.update_mpris, daemon=True)
                            self.mpris_thread.start()

                    if now >= next_frame:
                        self.render()
                        fps = RENDER_FPS if is_playing else 10
                        interval = 1 / fps
                        next_frame = (next_frame or now) + interval
                        finished = time.monotonic()
                        if next_frame <= finished:
                            next_frame += (math.floor((finished - next_frame) / interval) + 1) * interval
                    frame_wait = max(0.0, next_frame - time.monotonic())
                else:
                    was_hidden = True
                    # Pause rendering completely when off-screen; sleep in select until woken by socket2 or input
                    frame_wait = 0.25

                inputs = [sys.stdin]
                focus_connection = self.focus_mode.connection
                if focus_connection is not None:
                    inputs.append(focus_connection)
                hypr_sock = self.visibility_watcher.get_socket_fd()
                if hypr_sock is not None:
                    inputs.append(hypr_sock)

                readable = select.select(inputs, [], [], frame_wait)[0]
                if hypr_sock is not None and hypr_sock in readable:
                    self.visibility_watcher.handle_events()
                if sys.stdin in readable:
                    data = os.read(sys.stdin.fileno(), 4096)
                    if not data:
                        break
                    keys, activity = self.terminal_input.feed(data.decode("utf-8", errors="ignore"))
                    if activity:
                        self.idle_backdrop.interact()
                    for key in keys:
                        self.handle_key(key)
                        next_frame = 0
                        if not self.running:
                            break
                if focus_connection is not None and focus_connection in readable:
                    for key in self.focus_mode.read_keys():
                        self.idle_backdrop.interact()
                        self.handle_key(key)
                        next_frame = 0
                        if not self.running:
                            break
        finally:
            self.visibility_watcher.close()
            self.focus_mode.close()
            cava_active = False
            if cava_proc:
                try:
                    cava_proc.terminate()
                except OSError:
                    pass
            self.cava_thread.join(timeout=2)
            if self.mpris_thread is not None:
                self.mpris_thread.join(timeout=1.2)
            if self.lyrics_canvas is not None:
                sys.stdout.write(self.lyrics_canvas.clear())
            if self.spectrum_canvas is not None:
                sys.stdout.write(self.spectrum_canvas.clear())
            sys.stdout.write(self.idle_backdrop.close())
            cleanup_terminal()


def run_visualizer(player):
    global cava_active, cava_proc, cava_raw_targets
    cava_active = True
    cava_proc = None
    cava_raw_targets = [0.0] * NUM_BARS
    app = LyricsApp(local_player=player)
    app.run()
    return app.mode_requested


if __name__ == "__main__":
    if (not sys.stdin.isatty() or not sys.stdout.isatty()) and not any(
            flag in sys.argv for flag in ('--headless', '--help', '-h')):
        sys.exit("Music requires an interactive terminal.")
    signal.signal(signal.SIGINT, signal_handler)
    from music_player import main
    sys.exit(main(visualizer=run_visualizer) or 0)
