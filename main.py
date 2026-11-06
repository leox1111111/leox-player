"""Leox Player - odtwarzacz muzyki i YouTube na Androida (Kivy, Pydroid 3)."""
import bisect
import colorsys
import math
import datetime
import hashlib
import json
import os
import re
import socket
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter
from xml.sax.saxutils import escape as xml_escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.request
import random
import sqlite3
import threading
import time
from pathlib import Path

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import (Color, Ellipse, InstructionGroup, Line, PopMatrix, PushMatrix,
                           Rectangle, Rotate, RoundedRectangle)
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             StringProperty)
from kivy.utils import escape_markup
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget

try:
    import mutagen
except ImportError:
    mutagen = None

try:                                    # certyfikaty SSL w APK
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    import ssl as _ssl
    _CAFILE = certifi.where()
    _ssl._create_default_https_context = lambda *a, **k: _ssl.create_default_context(cafile=_CAFILE)
except ImportError:
    pass

_SD = Path("/storage/emulated/0/Music")
MUSIC_DIR = _SD if _SD.exists() else Path.home() / "Music"
YT_ID_RE = re.compile(r"\[([A-Za-z0-9_-]{11})\]")
VIDEO_FORMAT = ("best[ext=mp4][vcodec!=none][acodec!=none][height<=720]"
                "/best[vcodec!=none][acodec!=none]/18")
EXT = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wav", ".aac", ".webm"}

# ciepła, ciemna paleta
BG = (0.10, 0.08, 0.07, 1)
BG_POP = (0.14, 0.11, 0.09, 1)
CARD = (0.20, 0.15, 0.12, 1)
CARD_HI = (0.27, 0.20, 0.15, 1)
ACCENT = (0.86, 0.56, 0.32, 1)
ACCENT_DIM = (0.42, 0.26, 0.15, 1)
TEXT = (1.0, 1.0, 1.0, 1)          # biały tekst
MUTED = (0.80, 0.74, 0.68, 1)
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/varelaround/VarelaRound-Regular.ttf"
UA = {"User-Agent": "LeoxPlayer/1.0"}

THEME_KEYS = ("BG", "BG_POP", "CARD", "CARD_HI", "ACCENT", "ACCENT_DIM", "TEXT", "MUTED")
THEMES = {
    "Ciepły": dict(BG=(0.1, 0.08, 0.07, 1), BG_POP=(0.14, 0.11, 0.09, 1), CARD=(0.2, 0.15, 0.12, 1), CARD_HI=(0.27, 0.2, 0.15, 1), ACCENT=(0.86, 0.56, 0.32, 1), ACCENT_DIM=(0.42, 0.26, 0.15, 1), MUTED=(0.8, 0.74, 0.68, 1)),
    "Leśny": dict(BG=(0.06, 0.09, 0.07, 1), BG_POP=(0.09, 0.13, 0.1, 1), CARD=(0.12, 0.18, 0.14, 1), CARD_HI=(0.17, 0.25, 0.19, 1), ACCENT=(0.55, 0.8, 0.45, 1), ACCENT_DIM=(0.22, 0.38, 0.24, 1), MUTED=(0.72, 0.8, 0.72, 1)),
    "Nocny granat": dict(BG=(0.05, 0.07, 0.12, 1), BG_POP=(0.08, 0.1, 0.17, 1), CARD=(0.11, 0.14, 0.24, 1), CARD_HI=(0.16, 0.2, 0.32, 1), ACCENT=(0.45, 0.65, 1.0, 1), ACCENT_DIM=(0.18, 0.26, 0.48, 1), MUTED=(0.7, 0.75, 0.86, 1)),
    "Śliwka": dict(BG=(0.09, 0.06, 0.1, 1), BG_POP=(0.13, 0.09, 0.15, 1), CARD=(0.19, 0.12, 0.21, 1), CARD_HI=(0.26, 0.17, 0.29, 1), ACCENT=(0.9, 0.5, 0.75, 1), ACCENT_DIM=(0.42, 0.2, 0.36, 1), MUTED=(0.8, 0.7, 0.8, 1)),
    "Morski": dict(BG=(0.04, 0.09, 0.1, 1), BG_POP=(0.06, 0.13, 0.14, 1), CARD=(0.09, 0.19, 0.2, 1), CARD_HI=(0.13, 0.26, 0.28, 1), ACCENT=(0.3, 0.82, 0.78, 1), ACCENT_DIM=(0.12, 0.38, 0.38, 1), MUTED=(0.68, 0.82, 0.8, 1)),
    "Grafit": dict(BG=(0.08, 0.08, 0.09, 1), BG_POP=(0.12, 0.12, 0.13, 1), CARD=(0.17, 0.17, 0.19, 1), CARD_HI=(0.24, 0.24, 0.26, 1), ACCENT=(0.95, 0.75, 0.3, 1), ACCENT_DIM=(0.35, 0.3, 0.18, 1), MUTED=(0.75, 0.75, 0.78, 1)),
    "Wiśnia": dict(BG=(0.1, 0.04, 0.05, 1), BG_POP=(0.15, 0.06, 0.08, 1), CARD=(0.22, 0.09, 0.11, 1), CARD_HI=(0.3, 0.12, 0.15, 1), ACCENT=(0.95, 0.35, 0.4, 1), ACCENT_DIM=(0.45, 0.14, 0.18, 1), MUTED=(0.85, 0.7, 0.72, 1)),
    "Zachód słońca": dict(BG=(0.11, 0.06, 0.07, 1), BG_POP=(0.16, 0.09, 0.09, 1), CARD=(0.24, 0.12, 0.12, 1), CARD_HI=(0.32, 0.17, 0.15, 1), ACCENT=(1.0, 0.55, 0.35, 1), ACCENT_DIM=(0.5, 0.22, 0.2, 1), MUTED=(0.88, 0.74, 0.7, 1)),
    "Lawenda": dict(BG=(0.08, 0.07, 0.12, 1), BG_POP=(0.11, 0.1, 0.17, 1), CARD=(0.17, 0.15, 0.25, 1), CARD_HI=(0.23, 0.2, 0.33, 1), ACCENT=(0.72, 0.62, 1.0, 1), ACCENT_DIM=(0.32, 0.26, 0.5, 1), MUTED=(0.78, 0.75, 0.88, 1)),
    "Miodowy": dict(BG=(0.1, 0.08, 0.04, 1), BG_POP=(0.14, 0.11, 0.05, 1), CARD=(0.21, 0.16, 0.07, 1), CARD_HI=(0.29, 0.22, 0.1, 1), ACCENT=(1.0, 0.78, 0.25, 1), ACCENT_DIM=(0.45, 0.33, 0.1, 1), MUTED=(0.86, 0.8, 0.66, 1)),
    "Mięta": dict(BG=(0.05, 0.09, 0.08, 1), BG_POP=(0.07, 0.13, 0.11, 1), CARD=(0.1, 0.19, 0.16, 1), CARD_HI=(0.14, 0.26, 0.22, 1), ACCENT=(0.45, 0.95, 0.72, 1), ACCENT_DIM=(0.16, 0.4, 0.3, 1), MUTED=(0.72, 0.86, 0.8, 1)),
    "Kosmos": dict(BG=(0.03, 0.03, 0.08, 1), BG_POP=(0.06, 0.06, 0.13, 1), CARD=(0.1, 0.09, 0.2, 1), CARD_HI=(0.15, 0.13, 0.28, 1), ACCENT=(0.35, 0.9, 1.0, 1), ACCENT_DIM=(0.15, 0.3, 0.45, 1), MUTED=(0.7, 0.74, 0.9, 1)),
    "Czekolada": dict(BG=(0.08, 0.05, 0.04, 1), BG_POP=(0.12, 0.08, 0.06, 1), CARD=(0.18, 0.12, 0.09, 1), CARD_HI=(0.25, 0.17, 0.13, 1), ACCENT=(0.9, 0.72, 0.55, 1), ACCENT_DIM=(0.4, 0.27, 0.19, 1), MUTED=(0.82, 0.74, 0.68, 1)),
    "Północ (OLED)": dict(BG=(0.0, 0.0, 0.0, 1), BG_POP=(0.05, 0.05, 0.05, 1), CARD=(0.09, 0.09, 0.09, 1), CARD_HI=(0.15, 0.15, 0.15, 1), ACCENT=(1.0, 1.0, 1.0, 1), ACCENT_DIM=(0.28, 0.28, 0.28, 1), MUTED=(0.65, 0.65, 0.65, 1)),
}
FORMATS = {
    "najlepsza": "bestaudio[ext=m4a]/bestaudio/best[ext=mp4]/best",
    "oszczędna": "bestaudio[ext=m4a][abr<=96]/bestaudio[abr<=96]/worstaudio[ext=m4a]/worstaudio/best",
}


ANIM = {"on": True}


def anim(target, d=0.3, t="out_cubic", **props):
    """Płynna zmiana właściwości (albo natychmiastowa, gdy animacje są wyłączone)."""
    Animation.cancel_all(target, *props.keys())
    if not ANIM["on"] or d <= 0:
        for k, v in props.items():
            setattr(target, k, v)
        return
    Animation(d=d, t=t, **props).start(target)


_WHITE = []


def white_tex():
    """Jednolita biała tekstura - bez niej kształt potrafi 'pożyczyć' cudzy napis."""
    if not _WHITE:
        t = Texture.create(size=(1, 1), colorfmt="rgba")
        t.blit_buffer(b"\xff\xff\xff\xff", colorfmt="rgba", bufferfmt="ubyte")
        _WHITE.append(t)
    return _WHITE[0]


VIDEO_JUNK = re.compile(
    r"\s*[\(\[](official|oficjalny|lyrics?|tekst|audio|hd|hq|4k|visuali[sz]er|music video|"
    r"video|teledysk)[^\)\]]*[\)\]]", re.I)


def clean_title(s):
    return VIDEO_JUNK.sub("", s or "").strip() or (s or "")


def clean_artist(s):
    return re.sub(r"(VEVO|\s-\sTopic)$", "", s or "").strip()


def split_name(stem):
    """'Kanał - Wykonawca - Tytuł (Official Video) [id]' -> (tytuł, wykonawca)."""
    s = re.sub(r"\s*\[[A-Za-z0-9_-]{11}\]$", "", stem).strip()
    parts = s.split(" - ")
    if len(parts) >= 3:
        artist, title = parts[1], " - ".join(parts[2:])
    elif len(parts) == 2:
        artist, title = parts
    else:
        artist, title = "", s
    return clean_title(title), clean_artist(artist)


AUTO_THEME = "Auto (pora dnia)"


def resolve_theme(name):
    """Auto: dzień 7-18 Morski, wieczór 18-22 Ciepły, noc Północ (OLED)."""
    if name != AUTO_THEME:
        return name
    h = datetime.datetime.now().hour
    return "Morski" if 7 <= h < 18 else ("Ciepły" if 18 <= h < 22 else "Północ (OLED)")


def apply_theme(name):
    globals().update(THEMES.get(resolve_theme(name), THEMES["Ciepły"]))


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|]+', "_", s or "").strip()[:120] or "bez_nazwy"


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_duration(s):
    """'1:02:03', '62:03' albo '3723' -> sekundy."""
    try:
        parts = [int(float(x)) for x in str(s).strip().split(":")]
    except ValueError:
        return 0
    total = 0
    for x in parts:
        total = total * 60 + x
    return total


def replaygain(path):
    """Współczynnik głośności z tagów ReplayGain (tylko ściszanie, max 1.0)."""
    if not mutagen:
        return 1.0
    try:
        tags = mutagen.File(path).tags or {}
        val = None
        for k in ("replaygain_track_gain", "REPLAYGAIN_TRACK_GAIN",
                  "TXXX:REPLAYGAIN_TRACK_GAIN", "TXXX:replaygain_track_gain",
                  "----:com.apple.iTunes:replaygain_track_gain"):
            if k in tags:
                val = tags[k]
                break
        if val is None:
            return 1.0
        if isinstance(val, list):
            val = val[0]
        if hasattr(val, "text"):
            val = val.text[0]
        if isinstance(val, bytes):
            val = val.decode("utf-8", "ignore")
        db = float(str(val).lower().replace("db", "").strip())
        return max(0.05, min(1.0, 10 ** (db / 20)))
    except Exception:
        return 1.0


LRCLIB = "https://lrclib.net/api"


def parse_lrc(text):
    """Plik LRC -> [(sekunda, linijka)] posortowane."""
    out = []
    for line in text.splitlines():
        stamps = re.findall(r"\[(\d+):(\d+(?:[.:]\d+)?)\]", line)
        words = re.sub(r"<[^>]*>", "", re.sub(r"\[[^\]]*\]", "", line)).strip()
        for m, sec in stamps:
            out.append((int(m) * 60 + float(sec.replace(":", ".")), words))
    return sorted(out)


def lyric_timeline(text, synced, duration):
    """Tekst -> [(sekunda, słowo, nr linijki)]. Słowa linijki rozkładane w czasie."""
    tl = []
    if synced:
        lines = parse_lrc(text)
        for i, (t0, line) in enumerate(lines):
            words = line.split()
            if not words:
                continue
            end = lines[i + 1][0] if i + 1 < len(lines) else t0 + 4
            span = max(0.3, min(end - t0, 0.45 * len(words) + 0.6)) * 0.9
            for k, w in enumerate(words):
                tl.append((t0 + span * k / len(words), w, i))
    elif duration:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        words = [(w, i) for i, ln in enumerate(lines) for w in ln.split()]
        if words:
            a, b = duration * 0.08, duration * 0.95
            step = (b - a) / len(words)
            tl = [(a + k * step, w, li) for k, (w, li) in enumerate(words)]
    return tl


def fetch_lyrics(artist, title, duration, cache_dir, local_path=None):
    """Zwraca (tekst, zsynchronizowany?, długość wersji tekstu).
    Najpierw plik .lrc obok utworu, potem LRCLIB (wersja najbliższa długością)."""
    if local_path and not local_path.startswith(("http", "radio:")):
        lrc = Path(local_path).with_suffix(".lrc")
        if lrc.exists():
            return lrc.read_text(encoding="utf-8", errors="ignore"), True, 0
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = "v2_" + hashlib.md5(f"{artist}|{title}|{int(duration or 0) // 5}".lower().encode()).hexdigest()
    cache = cache_dir / (key + ".json")
    d = None
    if cache.exists():
        d = json.loads(cache.read_text(encoding="utf-8"))
    else:
        short = re.sub(r"\s*[\(\[]?(feat\.?|ft\.?)\s.*$", "", title, flags=re.I).strip() or title
        q = {"artist_name": artist, "track_name": short}
        if duration:
            q["duration"] = int(duration)
        try:
            d = json.loads(http_get(f"{LRCLIB}/get?" + urllib.parse.urlencode(q)))
        except Exception:
            d = None
        if not d or not (d.get("syncedLyrics") or d.get("plainLyrics")):
            res = json.loads(http_get(f"{LRCLIB}/search?" + urllib.parse.urlencode(
                {"q": f"{artist} {short}".strip()})))
            synced = [r for r in res if r.get("syncedLyrics")] or res

            def gap(r):
                return abs((r.get("duration") or 0) - (duration or 0)) if duration else 0
            d = min(synced, key=gap) if synced else None
        if d and (d.get("syncedLyrics") or d.get("plainLyrics")):
            cache.write_text(json.dumps(d), encoding="utf-8")
    if not d:
        return None, False, 0
    ldur = d.get("duration") or 0
    if d.get("syncedLyrics"):
        return d["syncedLyrics"], True, ldur
    if d.get("plainLyrics"):
        return d["plainLyrics"], False, ldur
    return None, False, 0


class _QuietLogger:
    """yt-dlp nie pisze na konsolę (w aplikacji graficznej potrafiło to wywołać błąd)."""
    def debug(self, msg):
        pass

    warning = info = debug

    def error(self, msg):
        pass


QUIET = _QuietLogger()


YT_FALLBACK_CLIENTS = (["android_vr"], ["tv", "web_safari"], ["mweb", "web_embedded"])
YT_RETRY_ERRORS = ("format is not available", "sign in to confirm", "no video formats",
                   "only images are available", "not a bot", "javascript")


def patch_ytdlp():
    """Bez silnika JavaScript (telefon) YouTube czasem nie podaje formatów.
    Wtedy ponawiamy pobranie przez inne klienty YouTube, które go nie wymagają."""
    try:
        import yt_dlp
    except ImportError:
        return
    if getattr(yt_dlp.YoutubeDL, "_leox_patch", False):
        return
    orig = yt_dlp.YoutubeDL.extract_info

    def extract_info(self, url, *a, **kw):
        try:
            return orig(self, url, *a, **kw)
        except yt_dlp.utils.DownloadError as e:
            low = str(e).lower()
            if "youtu" not in str(url) or not any(s in low for s in YT_RETRY_ERRORS):
                raise
            last = e
        for clients in YT_FALLBACK_CLIENTS:
            p = dict(self.params)
            ea = {k: dict(v) for k, v in (p.get("extractor_args") or {}).items()}
            ea.setdefault("youtube", {})["player_client"] = clients
            p["extractor_args"] = ea
            if p.get("format") and "/best" not in p["format"].replace("/bestaudio[", ""):
                p["format"] = p["format"] + "/bestaudio/18/best"
            try:
                with yt_dlp.YoutubeDL(p) as y2:
                    return orig(y2, url, *a, **kw)
            except yt_dlp.utils.DownloadError as e2:
                last = e2
        raise last

    yt_dlp.YoutubeDL.extract_info = extract_info
    yt_dlp.YoutubeDL._leox_patch = True


def open_external(url):
    """Otwiera link w aplikacji YouTube (albo w przeglądarce)."""
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        try:
            ctx = autoclass("org.kivy.android.PythonActivity").mActivity
        except Exception:
            ctx = None
        if ctx is None:
            ctx = autoclass("android.app.ActivityThread").currentApplication()
        ctx.startActivity(intent)
        return True
    except Exception:
        import webbrowser
        return webbrowser.open(url)


def parse_vtt(text):
    """Napisy WebVTT -> [(start, koniec, tekst)]."""
    def sec(t):
        parts = t.replace(",", ".").split(":")
        v = 0.0
        for x in parts:
            v = v * 60 + float(x)
        return v
    cues, last = [], ""
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        for i, ln in enumerate(lines):
            if "-->" in ln:
                a, b = [x.strip().split(" ")[0] for x in ln.split("-->")]
                body = " ".join(re.sub(r"<[^>]+>", "", x).strip() for x in lines[i + 1:]).strip()
                if body and body != last:
                    try:
                        cues.append((sec(a), sec(b), body))
                        last = body
                    except ValueError:
                        pass
                break
    return cues


def dominant_color(path):
    """Średni kolor obrazka (do tła ekranu Teraz gra)."""
    try:
        px = CoreImage(path, keep_data=True).texture.pixels
        n = len(px) // 4
        step = max(1, n // 500)
        r = g = b = c = 0
        for i in range(0, n, step):
            o = i * 4
            r, g, b, c = r + px[o], g + px[o + 1], b + px[o + 2], c + 1
        return (r / c / 255, g / c / 255, b / c / 255) if c else None
    except Exception:
        return None


def local_ip():
    try:
        sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sk.connect(("10.255.255.255", 1))
        ip = sk.getsockname()[0]
        sk.close()
        return ip
    except Exception:
        return "127.0.0.1"


class WakeLock:
    """Utrzymuje procesor przy graniu z wygaszonym ekranem (tylko w APK)."""

    def __init__(self):
        self.lock = None
        try:
            from jnius import autoclass
            act = autoclass("org.kivy.android.PythonActivity").mActivity
            Context = autoclass("android.content.Context")
            PowerManager = autoclass("android.os.PowerManager")
            pm = act.getSystemService(Context.POWER_SERVICE)
            self.lock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "leox:odtwarzanie")
        except Exception:
            self.lock = None

    def set(self, on):
        if not self.lock:
            return
        try:
            if on and not self.lock.isHeld():
                self.lock.acquire()
            elif not on and self.lock.isHeld():
                self.lock.release()
        except Exception:
            pass


PARTY_HTML = """<!doctype html><html lang="pl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Leox Player - impreza</title>
<style>
body{margin:0;font-family:sans-serif;background:%BG%;color:#fff}
header{padding:16px;background:%CARD%}
h1{margin:0;font-size:20px;color:%ACCENT%}
#now{margin-top:6px;color:%MUTED%}
main{padding:12px}
input{width:100%;box-sizing:border-box;padding:14px;border-radius:14px;border:0;background:%CARD%;color:#fff;font-size:16px}
.tabs{display:flex;gap:8px;margin:10px 0}
button{border:0;border-radius:12px;padding:10px 14px;background:%CARD%;color:#fff;font-size:15px}
.tabs .on{background:%ACCENT%;color:%BG%}
.item{display:flex;align-items:center;gap:10px;background:%CARD%;border-radius:14px;padding:10px;margin:6px 0}
.item div{flex:1;min-width:0}
.item b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.item small{color:%MUTED%}
.item button{background:%ACCENT%;color:%BG%}
</style></head><body>
<header><h1>Leox Player</h1><div id="now">...</div></header>
<main>
<input id="q" placeholder="Szukaj utworu...">
<div class="tabs"><button id="t1" class="on">Muzyka gospodarza</button><button id="t2">YouTube</button></div>
<div id="res"></div>
<h3>Następne w kolejce</h3><div id="queue"></div>
</main>
<script>
let src='lib',timer=null;
const $=id=>document.getElementById(id);
function item(title,sub,addUrl){
  const d=document.createElement('div');d.className='item';
  const t=document.createElement('div');const b=document.createElement('b');b.textContent=title;
  const s=document.createElement('small');s.textContent=sub||'';t.append(b,s);d.append(t);
  if(addUrl){const btn=document.createElement('button');btn.textContent='Dodaj';
    btn.onclick=async()=>{btn.disabled=true;btn.textContent='...';
      try{const r=await fetch(addUrl);const j=await r.json();btn.textContent=j.ok?'Dodano':(j.msg||'Błąd');}
      catch(e){btn.textContent='Błąd';}};
    d.append(btn);}
  return d;}
async function search(){
  const q=$('q').value.trim();const box=$('res');
  if(q.length<2){box.innerHTML='';return;}
  box.textContent='Szukanie...';
  try{const r=await fetch('/api/'+(src==='lib'?'search':'yt')+'?q='+encodeURIComponent(q));
    const j=await r.json();box.innerHTML='';
    if(!j.length){box.textContent='Nic nie znaleziono';}
    j.forEach(x=>box.append(item(x.title,x.sub,'/api/add?'+(src==='lib'?'id=':'yt=')+
      encodeURIComponent(x.id)+'&t='+encodeURIComponent(x.title)+'&a='+encodeURIComponent(x.sub||''))));}
  catch(e){box.textContent='Błąd połączenia';}}
$('q').oninput=()=>{clearTimeout(timer);timer=setTimeout(search,600);};
$('t1').onclick=()=>{src='lib';$('t1').className='on';$('t2').className='';search();};
$('t2').onclick=()=>{src='yt';$('t2').className='on';$('t1').className='';search();};
async function state(){
  try{const r=await fetch('/api/state');const j=await r.json();
    $('now').textContent=j.now?('Teraz gra: '+j.now):'Nic nie gra';
    const qb=$('queue');qb.innerHTML='';j.queue.forEach(x=>qb.append(item(x.title,x.sub,null)));}
  catch(e){}}
state();setInterval(state,5000);
</script></body></html>"""


AUDIO_TYPES = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".flac": "audio/flac",
               ".ogg": "audio/ogg", ".opus": "audio/ogg", ".wav": "audio/wav",
               ".aac": "audio/aac", ".webm": "audio/webm"}


def hex_color(c):
    return "#" + "".join(f"{int(x * 255):02x}" for x in c[:3])


WEB_STYLE = """<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{margin:0;font-family:sans-serif;background:%BG%;color:#fff}
header{padding:16px 20px;background:%CARD%}h1{margin:0;font-size:22px;color:%ACCENT%}
main{padding:16px 20px;max-width:900px;margin:auto}
input{width:100%;box-sizing:border-box;padding:14px;border-radius:14px;border:0;background:%CARD%;color:#fff;font-size:16px}
button{border:0;border-radius:14px;padding:14px 22px;background:%ACCENT%;color:%BG%;font-size:17px;cursor:pointer}
.row{display:flex;align-items:center;gap:12px;background:%CARD%;border-radius:14px;padding:10px 14px;margin:6px 0;cursor:pointer}
.row:hover,.row.on{outline:2px solid %ACCENT%}
.row div{flex:1;min-width:0}.row b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
small{color:%MUTED%}a{color:%ACCENT%}
#bar{position:sticky;bottom:0;background:%CARD%;padding:12px 20px}audio{width:100%}
</style>"""

WEB_HOME = """<!doctype html><html lang="pl"><head>%STYLE%<title>Leox Player</title></head><body>
<header><h1>Leox Player</h1></header><main>
<p><a href="/biblioteka">Biblioteka</a> - słuchaj muzyki z telefonu na tym komputerze.</p>
<p><a href="/odbiornik">Odbiornik</a> - telefon wysyła muzykę, a ten komputer ją gra.</p>
</main></body></html>"""

WEB_LIBRARY = """<!doctype html><html lang="pl"><head>%STYLE%<title>Leox Player - biblioteka</title></head><body>
<header><h1>Leox Player - biblioteka</h1></header><main>
<input id="q" placeholder="Szukaj w bibliotece telefonu..."><div id="list"></div></main>
<div id="bar"><b id="now">Wybierz utwór</b><audio id="au" controls></audio></div>
<script>
let items=[],cur=-1,timer=null;const $=i=>document.getElementById(i);
async function load(){const r=await fetch('/api/lib?q='+encodeURIComponent($('q').value));items=await r.json();draw();}
function draw(){const l=$('list');l.innerHTML='';items.forEach((x,i)=>{const d=document.createElement('div');
 d.className='row'+(i===cur?' on':'');const t=document.createElement('div');const b=document.createElement('b');
 b.textContent=x.title;const s=document.createElement('small');s.textContent=x.artist+'  '+x.dur;t.append(b,s);d.append(t);
 d.onclick=()=>play(i);l.append(d);});}
function play(i){if(i<0||i>=items.length)return;cur=i;const x=items[i];$('au').src='/plik/'+x.id+x.ext;
 $('now').textContent=x.title+(x.artist?' - '+x.artist:'');$('au').play();draw();}
$('au').onended=()=>play(cur+1);
$('q').oninput=()=>{clearTimeout(timer);timer=setTimeout(load,400);};load();
</script></body></html>"""

WEB_RECEIVER = """<!doctype html><html lang="pl"><head>%STYLE%<title>Leox Player - odbiornik</title></head><body>
<header><h1>Leox Player - odbiornik</h1></header><main style="text-align:center">
<div id="start"><p>Kliknij, aby ten komputer grał muzykę wysyłaną z telefonu.</p>
<button id="go">Połącz z telefonem</button></div>
<div id="box" hidden><img id="cov" style="max-width:320px;width:70%;border-radius:18px;margin-top:10px" alt="">
<h2 id="t">Czekam na muzykę z telefonu...</h2><p><small id="a"></small></p>
<audio id="au" controls style="max-width:520px"></audio><p><small id="st"></small></p></div></main>
<script>
let seq=-1,track=0;const $=i=>document.getElementById(i);const au=$('au');
async function poll(){try{const r=await fetch('/api/rx/poll?seq='+seq);const cmds=await r.json();
 for(const c of cmds){seq=c.seq;run(c);}}catch(e){$('st').textContent='Brak połączenia z telefonem';}}
function run(c){if(c.cmd==='play'){track=c.track;au.src=c.url;$('t').textContent=c.title;$('a').textContent=c.artist;
  $('cov').src=c.cover||'';$('cov').hidden=!c.cover;
  au.onloadedmetadata=()=>{if(c.pos>1)au.currentTime=c.pos;au.onloadedmetadata=null;};au.play();}
 else if(c.cmd==='pause')au.pause();else if(c.cmd==='resume')au.play();
 else if(c.cmd==='seek')au.currentTime=c.pos;
 else if(c.cmd==='stop'){au.pause();au.removeAttribute('src');$('t').textContent='Wysyłanie zakończone';}}
async function report(){try{await fetch('/api/rx/status?track='+track+'&pos='+(au.currentTime||0)+
 '&dur='+(isFinite(au.duration)?au.duration:0)+'&paused='+(au.paused?1:0)+'&ended='+(au.ended?1:0));
 $('st').textContent='Połączono z telefonem';}catch(e){}}
$('go').onclick=()=>{$('start').hidden=true;$('box').hidden=false;au.play().catch(()=>{});
 poll();setInterval(poll,800);setInterval(report,1000);};
</script></body></html>"""


class LeoxWeb:
    """Serwer w sieci domowej: biblioteka w przeglądarce, odbiornik na komputerze,
    pliki dla komputera i telewizora (z obsługą przewijania - nagłówek Range)."""

    def __init__(self, app):
        self.app, self.ids, self.lock = app, {}, threading.Lock()
        self.cmds, self.seq, self.last_play = [], 0, None
        self.rx = {"track": 0, "pos": 0.0, "dur": 0.0, "paused": True, "ended": False, "seen": 0.0}
        style = WEB_STYLE
        for k in ("BG", "CARD", "ACCENT", "MUTED"):
            style = style.replace(f"%{k}%", hex_color(globals()[k]))
        self.pages = {p: html.replace("%STYLE%", style).encode("utf-8")
                      for p, html in (("/", WEB_HOME), ("/biblioteka", WEB_LIBRARY),
                                      ("/odbiornik", WEB_RECEIVER))}
        web = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, body, ctype="application/json; charset=utf-8", code=200, head=False):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                if not head:
                    self.wfile.write(body)

            def do_HEAD(self):
                self.route(head=True)

            def do_GET(self):
                self.route(head=False)

            def route(self, head):
                u = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(u.query)

                def g(k, d=""):
                    return (qs.get(k) or [d])[0][:300]
                try:
                    if u.path in web.pages:
                        self.send(web.pages[u.path], "text/html; charset=utf-8", head=head)
                    elif u.path.startswith("/plik/"):
                        web.serve_file(self, u.path[6:22], head)
                    elif u.path.startswith("/okladka/"):
                        r = web.lookup(u.path[9:25])
                        jpg = Path(r[0]).with_suffix(".jpg") if r else None
                        if jpg and jpg.exists():
                            self.send(jpg.read_bytes(), "image/jpeg", head=head)
                        else:
                            self.send(b"", "text/plain", 404, head)
                    elif u.path == "/api/lib":
                        q, out = g("q").casefold(), []
                        for r in web.app.lib.tracks():
                            if q and q not in " ".join(x or "" for x in r[1:4]).casefold():
                                continue
                            k = hashlib.md5(r[0].encode()).hexdigest()[:16]
                            web.ids[k] = r
                            out.append({"id": k, "ext": Path(r[0]).suffix, "title": r[1] or "?",
                                        "artist": r[2] or "", "dur": fmt(r[4])})
                            if len(out) >= 300:
                                break
                        self.send(json.dumps(out).encode("utf-8"), head=head)
                    elif u.path == "/api/rx/poll":
                        web.rx["seen"] = time.time()
                        self.send(json.dumps(web.rx_since(int(g("seq", "-1")))).encode("utf-8"))
                    elif u.path == "/api/rx/status":
                        web.rx.update(track=int(g("track", "0")), pos=float(g("pos", "0")),
                                      dur=float(g("dur", "0")), paused=g("paused") == "1",
                                      ended=g("ended") == "1", seen=time.time())
                        self.send(b"{}")
                    else:
                        self.send("Nie ma takiej strony".encode("utf-8"),
                                  "text/plain; charset=utf-8", 404, head)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                except Exception as e:
                    try:
                        self.send(json.dumps({"error": str(e)[:100]}).encode("utf-8"), code=500)
                    except Exception:
                        pass

        self.srv = None
        for port in range(8090, 8100):
            try:
                self.srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
                break
            except OSError:
                continue
        if self.srv is None:
            raise RuntimeError("zajęte porty 8090-8099")
        self.srv.daemon_threads = True
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://{local_ip()}:{self.srv.server_address[1]}"

    def lookup(self, key):
        if key not in self.ids:
            for r in self.app.lib.tracks():
                self.ids[hashlib.md5(r[0].encode()).hexdigest()[:16]] = r
        return self.ids.get(key)

    def file_url(self, path):
        k = hashlib.md5(path.encode()).hexdigest()[:16]
        self.ids.setdefault(k, (path, "", "", "", 0))
        return f"{self.base}/plik/{k}{Path(path).suffix}"

    def cover_url(self, path):
        k = hashlib.md5(path.encode()).hexdigest()[:16]
        return f"{self.base}/okladka/{k}" if Path(path).with_suffix(".jpg").exists() else ""

    def serve_file(self, h, key, head):
        r = self.lookup(key)
        if not r or not os.path.exists(r[0]):
            h.send(b"", "text/plain", 404, head)
            return
        path, size = r[0], os.path.getsize(r[0])
        start, end, code = 0, size - 1, 200
        m = re.match(r"bytes=(\d*)-(\d*)", h.headers.get("Range", ""))
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:
                start = max(0, size - int(m.group(2)))
            end, code = min(end, size - 1), 206
        h.send_response(code)
        h.send_header("Content-Type", AUDIO_TYPES.get(Path(path).suffix.lower(), "application/octet-stream"))
        h.send_header("Accept-Ranges", "bytes")
        h.send_header("Content-Length", str(end - start + 1))
        if code == 206:
            h.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        h.send_header("transferMode.dlna.org", "Streaming")
        h.end_headers()
        if head:
            return
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(65536, left))
                if not chunk:
                    break
                h.wfile.write(chunk)
                left -= len(chunk)

    # --- odbiornik na komputerze
    def rx_push(self, **cmd):
        with self.lock:
            self.seq += 1
            cmd["seq"] = self.seq
            self.cmds = (self.cmds + [cmd])[-60:]
            if cmd["cmd"] == "play":
                self.last_play = cmd

    def rx_since(self, seq):
        with self.lock:
            if seq < 0:
                if not self.last_play:
                    return []
                return [self.last_play] + [c for c in self.cmds if c["seq"] > self.last_play["seq"]]
            return [c for c in self.cmds if c["seq"] > seq]

    def stop(self):
        srv, self.srv = self.srv, None
        if srv:
            threading.Thread(target=lambda: (srv.shutdown(), srv.server_close()), daemon=True).start()


class CastPC:
    """Wysyłanie na komputer: przeglądarka na stronie /odbiornik gra muzykę."""

    def __init__(self, app, web):
        self.app, self.web, self.name = app, web, "komputer"

    def play(self, url, t, pos, tid, cover):
        self.web.rx["ended"] = False
        self.web.rx_push(cmd="play", url=url, title=t[1] or "?", artist=t[2] or "",
                         pos=pos, track=tid, cover=cover or "")

    def pause(self):
        self.web.rx_push(cmd="pause")

    def resume(self):
        self.web.rx_push(cmd="resume")

    def seek(self, sec):
        self.web.rx_push(cmd="seek", pos=sec)

    def stop(self):
        self.web.rx_push(cmd="stop")

    def status(self):
        r = self.web.rx
        return {"pos": r["pos"], "dur": r["dur"], "paused": r["paused"],
                "ended": r["ended"] and r["track"] == self.app.cast_track,
                "connected": time.time() - r["seen"] < 5}


def hms(sec):
    sec = int(max(0, sec))
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def parse_hms(s):
    try:
        return parse_duration(s.split(".")[0]) if s and s != "NOT_IMPLEMENTED" else 0
    except Exception:
        return 0


def xml_tag(xml, name):
    m = re.search(rf"<(?:\w+:)?{name}>(.*?)</(?:\w+:)?{name}>", xml, re.S)
    return m.group(1).strip() if m else ""


def ssdp_discover(timeout=3.0):
    """Szuka w sieci telewizorów i głośników DLNA (usługa AVTransport)."""
    msg = "\r\n".join(["M-SEARCH * HTTP/1.1", "HOST: 239.255.255.250:1900",
                        'MAN: "ssdp:discover"', "MX: 2",
                        "ST: urn:schemas-upnp-org:service:AVTransport:1", "", ""]).encode()
    sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sk.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sk.settimeout(0.5)
    locs, end = set(), time.time() + timeout
    for _ in range(2):
        sk.sendto(msg, ("239.255.255.250", 1900))
    while time.time() < end:
        try:
            data, _ = sk.recvfrom(4096)
        except socket.timeout:
            continue
        except OSError:
            break
        m = re.search(r"(?im)^location:\s*(\S+)", data.decode("utf-8", "ignore"))
        if m:
            locs.add(m.group(1))
    sk.close()
    devices = []
    for loc in locs:
        try:
            root = ET.fromstring(http_get(loc, timeout=4))
        except Exception:
            continue
        name, ctrl = "", ""
        for el in root.iter():
            tag = el.tag.split("}")[-1]
            if tag == "friendlyName" and not name:
                name = (el.text or "").strip()
            if tag == "service":
                st = {c.tag.split("}")[-1]: (c.text or "") for c in el}
                if "AVTransport" in st.get("serviceType", ""):
                    ctrl = urllib.parse.urljoin(loc, st.get("controlURL", ""))
        if ctrl:
            devices.append({"name": name or loc, "control": ctrl})
    return devices


def dlna_call(ctrl, action, args):
    body = ('<?xml version="1.0" encoding="utf-8"?><s:Envelope '
            'xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
            f'<u:{action} xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">'
            + "".join(f"<{k}>{xml_escape(str(v))}</{k}>" for k, v in args)
            + f"</u:{action}></s:Body></s:Envelope>")
    req = urllib.request.Request(ctrl, data=body.encode("utf-8"), method="POST", headers={
        "Content-Type": 'text/xml; charset="utf-8"',
        "SOAPAction": f'"urn:schemas-upnp-org:service:AVTransport:1#{action}"'})
    with urllib.request.urlopen(req, timeout=6) as r:
        return r.read().decode("utf-8", "ignore")


class CastDLNA:
    """Wysyłanie na telewizor / głośnik DLNA."""

    def __init__(self, dev):
        self.name, self.ctrl = dev["name"], dev["control"]
        self.st = {"pos": 0.0, "dur": 0.0, "paused": False, "ended": False, "connected": True}
        self.alive, self.was_playing, self.t0 = True, False, time.time()
        threading.Thread(target=self._poll, daemon=True).start()

    def _call(self, action, *args):
        return dlna_call(self.ctrl, action, [("InstanceID", 0)] + list(args))

    @staticmethod
    def _bg(fn):
        def run():
            try:
                fn()
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def play(self, url, t, pos, tid, cover):
        mime = AUDIO_TYPES.get(Path(urllib.parse.urlparse(url).path).suffix.lower(), "audio/mpeg")
        didl = ('<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" '
                'xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">'
                '<item id="1" parentID="0" restricted="1">'
                f"<dc:title>{xml_escape(t[1] or '?')}</dc:title>"
                f"<upnp:artist>{xml_escape(t[2] or '')}</upnp:artist>"
                "<upnp:class>object.item.audioItem.musicTrack</upnp:class>"
                f'<res protocolInfo="http-get:*:{mime}:*">{xml_escape(url)}</res></item></DIDL-Lite>')
        self.st["ended"], self.was_playing, self.t0 = False, False, time.time()

        def go():
            try:
                self._call("Stop")
            except Exception:
                pass
            self._call("SetAVTransportURI", ("CurrentURI", url), ("CurrentURIMetaData", didl))
            self._call("Play", ("Speed", "1"))
            if pos > 5:
                time.sleep(1.5)
                self._call("Seek", ("Unit", "REL_TIME"), ("Target", hms(pos)))
        self._bg(go)

    def pause(self):
        self._bg(lambda: self._call("Pause"))

    def resume(self):
        self._bg(lambda: self._call("Play", ("Speed", "1")))

    def seek(self, sec):
        self._bg(lambda: self._call("Seek", ("Unit", "REL_TIME"), ("Target", hms(sec))))

    def stop(self):
        self.alive = False
        self._bg(lambda: self._call("Stop"))

    def status(self):
        return self.st

    def _poll(self):
        while self.alive:
            try:
                x = self._call("GetPositionInfo")
                y = self._call("GetTransportInfo")
                state = xml_tag(y, "CurrentTransportState")
                self.st.update(pos=parse_hms(xml_tag(x, "RelTime")),
                               dur=parse_hms(xml_tag(x, "TrackDuration")),
                               paused=state == "PAUSED_PLAYBACK", connected=True)
                if state == "PLAYING":
                    self.was_playing = True
                if (self.was_playing and state in ("STOPPED", "NO_MEDIA_PRESENT")
                        and time.time() - self.t0 > 5):
                    self.st["ended"] = True
            except Exception:
                self.st["connected"] = False
            time.sleep(1)


MB_UA = {"User-Agent": "LeoxPlayer/1.0 (aplikacja prywatna)"}


def mb_lookup(artist, title):
    """MusicBrainz: najlepsze dopasowanie nagrania (tytuł, wykonawca, album, okładka)."""
    q = f'recording:"{title}"' + (f' AND artist:"{artist}"' if artist else "")
    req = urllib.request.Request("https://musicbrainz.org/ws/2/recording?fmt=json&limit=3&query="
                                 + urllib.parse.quote(q), headers=MB_UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        recs = json.loads(r.read()).get("recordings") or []
    if not recs:
        return None
    rec = recs[0]
    rels = rec.get("releases") or [{}]
    # najpierw oryginalny album (nie składanka, nie singiel), potem najstarsze wydanie
    rels.sort(key=lambda r: ((r.get("release-group") or {}).get("primary-type") != "Album",
                             bool((r.get("release-group") or {}).get("secondary-types")),
                             r.get("date") or "9999"))
    rel = rels[0]
    return {"score": int(rec.get("score", 0)), "title": rec.get("title") or title,
            "artist": "".join(c.get("name", "") + c.get("joinphrase", "")
                              for c in rec.get("artist-credit", [])) or artist,
            "album": rel.get("title", ""), "release": rel.get("id"),
            "group": (rel.get("release-group") or {}).get("id")}


def caa_cover(info):
    """Okładka z Cover Art Archive: najpierw dla całego albumu, potem dla wydania."""
    for kind, key in (("release-group", info.get("group")), ("release", info.get("release"))):
        if not key:
            continue
        try:
            req = urllib.request.Request(f"https://coverartarchive.org/{kind}/{key}/front-250",
                                         headers=MB_UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read()
        except Exception:
            continue
    return None


def android_context():
    from jnius import autoclass
    try:
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        if act is not None:
            return act
    except Exception:
        pass
    return autoclass("android.app.ActivityThread").currentApplication()


def share_text(text, subject):
    """Okno Androida 'Udostępnij' (Dysk Google, Gmail, Keep...)."""
    from jnius import autoclass, cast
    Intent = autoclass("android.content.Intent")
    it = Intent(Intent.ACTION_SEND)
    it.setType("text/plain")
    it.putExtra(Intent.EXTRA_SUBJECT, cast("java.lang.CharSequence", autoclass("java.lang.String")(subject)))
    it.putExtra(Intent.EXTRA_TEXT, cast("java.lang.CharSequence", autoclass("java.lang.String")(text)))
    chooser = Intent.createChooser(it, cast("java.lang.CharSequence",
                                            autoclass("java.lang.String")("Zapisz kopię Leox Player")))
    chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    android_context().startActivity(chooser)


def video_headers(headers):
    """Kivy nie przekazuje nagłówków do ffpyplayer - dokładamy je tutaj."""
    try:
        import kivy.core.video.video_ffpyplayer as vf
        orig = getattr(vf, "_leox_orig_mp", None) or vf.MediaPlayer
        vf._leox_orig_mp = orig
        hdr = "".join(f"{k}: {v}\r\n" for k, v in (headers or {}).items())

        def wrapped(*a, **kw):
            if hdr:
                lo = dict(kw.get("lib_opts") or {})
                lo.setdefault("headers", hdr)
                kw["lib_opts"] = lo
            return orig(*a, **kw)
        vf.MediaPlayer = wrapped
    except Exception:
        pass


def fmt(t):
    t = int(t or 0)
    return f"{t // 60}:{t % 60:02d}"


def setup_font(folder):
    """Pobiera zaokrągloną czcionkę Varela Round (raz) i ustawia ją jako domyślną."""
    path = Path(folder) / "VarelaRound-Regular.ttf"
    try:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".part")
            with urllib.request.urlopen(FONT_URL, timeout=10) as r:
                tmp.write_bytes(r.read())
            tmp.rename(path)
        # nadpisanie domyślnej "Roboto" zmienia czcionkę w całej aplikacji
        LabelBase.register(name="Roboto", fn_regular=str(path))
    except Exception:
        pass    # brak internetu przy pierwszym starcie - zostaje standardowa czcionka


def request_perms():
    try:
        from android.permissions import request_permissions
        request_permissions([
            "android.permission.READ_MEDIA_AUDIO",
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.POST_NOTIFICATIONS",
        ])
    except Exception:
        pass


# ---------------------------------------------------------------- biblioteka
class Library:
    def __init__(self, path, dirs):
        self.dirs = dirs
        self.lock = threading.Lock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tracks(
                path TEXT PRIMARY KEY, title TEXT, artist TEXT,
                album TEXT, duration REAL, mtime REAL);
            CREATE TABLE IF NOT EXISTS playlists(
                id INTEGER PRIMARY KEY, name TEXT UNIQUE);
            CREATE TABLE IF NOT EXISTS playlist_tracks(
                playlist_id INTEGER, path TEXT, pos INTEGER);
            CREATE TABLE IF NOT EXISTS channels(
                url TEXT PRIMARY KEY, name TEXT);
            CREATE TABLE IF NOT EXISTS favorites(
                path TEXT PRIMARY KEY, added REAL);
            CREATE TABLE IF NOT EXISTS history(
                path TEXT, played REAL);
            CREATE TABLE IF NOT EXISTS seen(
                id TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS positions(
                path TEXT PRIMARY KEY, pos REAL);
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS stats(
                path TEXT PRIMARY KEY, plays INTEGER, last REAL);
            CREATE TABLE IF NOT EXISTS stations(
                url TEXT PRIMARY KEY, name TEXT, icon TEXT);
            CREATE TABLE IF NOT EXISTS podcasts(
                url TEXT PRIMARY KEY, title TEXT, image TEXT);
            CREATE TABLE IF NOT EXISTS play_log(
                path TEXT, ts REAL);
            CREATE TABLE IF NOT EXISTS yt_history(
                id TEXT PRIMARY KEY, title TEXT, channel TEXT, dur REAL, ch_url TEXT, ts REAL);
            CREATE TABLE IF NOT EXISTS yt_later(
                id TEXT PRIMARY KEY, title TEXT, channel TEXT, dur REAL, ch_url TEXT, ts REAL);
        """)
        if self.get_setting("wersja_tagow") != "2":      # jednorazowe odczytanie tytułów od nowa
            self.db.execute("UPDATE tracks SET mtime=0")
            self.set_setting("wersja_tagow", "2")

    @staticmethod
    def read_tags(p):
        title, artist = split_name(p.stem)
        album, dur = "", 0.0
        if mutagen:
            try:
                f = mutagen.File(p, easy=True)
                if f is not None:
                    title = (f.get("title") or [title])[0]
                    artist = (f.get("artist") or [artist])[0]
                    album = (f.get("album") or [""])[0]
                    dur = float(getattr(f.info, "length", 0) or 0)
            except Exception:
                pass
        return title, artist, album, dur

    def scan(self):
        with self.lock:
            known = dict(self.db.execute("SELECT path, mtime FROM tracks"))
        found, rows = set(), []
        for top in self.dirs:
            for root, _, files in os.walk(top):
                if Path(root).name == "Filmy":        # pobrane filmy to nie muzyka
                    continue
                for name in files:
                    p = Path(root) / name
                    if p.suffix.lower() not in EXT:
                        continue
                    try:
                        mt = p.stat().st_mtime
                    except OSError:
                        continue
                    sp = str(p)
                    found.add(sp)
                    if known.get(sp) != mt:
                        rows.append((sp, *self.read_tags(p), mt))
        gone = [(k,) for k in known if k not in found]
        with self.lock:
            self.db.executemany(
                "INSERT OR REPLACE INTO tracks VALUES(?,?,?,?,?,?)", rows)
            self.db.executemany("DELETE FROM tracks WHERE path=?", gone)
            self.db.commit()
        return len(rows), len(gone)

    def tracks(self):
        with self.lock:
            return self.db.execute(
                "SELECT path,title,artist,album,duration FROM tracks ORDER BY "
                "artist COLLATE NOCASE, album COLLATE NOCASE, title COLLATE NOCASE"
            ).fetchall()

    def playlists(self):
        with self.lock:
            return self.db.execute(
                "SELECT id,name FROM playlists ORDER BY name COLLATE NOCASE").fetchall()

    def playlist_tracks(self, pid):
        with self.lock:
            return self.db.execute(
                "SELECT t.path,t.title,t.artist,t.album,t.duration "
                "FROM playlist_tracks pt JOIN tracks t ON t.path=pt.path "
                "WHERE pt.playlist_id=? ORDER BY pt.pos", (pid,)).fetchall()

    def add_to_playlist(self, name, path):
        with self.lock:
            self.db.execute("INSERT OR IGNORE INTO playlists(name) VALUES(?)", (name,))
            pid = self.db.execute(
                "SELECT id FROM playlists WHERE name=?", (name,)).fetchone()[0]
            pos = self.db.execute(
                "SELECT COALESCE(MAX(pos),-1)+1 FROM playlist_tracks "
                "WHERE playlist_id=?", (pid,)).fetchone()[0]
            self.db.execute(
                "INSERT INTO playlist_tracks VALUES(?,?,?)", (pid, path, pos))
            self.db.commit()

    def remove_from_playlist(self, pid, path):
        with self.lock:
            self.db.execute(
                "DELETE FROM playlist_tracks WHERE playlist_id=? AND path=?",
                (pid, path))
            self.db.commit()

    def channels(self):
        with self.lock:
            return self.db.execute(
                "SELECT url,name FROM channels ORDER BY name COLLATE NOCASE").fetchall()

    def save_channel(self, url, name):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO channels VALUES(?,?)", (url, name))
            self.db.commit()

    def remove_channel(self, url):
        with self.lock:
            self.db.execute("DELETE FROM channels WHERE url=?", (url,))
            self.db.commit()

    # ulubione
    def is_fav(self, path):
        with self.lock:
            return self.db.execute(
                "SELECT 1 FROM favorites WHERE path=?", (path,)).fetchone() is not None

    def set_fav(self, path, on):
        with self.lock:
            if on:
                self.db.execute("INSERT OR IGNORE INTO favorites VALUES(?,?)",
                                (path, time.time()))
            else:
                self.db.execute("DELETE FROM favorites WHERE path=?", (path,))
            self.db.commit()

    def favorites(self):
        with self.lock:
            return self.db.execute(
                "SELECT t.path,t.title,t.artist,t.album,t.duration "
                "FROM favorites f JOIN tracks t ON t.path=f.path "
                "ORDER BY f.added DESC").fetchall()

    # historia
    def add_history(self, path):
        with self.lock:
            self.db.execute("INSERT INTO history VALUES(?,?)", (path, time.time()))
            self.db.execute("INSERT INTO play_log VALUES(?,?)", (path, time.time()))
            self.db.execute("INSERT OR IGNORE INTO stats VALUES(?,0,0)", (path,))
            self.db.execute("UPDATE stats SET plays=plays+1, last=? WHERE path=?",
                            (time.time(), path))
            self.db.execute(
                "DELETE FROM history WHERE rowid NOT IN "
                "(SELECT rowid FROM history ORDER BY played DESC LIMIT 500)")
            self.db.commit()

    def history(self):
        with self.lock:
            return self.db.execute(
                "SELECT t.path,t.title,t.artist,t.album,t.duration FROM "
                "(SELECT path, MAX(played) m FROM history GROUP BY path) h "
                "JOIN tracks t ON t.path=h.path ORDER BY h.m DESC LIMIT 100").fetchall()

    # zapamiętana pozycja w długich nagraniach
    def get_pos(self, path):
        with self.lock:
            r = self.db.execute("SELECT pos FROM positions WHERE path=?", (path,)).fetchone()
        return r[0] if r else 0

    def set_pos(self, path, pos):
        with self.lock:
            if pos > 0:
                self.db.execute("INSERT OR REPLACE INTO positions VALUES(?,?)", (path, pos))
            else:
                self.db.execute("DELETE FROM positions WHERE path=?", (path,))
            self.db.commit()

    # widziane filmy (do nowości z kanałów)
    def unseen(self, ids):
        with self.lock:
            seen = {r[0] for r in self.db.execute("SELECT id FROM seen")}
        return {i for i in ids if i and i not in seen}

    def mark_seen(self, ids):
        with self.lock:
            self.db.executemany("INSERT OR IGNORE INTO seen VALUES(?)",
                                [(i,) for i in ids if i])
            self.db.commit()


    # ustawienia
    def get_setting(self, key, default=""):
        with self.lock:
            r = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r[0] if r else default

    def set_setting(self, key, value):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, str(value)))
            self.db.commit()

    # widoki automatyczne
    def _q(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args).fetchall()

    COLS = "path,title,artist,album,duration"

    def recent(self):
        return self._q(f"SELECT {self.COLS} FROM tracks ORDER BY mtime DESC LIMIT 100")

    def never_played(self):
        return self._q(f"SELECT {self.COLS} FROM tracks WHERE path NOT IN "
                       "(SELECT path FROM stats) ORDER BY artist COLLATE NOCASE, title")

    def daily_mix(self):
        rows = self.tracks()
        rnd = random.Random(datetime.date.today().isoformat())
        return rnd.sample(rows, min(50, len(rows)))

    def duplicates(self):
        groups = {}
        for r in self.tracks():
            key = ((r[2] or "").casefold().strip(), (r[1] or "").casefold().strip())
            groups.setdefault(key, []).append(r)
        return [r for g in groups.values() if len(g) > 1 for r in g]

    def artists(self):
        return self._q("SELECT COALESCE(NULLIF(artist,''),'?') a, COUNT(*) FROM tracks "
                       "GROUP BY a ORDER BY a COLLATE NOCASE")

    def albums(self):
        return self._q("SELECT COALESCE(NULLIF(album,''),'(bez albumu)') a, COUNT(*) FROM tracks "
                       "GROUP BY a ORDER BY a COLLATE NOCASE")

    def by_artist(self, name):
        return self._q(f"SELECT {self.COLS} FROM tracks WHERE COALESCE(NULLIF(artist,''),'?')=? "
                       "ORDER BY album COLLATE NOCASE, title COLLATE NOCASE", (name,))

    def by_album(self, name):
        return self._q(f"SELECT {self.COLS} FROM tracks WHERE "
                       "COALESCE(NULLIF(album,''),'(bez albumu)')=? ORDER BY title", (name,))

    # statystyki
    def top_tracks(self, n=15):
        return self._q("SELECT t.title, t.artist, s.plays FROM stats s JOIN tracks t "
                       "ON t.path=s.path ORDER BY s.plays DESC LIMIT ?", (n,))

    def top_artists(self, n=10):
        return self._q("SELECT COALESCE(NULLIF(t.artist,''),'?'), SUM(s.plays) p FROM stats s "
                       "JOIN tracks t ON t.path=s.path GROUP BY 1 ORDER BY p DESC LIMIT ?", (n,))

    def totals(self):
        r = self._q("SELECT COUNT(*), COALESCE(SUM(duration),0) FROM tracks")[0]
        plays = self._q("SELECT COALESCE(SUM(plays),0) FROM stats")[0][0]
        return r[0], r[1], plays

    # edycja i usuwanie
    def set_tags(self, path, title, artist):
        with self.lock:
            self.db.execute("UPDATE tracks SET title=?, artist=? WHERE path=?",
                            (title, artist, path))
            self.db.commit()

    def forget_track(self, path):
        with self.lock:
            for t in ("tracks", "favorites", "playlist_tracks", "positions", "history", "stats"):
                self.db.execute(f"DELETE FROM {t} WHERE path=?", (path,))
            self.db.commit()

    # radio i podcasty
    def stations(self):
        return self._q("SELECT url,name,icon FROM stations ORDER BY name COLLATE NOCASE")

    def save_station(self, url, name, icon):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO stations VALUES(?,?,?)", (url, name, icon))
            self.db.commit()

    def remove_station(self, url):
        with self.lock:
            self.db.execute("DELETE FROM stations WHERE url=?", (url,))
            self.db.commit()

    def podcasts(self):
        return self._q("SELECT url,title,image FROM podcasts ORDER BY title COLLATE NOCASE")

    def save_podcast(self, url, title, image):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO podcasts VALUES(?,?,?)", (url, title, image))
            self.db.commit()

    # podsumowanie roku
    def year_summary(self, year):
        t0 = datetime.datetime(year, 1, 1).timestamp()
        rows = self._q("SELECT l.path, l.ts, t.title, t.artist, t.duration FROM play_log l "
                       "LEFT JOIN tracks t ON t.path=l.path WHERE l.ts>=?", (t0,))
        hours = Counter(datetime.datetime.fromtimestamp(r[1]).hour for r in rows)
        return {"plays": len(rows),
                "minutes": int(sum(r[4] or 0 for r in rows) // 60),
                "distinct": len({r[0] for r in rows}),
                "top_tracks": Counter((r[2] or Path(r[0]).stem, r[3] or "") for r in rows).most_common(5),
                "top_artists": Counter((r[3] or "Nieznany wykonawca") for r in rows).most_common(5),
                "hour": hours.most_common(1)[0][0] if hours else None}

    def set_album(self, path, album):
        with self.lock:
            self.db.execute("UPDATE tracks SET album=? WHERE path=?", (album, path))
            self.db.commit()

    # YouTube: historia i "Do obejrzenia"
    def yt_add(self, table, v):
        if not v.get("id"):
            return
        with self.lock:
            self.db.execute(f"INSERT OR REPLACE INTO {table} VALUES(?,?,?,?,?,?)",
                            (v["id"], v["title"], v["channel"], v.get("dur") or 0,
                             v.get("ch_url") or "", time.time()))
            self.db.commit()

    def yt_list(self, table):
        rows = self._q(f"SELECT id,title,channel,dur,ch_url FROM {table} ORDER BY ts DESC LIMIT 100")
        return [{"id": i, "title": t, "channel": c, "dur": d, "ch_url": cu or None,
                 "url": f"https://www.youtube.com/watch?v={i}"} for i, t, c, d, cu in rows]

    def yt_remove(self, table, vid=None):
        with self.lock:
            if vid:
                self.db.execute(f"DELETE FROM {table} WHERE id=?", (vid,))
            else:
                self.db.execute(f"DELETE FROM {table}")
            self.db.commit()

    def remove_podcast(self, url):
        with self.lock:
            self.db.execute("DELETE FROM podcasts WHERE url=?", (url,))
            self.db.commit()


# ---------------------------------------------------------------- odtwarzacz
class Player:
    """Android MediaPlayer przez pyjnius; poza Androidem Kivy SoundLoader."""

    def __init__(self):
        self.mp = self.snd = None
        self.paused = False
        self._pp = 0
        self.speed = 1.0
        self.vol, self.gain = 1.0, 1.0          # głośność użytkownika i wyrównanie
        self.eq_preset, self.bass = -1, 0       # -1 = korektor wyłączony, -2 = własny
        self.eq_bands = []
        self.fade_in, self._old = 1.0, None     # przejście: nowy narasta, stary cichnie
        self.on_done, self._listener = None, None   # wywołanie po końcu utworu (gdy aplikacja w tle)
        self._fx = []
        try:
            from jnius import autoclass
            self.MP = autoclass("android.media.MediaPlayer")
            self.PP = autoclass("android.media.PlaybackParams")
        except Exception:
            self.MP = self.PP = None
        try:
            from jnius import autoclass
            self.EQ = autoclass("android.media.audiofx.Equalizer")
            self.BB = autoclass("android.media.audiofx.BassBoost")
        except Exception:
            self.EQ = self.BB = None

    def prepare(self, source, headers=None):
        """Tworzy gotowy MediaPlayer. Może działać w wątku (strumienie).
        headers: nagłówki HTTP wymagane przez serwer (np. YouTube)."""
        if not self.MP:
            raise RuntimeError("strumieniowanie działa tylko na Androidzie")
        mp = self.MP()
        try:
            if headers:
                from jnius import autoclass
                Uri = autoclass("android.net.Uri")
                m = autoclass("java.util.HashMap")()
                for k, val in headers.items():
                    m.put(str(k), str(val))
                mp.setDataSource(android_context(), Uri.parse(source), m)
            else:
                mp.setDataSource(source)
            mp.prepare()
        except Exception:
            mp.release()
            raise
        return mp

    def attach(self, mp):
        self.stop()
        self.paused = False
        self.mp = mp
        self.set_volume(self.vol)
        self._hook(mp)
        mp.start()
        self.apply_speed()
        self.apply_fx()
        self.start_meter()

    def _hook(self, mp):
        """Android sam powiadamia o końcu utworu - działa też, gdy okno aplikacji jest w tle."""
        if not self.on_done:
            return
        try:
            if self._listener is None:
                from jnius import PythonJavaClass, java_method
                player = self

                class Done(PythonJavaClass):
                    __javainterfaces__ = ["android/media/MediaPlayer$OnCompletionListener"]
                    __javacontext__ = "app"

                    @java_method("(Landroid/media/MediaPlayer;)V")
                    def onCompletion(self, m):
                        try:
                            player.on_done()
                        except Exception:
                            pass
                self._listener = Done()
            mp.setOnCompletionListener(self._listener)
        except Exception:
            pass

    def start_meter(self):
        """Pomiar głośności (Visualizer). Wymaga zgody na mikrofon - bez niej rytm jest symulowany."""
        self.stop_meter()
        if not self.mp:
            return
        try:
            from jnius import autoclass
            V = autoclass("android.media.audiofx.Visualizer")
            M = autoclass("android.media.audiofx.Visualizer$MeasurementPeakRms")
            v = V(self.mp.getAudioSessionId())
            v.setMeasurementMode(V.MEASUREMENT_MODE_PEAK_RMS)
            v.setEnabled(True)
            self.meter = (v, M())
        except Exception:
            self.meter = None

    def stop_meter(self):
        m = getattr(self, "meter", None)
        if m:
            try:
                m[0].setEnabled(False)
                m[0].release()
            except Exception:
                pass
        self.meter = None

    def level(self):
        """0..1 albo None, gdy pomiar niedostępny."""
        m = getattr(self, "meter", None)
        if not m:
            return None
        try:
            m[0].getMeasurementPeakRms(m[1])
            return max(0.0, min(1.0, (m[1].mRms + 4800) / 4000))
        except Exception:
            return None

    def apply_fx(self):
        for fx in self._fx:
            try:
                fx.release()
            except Exception:
                pass
        self._fx = []
        if not self.mp or not self.EQ:
            return
        sid = self.mp.getAudioSessionId()
        try:
            if self.eq_preset >= 0:
                eq = self.EQ(0, sid)
                eq.usePreset(self.eq_preset)
                eq.setEnabled(True)
                self._fx.append(eq)
            elif self.eq_preset == -2 and self.eq_bands:
                eq = self.EQ(0, sid)
                for i, lvl in enumerate(self.eq_bands):
                    eq.setBandLevel(i, int(lvl))
                eq.setEnabled(True)
                self._fx.append(eq)
            if self.bass > 0:
                bb = self.BB(0, sid)
                bb.setStrength(int(self.bass))
                bb.setEnabled(True)
                self._fx.append(bb)
        except Exception:
            pass

    def eq_info(self):
        """(liczba pasm, (min, max) w milibelach, częstotliwości w Hz)."""
        if not self.EQ or not self.MP:
            return None
        tmp = self.MP()
        try:
            eq = self.EQ(0, tmp.getAudioSessionId())
            n = eq.getNumberOfBands()
            rng = list(eq.getBandLevelRange())
            freqs = [eq.getCenterFreq(i) // 1000 for i in range(n)]
            eq.release()
            return n, (rng[0], rng[1]), freqs
        finally:
            tmp.release()

    def eq_presets(self):
        if not self.EQ or not self.MP:
            return []
        tmp = self.MP()
        try:
            eq = self.EQ(0, tmp.getAudioSessionId())
            names = [eq.getPresetName(i) for i in range(eq.getNumberOfPresets())]
            eq.release()
            return names
        finally:
            tmp.release()

    def load(self, path, fade=0):
        if self.MP and fade > 0 and self.mp is not None and not self.paused:
            new = self.prepare(path)
            old, self.mp = self.mp, None
            self.fade_in = 0.0
            self.attach(new)
            self._old = (old, time.time(), fade)
            return
        if self.MP:
            self.fade_in = 1.0
            self.attach(self.prepare(path))
        else:
            self.stop()
            self.paused = False
            self.snd = SoundLoader.load(path)
            if not self.snd:
                raise RuntimeError("nie można otworzyć pliku")
            self.snd.play()

    def fade_step(self):
        if not self._old:
            return
        old, t0, dur = self._old
        k = (time.time() - t0) / dur
        if k >= 1:
            self.kill_old()
            self.fade_in = 1.0
            self.set_volume(self.vol)
            return
        try:
            vv = (1 - k) * self.vol
            old.setVolume(vv, vv)
        except Exception:
            pass
        self.fade_in = k
        self.set_volume(self.vol)

    def kill_old(self):
        if self._old:
            try:
                self._old[0].stop()
                self._old[0].release()
            except Exception:
                pass
            self._old = None

    def stop(self):
        self.kill_old()
        self.stop_meter()
        if self.mp:
            try:
                self.mp.stop()
            except Exception:
                pass
            self.mp.release()
            self.mp = None
        if self.snd:
            self.snd.stop()
            self.snd.unload()
            self.snd = None

    def toggle(self):
        if self.mp:
            self.mp.start() if self.paused else self.mp.pause()
        elif self.snd:
            if self.paused:
                self.snd.play()
                self.snd.seek(self._pp)
            else:
                self._pp = self.snd.get_pos()
                self.snd.stop()
        self.paused = not self.paused

    def set_speed(self, sp):
        self.speed = sp
        self.apply_speed()

    def apply_speed(self):
        if self.mp and self.PP:
            try:
                self.mp.setPlaybackParams(self.PP().setSpeed(float(self.speed)))
                if self.paused:
                    self.mp.pause()
            except Exception:
                pass

    def position(self):
        if self.mp:
            return self.mp.getCurrentPosition() / 1000
        return self.snd.get_pos() if self.snd else 0

    def duration(self):
        if self.mp:
            return self.mp.getDuration() / 1000
        return self.snd.length if self.snd else 0

    def seek(self, s):
        if self.mp:
            self.mp.seekTo(int(s * 1000))
        elif self.snd:
            self.snd.seek(s)

    def set_volume(self, v):
        self.vol = v = max(0.0, min(1.0, v))
        real = v * self.gain * self.fade_in
        if self.mp:
            self.mp.setVolume(real, real)
        elif self.snd:
            self.snd.volume = real

    def finished(self):
        if self.paused:
            return False
        if self.mp:
            if self.mp.isPlaying():
                return False
            dur = self.mp.getDuration()
            # przy strumieniu isPlaying bywa chwilowo False podczas buforowania
            return dur <= 0 or self.mp.getCurrentPosition() >= dur - 2000
        return bool(self.snd) and self.snd.state == "stop"


SERVICE_CLASS = "pl.leox.leoxplayer.ServiceLeoxplayer"


def service_available():
    """True tylko w APK z usługą odtwarzania (w Pydroid zawsze False)."""
    try:
        from jnius import autoclass
        autoclass(SERVICE_CLASS)
        return True
    except Exception:
        return False


class RemotePlayer:
    """Odtwarzacz w usłudze Androida (APK): gra także po zamknięciu aplikacji.
    Polecenia idą przez UDP do service.py, stan wraca co 0,5 s."""
    SVC_PORT, APP_PORT = 17401, 17402

    def __init__(self, on_msg):
        self.on_msg = on_msg
        self.paused, self.vol, self.gain, self.speed = False, 1.0, 1.0, 1.0
        self.eq_preset, self.bass, self.eq_bands = -1, 0, []
        self.mp = self.snd = None
        self.st = {"pos": 0.0, "dur": 0.0, "playing": False, "t": time.time()}
        self.last_toggle = 0.0
        self.alive, self.pending = False, []   # polecenia czekają, aż usługa wystartuje
        self.local = Player()                  # korektor (lista ustawień) i quiz
        self.MP, self.PP, self.EQ = self.local.MP, self.local.PP, self.local.EQ
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", self.APP_PORT))
        threading.Thread(target=self._listen, daemon=True).start()
        try:
            from jnius import autoclass
            act = autoclass("org.kivy.android.PythonActivity").mActivity
            autoclass(SERVICE_CLASS).start(act, "")
        except Exception:
            pass

    def _listen(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(65535)
                msg = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            if not self.alive:
                self.alive = True
                for kw in self.pending:
                    self._send(kw)
                self.pending = []
            if msg.get("event") == "status":
                self.st.update(pos=msg.get("pos", 0), dur=msg.get("dur", 0),
                               playing=msg.get("playing", False), t=time.time())
                if time.time() - self.last_toggle > 1.5:     # pauza z powiadomienia/słuchawek
                    self.paused = msg.get("paused", False)
            Clock.schedule_once(lambda dt, m=msg: self.on_msg(m))

    def cmd(self, **kw):
        if not self.alive:
            self.pending = self.pending[-30:] + [kw]
            return
        self._send(kw)

    def _send(self, kw):
        try:
            self.sock.sendto(json.dumps(kw).encode("utf-8"), ("127.0.0.1", self.SVC_PORT))
        except Exception:
            pass

    # --- ten sam interfejs co Player
    def load(self, path, fade=0):
        pass                                    # w APK kolejkę gra usługa

    def stop(self):
        self.cmd(cmd="stop")
        self.st["playing"] = False

    def toggle(self):
        self.st["pos"], self.st["t"] = self.position(), time.time()
        self.last_toggle = time.time()
        self.paused = not self.paused
        self.cmd(cmd="pause" if self.paused else "resume")

    def set_speed(self, sp):
        self.speed = sp
        self.cmd(cmd="speed", v=sp)

    def apply_fx(self):
        self.cmd(cmd="fx", eq=self.eq_preset, bass=self.bass, bands=self.eq_bands)

    def eq_presets(self):
        return self.local.eq_presets()

    def eq_info(self):
        return self.local.eq_info()

    def position(self):
        st = self.st
        p = st["pos"]
        if st["playing"] and not self.paused:
            p += (time.time() - st["t"]) * self.speed
        return min(p, st["dur"]) if st["dur"] else p

    def duration(self):
        return self.st["dur"]

    def seek(self, sec):
        self.cmd(cmd="seek", sec=sec)
        self.st.update(pos=sec, t=time.time())

    def set_volume(self, v):
        self.vol = max(0.0, min(1.0, v))
        self.cmd(cmd="volume", v=self.vol)

    def finished(self):
        return False                            # koniec utworu obsługuje usługa

    def level(self):
        return None

    def fade_step(self):
        pass


# ---------------------------------------------------------------- widgety
class Springy:
    """Przycisk lekko się wciska, odbija i rozchodzi się po nim fala od palca."""
    pscale = NumericProperty(1)
    ripple_r = NumericProperty(0)
    ripple_a = NumericProperty(0)
    rx = NumericProperty(0)
    ry = NumericProperty(0)

    def on_touch_down(self, touch):
        if ANIM["on"] and not self.disabled and self.collide_point(*touch.pos):
            self.rx, self.ry = touch.pos
            Animation.cancel_all(self, "ripple_r", "ripple_a")
            self.ripple_r, self.ripple_a = dp(8), 0.28
            Animation(ripple_r=max(self.width, self.height) * 1.15, d=0.5,
                      t="out_quad").start(self)
            Animation(ripple_a=0, d=0.6, t="in_quad").start(self)
        return super().on_touch_down(touch)

    def on_state(self, _w, state):
        if isinstance(self, ToggleButton):          # przełącznik: krótki impuls
            if ANIM["on"]:
                Animation.cancel_all(self, "pscale")
                (Animation(pscale=0.9, d=0.08) +
                 Animation(pscale=1, d=0.3, t="out_back")).start(self)
            return
        if state == "down":
            anim(self, d=0.08, t="out_quad", pscale=0.93)
        else:
            anim(self, d=0.3, t="out_back", pscale=1)


class RoundButton(Springy, Button):
    bg = ListProperty(list(CARD))


class RoundToggle(Springy, ToggleButton):
    bg = ListProperty(list(CARD))


class RoundSpinner(Springy, Spinner):
    bg = ListProperty(list(CARD))


class RoundInput(TextInput):
    """Tło rysowane POD tekstem i kursorem (wcześniej zasłaniało wpisywany tekst)."""

    def __init__(self, **kw):
        super().__init__(**kw)
        # grupa zachowuje kolejność: kolor, tekstura, kształt (samo insert ją psuło)
        grp = InstructionGroup()
        grp.add(Color(*CARD))
        self._bg = RoundedRectangle(radius=[dp(14)], texture=white_tex())
        grp.add(self._bg)
        self.canvas.before.insert(0, grp)
        self.bind(pos=self._update_bg, size=self._update_bg)
        self._update_bg()

    def _update_bg(self, *_):
        self._bg.pos = (self.x + dp(3), self.y + dp(3))
        self._bg.size = (max(self.width - dp(6), 0), max(self.height - dp(6), 0))


class RoundPopup(Popup):
    """Okno wjeżdża od dołu z lekkim odbiciem."""
    pscale = NumericProperty(1)
    py = NumericProperty(0)

    def open(self, *a, **kw):
        if ANIM["on"]:
            self.pscale, self.py = 0.88, -dp(60)
        super().open(*a, **kw)
        anim(self, d=0.38, t="out_back", pscale=1)
        anim(self, d=0.35, t="out_cubic", py=0)

    def dismiss(self, *a, **kw):
        anim(self, d=0.14, t="in_quad", pscale=0.92)
        anim(self, d=0.14, t="in_quad", py=-dp(30))
        super().dismiss(*a, **kw)


class SwipeArea(BoxLayout):
    """Przesunięcie w lewo/prawo zmienia utwór, dotknięcie zwija panel."""

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.ud["swipe_x"], touch.ud["swipe_y"] = touch.x, touch.y
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        x0 = touch.ud.get("swipe_x")
        if x0 is None:
            return super().on_touch_up(touch)
        touch.ud["swipe_x"] = None
        app = App.get_running_app()
        dx, dy = touch.x - x0, touch.y - touch.ud.get("swipe_y", touch.y)
        if dx < -dp(60) and abs(dy) < dp(50):
            app.next()
        elif dx > dp(60) and abs(dy) < dp(50):
            app.prev()
        elif abs(dy) > dp(40):
            app.toggle_mini()
        elif abs(dx) < dp(12):
            app.show_now_playing()
        return True


class VizBars(Widget):
    """Dekoracyjna wizualizacja (nie analizuje dźwięku)."""
    N = 28

    def __init__(self, **kw):
        super().__init__(**kw)
        self.levels = [0.05] * self.N
        self.phase = 0.0
        self.rects = []
        with self.canvas:
            for i in range(self.N):
                k = abs(i - (self.N - 1) / 2) / (self.N / 2)       # środek jaśniejszy
                Color(*[ACCENT[c] * (1 - 0.45 * k) + ACCENT_DIM[c] * 0.45 * k
                        for c in range(3)], 1)
                self.rects.append(RoundedRectangle(texture=white_tex(), radius=[dp(3)]))
        self.bind(pos=self.redraw, size=self.redraw)

    def step(self, playing):
        energy = getattr(App.get_running_app(), "energy", 0.6)
        self.phase += 0.25
        for i in range(self.N):
            if playing:
                wave = 0.5 + 0.35 * ((i * 7 + int(self.phase * 3)) % 11) / 10
                target = min(1.0, (0.3 + 0.9 * energy) * wave * random.uniform(0.55, 1.1))
            else:
                target = 0.05
            self.levels[i] += (target - self.levels[i]) * 0.3
        self.redraw()

    def redraw(self, *_):
        if not self.width:
            return
        w = self.width / self.N
        for i, r in enumerate(self.rects):
            h = max(dp(2), self.height * self.levels[i])
            r.pos = (self.x + i * w + dp(1), self.y + (self.height - h) / 2)
            r.size = (max(w - dp(2), 1), h)


class TrackMain(Springy, ButtonBehavior, BoxLayout):
    bg = ListProperty([0, 0, 0, 0])


class WarmDropDown(DropDown):
    """Menu widoków: pojawia się płynnie, wybrany widok jest wyróżniony."""

    def open(self, widget):
        app = App.get_running_app()
        for c in self.container.children:
            c.color = ACCENT if c.text == app.current_view else TEXT
        self.opacity = 0
        super().open(widget)
        anim(self, d=0.2, opacity=1)


def palette():
    """Kolory efektów: akcent motywu, biel i odcienie obok akcentu."""
    h, l, sat = colorsys.rgb_to_hls(*ACCENT[:3])
    cols = [tuple(ACCENT[:3]), tuple(TEXT[:3]), tuple(MUTED[:3])]
    for dh in (0.08, -0.08, 0.5):
        cols.append(colorsys.hls_to_rgb((h + dh) % 1, min(0.75, l + 0.05), max(sat, 0.5)))
    return cols


FX_MODES = ("Świetliki", "Gwiazdy", "Śnieg", "Bąbelki", "Zorza", "Wyłączone")


class FxBack(Widget):
    """Tło: świetliki, gwiazdy ze spadającymi gwiazdami, śnieg, bąbelki albo zorza."""
    COUNTS = {"Świetliki": 34, "Gwiazdy": 80, "Śnieg": 60, "Bąbelki": 24, "Zorza": 7}

    def __init__(self, mode="Świetliki", **kw):
        super().__init__(**kw)
        self.mode = mode
        self.parts, self.stars = [], []
        self.star_timer = 3.0
        self.bind(size=self.rebuild)

    def rebuild(self, *_):
        self.canvas.clear()
        self.parts, self.stars = [], []
        if self.mode not in self.COUNTS or self.width < 10:
            return
        cols = palette()
        for _ in range(self.COUNTS[self.mode]):
            p = {"phase": random.uniform(0, 6.28)}
            c = random.choice(cols) if self.mode in ("Świetliki", "Zorza", "Bąbelki") else TEXT[:3]
            with self.canvas:
                if self.mode in ("Świetliki", "Zorza"):
                    p["gc"] = Color(*c, 0)
                    p["g"] = Ellipse(texture=white_tex())
                p["c"] = Color(*c, 0)
                if self.mode == "Bąbelki":
                    p["e"] = Line(circle=(0, 0, 1), width=dp(1.1))
                else:
                    p["e"] = Ellipse(texture=white_tex())
            self.respawn(p, initial=True)
            self.parts.append(p)

    def respawn(self, p, initial=False):
        W, H, m = self.width, self.height, self.mode
        p["x"] = random.uniform(0, W)
        p["y"] = random.uniform(0, H)
        p["vx"] = p["vy"] = 0.0
        if m == "Świetliki":
            p["r"] = dp(random.uniform(1.5, 3.2))
            ang, v = random.uniform(0, 6.28), dp(random.uniform(6, 18))
            p["vx"], p["vy"] = math.cos(ang) * v, math.sin(ang) * v
        elif m == "Gwiazdy":
            p["r"] = dp(random.uniform(0.6, 1.8))
        elif m == "Śnieg":
            if not initial:
                p["y"] = H + dp(8)
            p["r"] = dp(random.uniform(1.2, 3.5))
            p["vy"] = -dp(random.uniform(18, 55))
        elif m == "Bąbelki":
            if not initial:
                p["y"] = -dp(20)
            p["r"] = dp(random.uniform(4, 14))
            p["vy"] = dp(random.uniform(14, 40))
        else:                                   # Zorza
            p["r"] = dp(random.uniform(90, 170))
            ang, v = random.uniform(0, 6.28), dp(random.uniform(4, 10))
            p["vx"], p["vy"] = math.cos(ang) * v, math.sin(ang) * v

    def update(self, dt, energy):
        if not self.parts:
            return
        m, W, H = self.mode, self.width, self.height
        speed, bright = 1 + energy * 1.6, 0.6 + energy * 0.7
        for p in self.parts:
            p["phase"] += dt * (1.5 + energy * 3)
            if m == "Świetliki":
                turn = random.uniform(-1.2, 1.2) * dt
                vx, vy = p["vx"], p["vy"]
                p["vx"] = vx * math.cos(turn) - vy * math.sin(turn)
                p["vy"] = vx * math.sin(turn) + vy * math.cos(turn)
            elif m == "Śnieg":
                p["vx"] = math.sin(p["phase"] * 0.7) * dp(12)
            elif m == "Bąbelki":
                p["vx"] = math.sin(p["phase"]) * dp(10)
            p["x"] += p["vx"] * dt * speed
            p["y"] += p["vy"] * dt * speed
            r = p["r"]
            if m in ("Świetliki", "Zorza", "Gwiazdy"):          # zawijanie przy krawędziach
                if p["x"] < -r:
                    p["x"] = W + r
                elif p["x"] > W + r:
                    p["x"] = -r
                if p["y"] < -r:
                    p["y"] = H + r
                elif p["y"] > H + r:
                    p["y"] = -r
            elif m == "Śnieg" and p["y"] < -dp(10):
                self.respawn(p)
            elif m == "Bąbelki" and p["y"] > H + dp(20):
                self.respawn(p)
            tw = 0.5 + 0.5 * math.sin(p["phase"])
            if m == "Świetliki":
                a = (0.25 + 0.75 * tw) * bright
                p["c"].a, p["gc"].a = min(1, a), min(0.35, a * 0.22)
                gr = r * (4 + 2 * energy)
                p["g"].pos, p["g"].size = (p["x"] - gr, p["y"] - gr), (gr * 2, gr * 2)
            elif m == "Gwiazdy":
                p["c"].a = min(1, (0.2 + 0.8 * tw) * bright * 0.8)
            elif m == "Śnieg":
                p["c"].a = 0.35 + 0.45 * (r / dp(3.5))
            elif m == "Bąbelki":
                p["c"].a = max(0.0, min(0.55, (1 - p["y"] / max(H, 1)) * 0.6)) * bright
                p["e"].circle = (p["x"], p["y"], r * (1 + 0.15 * energy))
                continue
            else:
                a = (0.03 + 0.03 * tw) * (0.8 + energy)
                p["c"].a, p["gc"].a = min(0.1, a), min(0.05, a * 0.5)
                gr = r * 1.6 * (1 + 0.1 * energy)
                p["g"].pos, p["g"].size = (p["x"] - gr, p["y"] - gr), (gr * 2, gr * 2)
                r *= 1 + 0.12 * energy
            p["e"].pos, p["e"].size = (p["x"] - r, p["y"] - r), (r * 2, r * 2)
        if m == "Gwiazdy":
            self.shooting(dt, energy)

    def shooting(self, dt, energy):
        self.star_timer -= dt * (1 + energy * 2)
        if self.star_timer <= 0:
            self.star_timer = random.uniform(2.5, 7)
            with self.canvas:
                col = Color(*TEXT[:3], 0.9)
                ln = Line(points=[0, 0, 0, 0], width=dp(1.4), cap="round")
            self.stars.append({"x": random.uniform(self.width * 0.3, self.width * 1.1),
                               "y": random.uniform(self.height * 0.5, self.height),
                               "vx": -dp(random.uniform(380, 560)),
                               "vy": -dp(random.uniform(160, 260)),
                               "life": 0.9, "c": col, "l": ln})
        for st in list(self.stars):
            st["life"] -= dt
            st["x"] += st["vx"] * dt
            st["y"] += st["vy"] * dt
            st["l"].points = [st["x"], st["y"], st["x"] - st["vx"] * 0.12, st["y"] - st["vy"] * 0.12]
            st["c"].a = max(0.0, st["life"] / 0.9) * 0.9
            if st["life"] <= 0:
                self.canvas.remove(st["c"])
                self.canvas.remove(st["l"])
                self.stars.remove(st)


class FxFront(Widget):
    """Wierzch: konfetti, iskry, fale, błysk i neonowa ramka pulsująca w rytm."""

    def __init__(self, border=True, **kw):
        super().__init__(**kw)
        self.bits, self.rings = [], []
        self.border_on = border
        with self.canvas:
            self.flash_c = Color(*ACCENT[:3], 0)
            self.flash = Rectangle(texture=white_tex())
            self.bc = Color(*ACCENT[:3], 0)
            self.border = Line(width=dp(2.2))
        self.bind(pos=self._layout, size=self._layout)

    def _layout(self, *_):
        self.flash.pos, self.flash.size = self.pos, self.size
        self.border.rounded_rectangle = (self.x + dp(3), self.y + dp(3),
                                         max(self.width - dp(6), 1), max(self.height - dp(6), 1),
                                         dp(24))

    def burst(self, x, y, n=36, power=1.0, sparkle=False):
        if not ANIM["on"]:
            return
        cols = palette()
        for _ in range(n):
            ang, v = random.uniform(0, 6.283), dp(random.uniform(120, 420)) * power
            w0 = dp(random.uniform(2, 4)) if sparkle else dp(random.uniform(4, 8))
            h0 = w0 if sparkle else w0 * random.uniform(0.6, 1.5)
            shape = Ellipse if sparkle or random.random() < 0.4 else Rectangle
            g = InstructionGroup()
            c = Color(*random.choice(cols), 1)
            r = shape(texture=white_tex(), size=(w0, h0))
            g.add(c)
            g.add(r)
            self.canvas.add(g)
            life = random.uniform(0.5, 0.8) if sparkle else random.uniform(0.9, 1.5)
            self.bits.append({"x": x, "y": y, "vx": math.cos(ang) * v,
                              "vy": math.sin(ang) * v + (0 if sparkle else dp(120)),
                              "g": g, "c": c, "r": r, "w0": w0, "h0": h0, "life": life,
                              "max": life, "grav": 0 if sparkle else dp(620),
                              "spin": 0 if sparkle else random.uniform(4, 10)})

    def ring(self, x, y, maxr=None):
        if not ANIM["on"]:
            return
        g = InstructionGroup()
        c = Color(*ACCENT[:3], 0.7)
        ln = Line(circle=(x, y, 1), width=dp(2.5))
        g.add(c)
        g.add(ln)
        self.canvas.add(g)
        self.rings.append({"x": x, "y": y, "t": 0.0, "dur": 0.8, "g": g, "c": c, "l": ln,
                           "max": maxr or max(self.width, self.height) * 0.6})

    def update(self, dt, beat=0.0, playing=False):
        for b in list(self.bits):
            b["life"] -= dt
            if b["life"] <= 0:
                self.canvas.remove(b["g"])
                self.bits.remove(b)
                continue
            b["vy"] -= b["grav"] * dt
            b["vx"] *= 1 - min(0.9, 1.2 * dt)
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            b["c"].a = min(1.0, b["life"] / b["max"] * 1.6)
            w = b["w0"] * abs(math.cos(b["life"] * b["spin"])) + dp(1) if b["spin"] else b["w0"]
            b["r"].size = (w, b["h0"])
            b["r"].pos = (b["x"] - w / 2, b["y"] - b["h0"] / 2)
        for r in list(self.rings):
            r["t"] += dt
            k = r["t"] / r["dur"]
            if k >= 1:
                self.canvas.remove(r["g"])
                self.rings.remove(r)
                continue
            e = 1 - (1 - k) ** 3
            r["l"].circle = (r["x"], r["y"], dp(10) + e * r["max"])
            r["l"].width = dp(2.5) * (1 - k) + dp(0.5)
            r["c"].a = 0.7 * (1 - k)
        if self.flash_c.a > 0:
            self.flash_c.a = max(0.0, self.flash_c.a - dt * 0.4)
        if self.border_on and playing:
            self.bc.a = 0.12 + 0.55 * beat
        else:
            self.bc.a = max(0.0, self.bc.a - dt * 2)


class VinylDisc(Widget):
    """Płyta winylowa z okładką w środku; kręci się, gdy muzyka gra."""
    angle = NumericProperty(0)
    source = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas:
            PushMatrix()
            self._rot = Rotate(angle=0, origin=(0, 0))
            Color(0.05, 0.05, 0.06, 1)
            self._disc = Ellipse(texture=white_tex())
            self._grooves = []
            for i in range(7):
                Color(1, 1, 1, 0.035 + 0.01 * (i % 2))
                self._grooves.append(Line(circle=(0, 0, 1), width=1.1))
            self._cc = Color(*ACCENT_DIM)
            self._cover = Ellipse(texture=white_tex())
            Color(0.05, 0.05, 0.06, 1)
            self._hole = Ellipse(texture=white_tex())
            PopMatrix()
        self.bind(pos=self._upd, size=self._upd, angle=self._upd, source=self._src)

    def _src(self, *_):
        if self.source:
            self._cover.source = self.source
            self._cc.rgba = (1, 1, 1, 1)
        else:
            self._cover.texture = white_tex()
            self._cc.rgba = ACCENT_DIM
        self._upd()

    def _upd(self, *_):
        d = min(self.width, self.height)
        cx, cy = self.center
        r = d / 2
        self._disc.pos, self._disc.size = (cx - r, cy - r), (d, d)
        for i, g in enumerate(self._grooves):
            g.circle = (cx, cy, r * (0.66 + i * 0.045))
        rc = r * 0.6
        self._cover.pos, self._cover.size = (cx - rc, cy - rc), (rc * 2, rc * 2)
        rh = r * 0.05
        self._hole.pos, self._hole.size = (cx - rh, cy - rh), (rh * 2, rh * 2)
        self._rot.origin = (cx, cy)
        self._rot.angle = -self.angle


class QRWidget(Widget):
    """Kod QR z listy wierszy (True = czarny moduł)."""

    def __init__(self, matrix, **kw):
        super().__init__(**kw)
        self.matrix = matrix
        self.bind(pos=self.draw, size=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        n = len(self.matrix)
        side = min(self.width, self.height)
        cell = side / n
        x0 = self.center_x - side / 2
        y0 = self.center_y - side / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=(x0, y0), size=(side, side), texture=white_tex())
            Color(0, 0, 0, 1)
            for r, row in enumerate(self.matrix):
                for c, v in enumerate(row):
                    if v:
                        Rectangle(pos=(x0 + c * cell, y0 + (n - 1 - r) * cell),
                                  size=(cell + 0.5, cell + 0.5), texture=white_tex())


class ThemedSlider(Slider):
    pass


class TapImage(ButtonBehavior, AsyncImage):
    pass


class MsgLabel(Label):
    """Napis na przyciemnionym tle (czytelny na miniaturze)."""
    pass


class WordLabel(Label):
    """Pojedyncze słowo tekstu: obrót i skala do animacji."""
    angle = NumericProperty(0)
    wscale = NumericProperty(1)


class TrackRow(RecycleDataViewBehavior, BoxLayout):
    ox = NumericProperty(0)

    def refresh_view_attrs(self, rv, index, data):
        res = super().refresh_view_attrs(rv, index, data)
        app = App.get_running_app()
        if ANIM["on"] and app and time.time() < getattr(app, "stagger_until", 0):
            n = app.stagger_n
            app.stagger_n += 1
            Animation.cancel_all(self, "ox", "opacity")
            self.ox, self.opacity = dp(46) * app.stagger_dir, 0
            Clock.schedule_once(lambda dt: (
                Animation(ox=0, d=0.38, t="out_cubic").start(self),
                Animation(opacity=1, d=0.3).start(self)), min(n, 12) * 0.035)
        else:
            self.ox, self.opacity = 0, 1
        return res

    text = StringProperty("")
    sub = StringProperty("")
    side = StringProperty("+")
    idx = NumericProperty(0)
    current = BooleanProperty(False)


KV_BODY = """
<RoundButton,RoundToggle,RoundSpinner>:
    bg: CARD
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    color: BG if self.state == 'down' else TEXT
    font_size: '15sp'
    canvas.before:
        PushMatrix
        Scale:
            origin: self.center
            x: self.pscale
            y: self.pscale
        Color:
            rgba: ACCENT if self.state == 'down' else self.bg
        RoundedRectangle:
            pos: self.x + dp(3), self.y + dp(3)
            size: self.width - dp(6), self.height - dp(6)
            radius: [dp(14)]
    canvas.after:
        StencilPush
        RoundedRectangle:
            pos: self.x + dp(3), self.y + dp(3)
            size: self.width - dp(6), self.height - dp(6)
            radius: [dp(14)]
        StencilUse
        Color:
            rgba: 1, 1, 1, self.ripple_a
        Ellipse:
            pos: self.rx - self.ripple_r, self.ry - self.ripple_r
            size: self.ripple_r * 2, self.ripple_r * 2
        StencilUnUse
        RoundedRectangle:
            pos: self.x + dp(3), self.y + dp(3)
            size: self.width - dp(6), self.height - dp(6)
            radius: [dp(14)]
        StencilPop
        PopMatrix

<RoundSpinner>:
    option_cls: 'WarmOption'
    dropdown_cls: 'WarmDropDown'
    shorten: True
    text_size: self.width - dp(20), None
    halign: 'center'

<WarmDropDown>:
    auto_width: False
    width: dp(250)
    max_height: dp(560)
    bar_color: ACCENT_DIM
    canvas.before:
        Color:
            rgba: BG_POP
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(14)]

<WarmOption@SpinnerOption>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    height: dp(50)
    halign: 'left'
    valign: 'middle'
    padding: dp(20), 0
    text_size: self.size
    shorten: True
    canvas.before:
        Color:
            rgba: CARD_HI if self.state == 'down' else (0, 0, 0, 0)
        RoundedRectangle:
            pos: self.x + dp(4), self.y + dp(2)
            size: self.width - dp(8), self.height - dp(4)
            radius: [dp(10)]

<RoundInput>:
    background_normal: ''
    background_active: ''
    background_color: 0, 0, 0, 0
    foreground_color: TEXT
    hint_text_color: MUTED
    cursor_color: ACCENT
    padding: dp(14), dp(14)

<RoundPopup>:
    canvas.before:
        PushMatrix
        Translate:
            y: self.py
        Scale:
            origin: self.center
            x: self.pscale
            y: self.pscale
    canvas.after:
        PopMatrix
    background: ''
    background_color: BG_POP
    title_color: ACCENT
    title_size: '17sp'
    separator_color: ACCENT_DIM

<Label>:
    color: TEXT

<ThemedSlider>:
    cursor_size: 0, 0
    background_width: 0
    canvas.after:
        Color:
            rgba: CARD_HI
        RoundedRectangle:
            pos: self.x + self.padding, self.center_y - dp(2)
            size: self.width - 2 * self.padding, dp(4)
            radius: [dp(2)]
        Color:
            rgba: ACCENT
        RoundedRectangle:
            pos: self.x + self.padding, self.center_y - dp(2)
            size: max(self.value_pos[0] - self.x - self.padding, 0), dp(4)
            radius: [dp(2)]
        Ellipse:
            pos: self.value_pos[0] - dp(9), self.center_y - dp(9)
            size: dp(18), dp(18)

<MsgLabel>:
    canvas.before:
        Color:
            rgba: 0, 0, 0, 0.6 if self.text else 0
        Rectangle:
            pos: self.pos
            size: self.size

<TapImage>:
    color: (1, 1, 1, 1) if self.source else (0, 0, 0, 0)

<WordLabel>:
    canvas.before:
        PushMatrix
        Rotate:
            angle: self.angle
            origin: self.center
        Scale:
            origin: self.center
            x: self.wscale
            y: self.wscale
    canvas.after:
        PopMatrix

<TrackRow>:
    size_hint_y: None
    height: dp(66)
    spacing: dp(2)
    canvas.before:
        PushMatrix
        Translate:
            x: self.ox
    canvas.after:
        PopMatrix
    TrackMain:
        orientation: 'vertical'
        padding: dp(18), dp(10)
        bg: ACCENT_DIM if root.current else CARD
        on_release: app.play_index(root.idx)
        canvas.before:
            PushMatrix
            Scale:
                origin: self.center
                x: self.pscale
                y: self.pscale
            Color:
                rgba: CARD_HI if self.state == 'down' else self.bg
            RoundedRectangle:
                pos: self.x + dp(3), self.y + dp(3)
                size: self.width - dp(6), self.height - dp(6)
                radius: [dp(14)]
        canvas.after:
            StencilPush
            RoundedRectangle:
                pos: self.x + dp(3), self.y + dp(3)
                size: self.width - dp(6), self.height - dp(6)
                radius: [dp(14)]
            StencilUse
            Color:
                rgba: 1, 1, 1, self.ripple_a
            Ellipse:
                pos: self.rx - self.ripple_r, self.ry - self.ripple_r
                size: self.ripple_r * 2, self.ripple_r * 2
            StencilUnUse
            RoundedRectangle:
                pos: self.x + dp(3), self.y + dp(3)
                size: self.width - dp(6), self.height - dp(6)
                radius: [dp(14)]
            StencilPop
            PopMatrix
        Label:
            text: root.text
            font_size: '15sp'
            color: TEXT
            shorten: True
            shorten_from: 'right'
            text_size: self.width, None
            halign: 'left'
            valign: 'middle'
        Label:
            text: root.sub
            font_size: '12sp'
            color: MUTED
            shorten: True
            shorten_from: 'right'
            text_size: self.width, None
            halign: 'left'
            valign: 'middle'
            size_hint_y: 0.75 if root.sub else 0.001
            opacity: 1 if root.sub else 0
    RoundButton:
        text: root.side
        size_hint_x: None
        width: dp(54) if root.side else 0
        opacity: 1 if root.side else 0
        disabled: not root.side
        bg: CARD_HI
        on_release: app.side_action(root.idx)

BoxLayout:
    orientation: 'vertical'
    padding: dp(6)
    spacing: dp(2)
    canvas.before:
        Color:
            rgba: app.tint
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        size_hint_y: None
        height: dp(54)
        RoundSpinner:
            text: 'Biblioteka'
            values: app.view_names
            size_hint_x: 0.38
            on_text: app.set_view(self.text)
        RoundInput:
            id: search
            hint_text: 'Szukaj w bibliotece'
            multiline: False
            on_text: app.refresh()
            on_text_validate: app.show_global_search(self.text)
        RoundButton:
            text: 'Mów'
            size_hint_x: None
            width: dp(60)
            on_release: app.voice_search()
    BoxLayout:
        size_hint_y: None
        height: dp(52)
        RoundButton:
            text: 'YouTube'
            bg: ACCENT_DIM
            on_release: app.show_youtube()
        RoundButton:
            text: 'Radio'
            bg: ACCENT_DIM
            on_release: app.show_radio()
        RoundButton:
            id: dl_btn
            text: app.dl_label
            bg: ACCENT if app.dl_label != 'Pobrane' else CARD
            color: BG if app.dl_label != 'Pobrane' else TEXT
            on_release: app.show_downloads()
            canvas.after:
                Color:
                    rgba: (BG[0], BG[1], BG[2], 0.55 if app.dl_label != 'Pobrane' else 0)
                RoundedRectangle:
                    pos: self.x + dp(12), self.y + dp(8)
                    size: (self.width - dp(24)) * app.dl_frac, dp(3)
                    radius: [dp(2)]
        RoundButton:
            text: 'Więcej'
            on_release: app.show_more()
    RecycleView:
        id: rv
        viewclass: 'TrackRow'
        bar_color: ACCENT_DIM
        opacity: app.list_alpha
        canvas.before:
            PushMatrix
            Translate:
                y: -app.list_shift
        canvas.after:
            PopMatrix
        RecycleBoxLayout:
            default_size: None, dp(66)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'
    Label:
        text: app.status
        opacity: app.status_alpha
        size_hint_y: None
        height: dp(24)
        font_size: '12sp'
        color: MUTED
        shorten: True
        text_size: self.width - dp(16), None
        halign: 'center'
    VizBars:
        id: viz
        size_hint_y: None
        height: dp(36) * app.mini_k * app.viz_k
        opacity: app.mini_k * app.viz_k
    SwipeArea:
        id: np
        size_hint_y: None
        height: dp(70)
        opacity: app.np_alpha
        canvas.before:
            PushMatrix
            Translate:
                x: app.np_shift
            Color:
                rgba: ACCENT[0], ACCENT[1], ACCENT[2], app.glow_a
            RoundedRectangle:
                pos: self.x + dp(2), self.y + dp(2)
                size: self.width - dp(4), self.height - dp(4)
                radius: [dp(18)]
        canvas.after:
            PopMatrix
        spacing: dp(8)
        padding: dp(6), 0
        AsyncImage:
            source: app.cover
            opacity: 1 if app.cover else 0
            canvas.before:
                PushMatrix
                Scale:
                    origin: self.center
                    x: app.cover_k
                    y: app.cover_k
            canvas.after:
                PopMatrix
            size_hint_x: None
            width: dp(64) if app.cover else 0
            fit_mode: 'contain'
        BoxLayout:
            orientation: 'vertical'
            padding: 0, dp(8)
            Label:
                text: app.now_text
                bold: True
                font_size: '16sp'
                color: ACCENT
                shorten: True
                shorten_from: 'right'
                text_size: self.width, None
                halign: 'left' if app.cover else 'center'
            Label:
                text: app.now_sub
                font_size: '13sp'
                color: MUTED
                shorten: True
                shorten_from: 'right'
                text_size: self.width, None
                halign: 'left' if app.cover else 'center'
                size_hint_y: 0.8 if app.now_sub else 0.001
    BoxLayout:
        size_hint_y: None
        height: dp(36) * app.mini_k
        opacity: app.mini_k
        disabled: app.mini
        Label:
            text: app.pos_text
            color: MUTED
            size_hint_x: None
            width: dp(56)
        Slider:
            min: 0
            max: app.dur
            value: app.pos
            cursor_size: 0, 0
            background_width: 0
            on_touch_up: if self.collide_point(*args[1].pos): app.seek(self.value)
            canvas.after:
                Color:
                    rgba: CARD_HI
                RoundedRectangle:
                    pos: self.x + self.padding, self.center_y - dp(2)
                    size: self.width - 2 * self.padding, dp(4)
                    radius: [dp(2)]
                Color:
                    rgba: ACCENT
                RoundedRectangle:
                    pos: self.x + self.padding, self.center_y - dp(2)
                    size: max(self.value_pos[0] - self.x - self.padding, 0), dp(4)
                    radius: [dp(2)]
                Ellipse:
                    pos: self.value_pos[0] - dp(8), self.center_y - dp(8)
                    size: dp(16), dp(16)
        Label:
            text: app.dur_text
            color: MUTED
            size_hint_x: None
            width: dp(56)
    BoxLayout:
        size_hint_y: None
        height: dp(52) * app.mini_k
        opacity: app.mini_k
        disabled: app.mini
        RoundButton:
            id: fav_btn
            text: 'Lubię'
            bg: ACCENT if app.is_fav else CARD
            color: BG if app.is_fav else TEXT
            on_release: app.toggle_fav()
        RoundToggle:
            text: 'Shuffle'
            on_state: app.set_shuffle(self.state == 'down')
        RoundButton:
            text: app.repeat_label
            bg: CARD if app.repeat_label == 'Powt. -' else ACCENT_DIM
            on_release: app.cycle_repeat()
        RoundButton:
            text: app.timer_label
            bg: ACCENT_DIM if app.timer_label != 'Wyłącznik' else CARD
            on_release: app.ask_timer()
    BoxLayout:
        size_hint_y: None
        height: dp(64)
        RoundButton:
            text: '|<'
            on_release: app.prev()
        RoundButton:
            text: app.play_label
            bg: ACCENT_DIM
            on_release: app.toggle()
        RoundButton:
            text: '>|'
            on_release: app.next()
        RoundButton:
            text: app.speed_label
            size_hint_x: 0.8
            bg: CARD if app.speed_label == '1.0x' else ACCENT_DIM
            on_release: app.cycle_speed()
        RoundButton:
            text: 'Tekst'
            size_hint_x: 0.8
            on_release: app.show_lyrics()
"""


def make_kv():
    g = globals()
    return "".join(f"#:set {k} {tuple(g[k])}\n" for k in THEME_KEYS) + KV_BODY


# ---------------------------------------------------------------- aplikacja
Window.clearcolor = BG                          # bez białego błysku przy starcie


class MuzykaApp(App):
    now_text = StringProperty("Leox Player")
    status = StringProperty("")
    pos = NumericProperty(0)
    dur = NumericProperty(1)
    pos_text = StringProperty("0:00")
    dur_text = StringProperty("0:00")
    play_label = StringProperty("Play")
    SPECIAL = ("Biblioteka", "Ulubione", "Historia", "Kolejka", "Wykonawcy", "Albumy",
               "Ostatnio pobrane", "Nigdy nie grane", "Miks na dziś", "Duplikaty")
    view_names = ListProperty(list(SPECIAL))
    dl_label = StringProperty("Pobrane")
    now_sub = StringProperty("")
    list_shift = NumericProperty(0)
    list_alpha = NumericProperty(1)
    np_shift = NumericProperty(0)
    np_alpha = NumericProperty(1)
    mini_k = NumericProperty(1)
    viz_k = NumericProperty(0)
    status_alpha = NumericProperty(1)
    dl_frac = NumericProperty(0)
    cover_k = NumericProperty(1)
    tint = ListProperty([0, 0, 0, 0])
    glow_a = NumericProperty(0)
    current_view = StringProperty("Biblioteka")
    mini = BooleanProperty(False)
    viz = BooleanProperty(False)
    is_fav = BooleanProperty(False)
    timer_label = StringProperty("Wyłącznik")
    repeat_label = StringProperty("Powt. -")
    speed_label = StringProperty("1.0x")
    cover = StringProperty("")
    SPEEDS = (0.75, 1.0, 1.25, 1.5, 2.0)
    REPEAT = {"off": "Powt. -", "all": "Powt. wsz.", "one": "Powt. 1"}

    def build(self):
        self.title = "Leox Player"
        threading.Thread(target=patch_ytdlp, daemon=True).start()
        Clock.schedule_once(lambda dt: self.online_start(), 1.5)
        request_perms()
        Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
        setup_font(Path(self.user_data_dir) / "fonts")
        self.dl_dir = self.pick_download_dir()
        self.export_dir = self.dl_dir.parent
        dirs = [MUSIC_DIR]
        if MUSIC_DIR not in self.dl_dir.parents:
            dirs.append(self.dl_dir)
        self.lib = Library(Path(self.user_data_dir) / "library.db", dirs)
        apply_theme(self.lib.get_setting("motyw", "Ciepły"))
        Window.clearcolor = BG
        self.apk = self.apk_build = service_available()
        self.player = RemotePlayer(self.on_remote) if self.apk else Player()
        self.player.eq_preset = int(self.lib.get_setting("eq", "-1"))
        self.player.bass = int(self.lib.get_setting("bas", "0"))
        try:
            self.player.eq_bands = json.loads(self.lib.get_setting("eq_bands", "[]"))
        except ValueError:
            self.player.eq_bands = []
        self.cast, self.cast_track, self.cast_started, self.cast_end_handled = None, 0, 0.0, False
        self.cast_paused, self.web, self.shake, self._voice_bound = False, None, None, False
        self.theme_now = resolve_theme(self.lib.get_setting("motyw", "Ciepły"))
        self.in_bg, self.bg_changed, self.pending_stream, self.remote_t = False, False, None, 0.0
        if self.apk:
            self.player.apply_fx()
            Clock.schedule_once(lambda dt: self.player.cmd(cmd="hello"), 1.0)
            Clock.schedule_once(self.check_service, 12)
        else:
            self.player.on_done = self.bg_done
        self.view, self.pl_id, self.group = "Biblioteka", None, None
        self.items, self.queue, self.qi = [], [], -1
        self.active, self.loaded_at, self.shuffle = False, 0.0, False
        self.sleep_at, self.sleep_end_track = None, False
        self.repeat, self.stream_token, self.last_pos_save = "off", None, 0.0
        self.alarm_at, self.fade_in_start = None, None
        self.dl_jobs, self.dl_running, self.dl_lock = [], False, threading.Lock()
        self.cover_dir = Path(self.user_data_dir) / "okladki"
        self.cover_dir.mkdir(exist_ok=True)
        self.viz = self.lib.get_setting("wizualizacja", "0") == "1"
        self.viz_k = 1 if self.viz else 0
        ANIM["on"] = self.lib.get_setting("animacje", "1") == "1"
        self._dir = 1
        self.ly = None
        self.energy = self.energy_avg = self.beat = 0.0
        self.last_beat, self.fx_t = 0.0, 0.0
        self.fx_back = self.fx_front = None
        self.xf, self.xf_started = int(self.lib.get_setting("przejscie", "0")), False
        self.wake = WakeLock()
        self.party, self.party_url = None, ""
        self.bind(status=self._status_anim)
        self.bind(now_text=lambda *a: setattr(self, "now_sub", ""))
        self.bind(cover=self.update_tint)
        Clock.schedule_interval(self.check_auto_theme, 300)
        root = Builder.load_string(make_kv(), filename="muzyka_ui.kv")
        Clock.schedule_interval(self.tick, 0.5)
        Clock.schedule_interval(self.viz_tick, 1 / 15)
        Clock.schedule_interval(self.fx_tick, 1 / 30)
        Clock.schedule_once(lambda dt: self.scan(), 0.5)
        Clock.schedule_interval(self.autobackup, 30)
        Clock.schedule_once(self.ask_all_files, 2)
        if self.lib.get_setting("auto_nowosci", "0") == "1":
            Clock.schedule_once(lambda dt: self.auto_news(), 8)
        return root

    def pick_download_dir(self):
        for d in (MUSIC_DIR / "Pobrane", Path(self.user_data_dir) / "Pobrane"):
            try:
                d.mkdir(parents=True, exist_ok=True)
                t = d / ".test_zapisu.m4a"
                t.write_text("x")
                t.unlink()
                return d
            except OSError:
                continue
        return Path(self.user_data_dir)

    # --- lista utworów
    def refresh(self, *_):
        if not self.root:
            return
        cur = self.current_path()
        names = list(self.SPECIAL) + [n for _, n in self.lib.playlists()]
        if self.view == "Kolejka":
            self.items = list(self.queue)
            self.root.ids.rv.data = [
                {"text": f"{i + 1}.  {r[1] or '?'}", "sub": self.sub_line(r), "idx": i,
                 "current": self.active and i == self.qi, "side": "x"}
                for i, r in enumerate(self.items)]
            self.view_names = names
            return
        q = self.root.ids.search.text.casefold()
        if self.view in ("Wykonawcy", "Albumy") and self.group is None:
            groups = self.lib.artists() if self.view == "Wykonawcy" else self.lib.albums()
            if q:
                groups = [g for g in groups if q in g[0].casefold()]
            self.items = [("__group__", g) for g, _ in groups]
            self.root.ids.rv.data = [
                {"text": "Nieznany wykonawca" if g == "?" else g, "sub": f"{n} utw.",
                 "idx": i, "current": False, "side": "Graj"}
                for i, (g, n) in enumerate(groups)]
            self.view_names = names
            return
        v = self.view
        if v == "Biblioteka":
            rows = self.lib.tracks()
        elif v == "Ulubione":
            rows = self.lib.favorites()
        elif v == "Historia":
            rows = self.lib.history()
        elif v == "Wykonawcy":
            rows = self.lib.by_artist(self.group)
        elif v == "Albumy":
            rows = self.lib.by_album(self.group)
        elif v == "Ostatnio pobrane":
            rows = self.lib.recent()
        elif v == "Nigdy nie grane":
            rows = self.lib.never_played()
        elif v == "Miks na dziś":
            rows = self.lib.daily_mix()
        elif v == "Duplikaty":
            rows = self.lib.duplicates()
        else:
            rows = self.lib.playlist_tracks(self.pl_id)
        if q:
            rows = [r for r in rows
                    if q in " ".join(x or "" for x in r[1:4]).casefold()]
        data = [{"text": r[1] or "?", "sub": self.sub_line(r), "current": r[0] == cur,
                 "side": "..."} for r in rows]
        items = list(rows)
        if self.group is not None:
            items.insert(0, ("__back__",))
            data.insert(0, {"text": "< Wróć", "sub": self.group, "current": False, "side": ""})
        for i, d in enumerate(data):
            d["idx"] = i
        self.items = items
        self.root.ids.rv.data = data
        self.view_names = names

    @staticmethod
    def sub_line(r):
        return f"{r[2] or 'Nieznany wykonawca'}    {fmt(r[4])}"

    def animate_list(self, direction=1):
        self.stagger_until, self.stagger_n, self.stagger_dir = time.time() + 0.5, 0, direction
        if ANIM["on"]:
            self.list_alpha = 0.3
        anim(self, d=0.25, list_alpha=1)

    def _status_anim(self, *_):
        if ANIM["on"]:
            self.status_alpha = 0
            anim(self, d=0.35, status_alpha=1)

    def set_view(self, name):
        self.current_view = name
        self.animate_list()
        self.view, self.pl_id, self.group = name, None, None
        if name not in self.SPECIAL:
            self.pl_id = next((i for i, n in self.lib.playlists() if n == name), None)
            if self.pl_id is None:
                self.view = "Biblioteka"
        self.refresh()

    def group_tracks(self, name):
        return self.lib.by_artist(name) if self.view == "Wykonawcy" else self.lib.by_album(name)

    def side_action(self, i):
        if self.view == "Kolejka":
            self.queue_remove(i)
            return
        t = self.items[i]
        if t[0] == "__back__":
            return
        if t[0] == "__group__":
            rows = list(self.group_tracks(t[1]))
            if rows:
                if self.shuffle:
                    random.shuffle(rows)
                self.queue, self.qi = rows, 0
                self.play_current()
            return
        rows = [
            {"text": "Zagraj jako następny", "tap": lambda b: self.queue_add(t, True)},
            {"text": "Dodaj na koniec kolejki", "tap": lambda b: self.queue_add(t, False)},
            {"text": "Dodaj do playlisty", "tap": lambda b: self.ask(
                "Playlista (nowa lub istniejąca)",
                lambda name: self.add_to_playlist(name, t[0]))},
            {"text": "Edytuj tytuł i wykonawcę", "tap": lambda b: self.edit_tags(t)},
            {"text": "Uzupełnij tagi i okładkę (MusicBrainz)", "tap": lambda b: self.mb_track(t)},
            {"text": "Radio z utworu (podobne z YouTube)", "tap": lambda b: self.radio_from(t)},
            {"text": "Udostępnij", "tap": lambda b: self.share_track(t)},
        ]
        if self.view == "Ulubione":
            rows.append({"text": "Usuń z ulubionych", "tap": lambda b: (
                self.lib.set_fav(t[0], False), self.update_fav(), self.refresh())})
        elif self.view not in self.SPECIAL:
            rows.append({"text": "Usuń z playlisty", "tap": lambda b: (
                self.lib.remove_from_playlist(self.pl_id, t[0]), self.refresh())})
        rows.append({"text": "Usuń plik z telefonu", "tap": lambda b: self.confirm_delete(t)})
        self.list_popup(f"{t[2] or '?'} - {t[1]}", rows)

    def add_to_playlist(self, name, path):
        if name in self.SPECIAL:
            self.set_status("Ta nazwa jest zarezerwowana")
            return
        self.lib.add_to_playlist(name, path)
        self.set_status(f"Dodano do: {name}")
        self.refresh()

    # --- kolejka
    def queue_add(self, track, next_):
        if not self.active and not self.stream_token:
            self.queue, self.qi = [track], 0
            self.play_current()
            return
        pos = self.qi + 1 if next_ else len(self.queue)
        self.queue.insert(pos, track)
        self.sync_queue()
        self.set_status("Zagra jako następny" if next_ else "Dodano do kolejki")
        self.refresh()

    def queue_remove(self, i):
        if i == self.qi:
            self.set_status("Nie można usunąć granego utworu")
            return
        del self.queue[i]
        if i < self.qi:
            self.qi -= 1
        self.sync_queue()
        self.refresh()

    def cycle_repeat(self):
        order = ["off", "all", "one"]
        self.repeat = order[(order.index(self.repeat) + 1) % 3]
        self.repeat_label = self.REPEAT[self.repeat]
        if self.apk:
            self.player.cmd(cmd="set", repeat=self.repeat)

    def cycle_speed(self):
        cur = self.player.speed
        i = self.SPEEDS.index(cur) if cur in self.SPEEDS else 1
        sp = self.SPEEDS[(i + 1) % len(self.SPEEDS)]
        self.player.set_speed(sp)
        self.speed_label = f"{sp}x"
        if not self.player.PP:
            self.set_status("Zmiana prędkości działa tylko na Androidzie")

    # --- ulubione
    def current_path(self):
        return self.queue[self.qi][0] if self.active else None

    @staticmethod
    def is_stream(path):
        return bool(path) and (path.startswith("http") or path.startswith("radio:"))

    @staticmethod
    def is_youtube(path):
        return bool(path) and path.startswith("http") and (
            "youtube.com" in path or "youtu.be" in path)

    @staticmethod
    def is_radio(path):
        return bool(path) and path.startswith("radio:")

    def keeps_position(self, path):
        """Pozycję pamiętamy dla plików i podcastów, nie dla YouTube i radia."""
        return bool(path) and not self.is_youtube(path) and not self.is_radio(path)

    def update_fav(self):
        p = self.current_path()
        self.is_fav = bool(p) and not self.is_stream(p) and self.lib.is_fav(p)

    def toggle_fav(self):
        p = self.current_path()
        if not p:
            self.set_status("Nic nie gra")
            return
        if self.is_stream(p):
            self.set_status("Pobierz utwór, aby dodać go do ulubionych")
            return
        self.lib.set_fav(p, not self.lib.is_fav(p))
        self.update_fav()
        self.set_status("Dodano do ulubionych" if self.is_fav else "Usunięto z ulubionych")
        if self.is_fav:
            self.fx_at("fav_btn", "fav")
        if self.view == "Ulubione":
            self.refresh()

    # --- wyłącznik czasowy
    def ask_timer(self):
        rows = [{"text": f"{m} min", "tap": lambda b, m=m: self.set_timer(m)}
                for m in (15, 30, 45, 60, 90)]
        rows.append({"text": "Po tym utworze", "tap": lambda b: self.set_timer_track()})
        footer = ([("Wyłącz", lambda b: self.cancel_timer())]
                  if self.sleep_at or self.sleep_end_track else [])
        self.list_popup("Wyłącznik czasowy", rows, footer)

    def set_timer(self, minutes):
        self.sleep_at, self.sleep_end_track = time.time() + minutes * 60, False
        self.player.set_volume(1.0)
        self.set_status(f"Wyłącznik: za {minutes} min")

    def set_timer_track(self):
        self.sleep_at, self.sleep_end_track = None, True
        self.player.set_volume(1.0)
        self.timer_label = "Wył. po utworze"
        if self.apk:
            self.player.cmd(cmd="stop_after", on=True)
        self.set_status("Wyłącznik: po tym utworze")

    def cancel_timer(self):
        self.sleep_at, self.sleep_end_track = None, False
        if self.apk:
            self.player.cmd(cmd="stop_after", on=False)
        self.player.set_volume(1.0)
        self.timer_label = "Wyłącznik"
        self.set_status("Wyłącznik anulowany")

    def tick_timer(self):
        if self.sleep_at is None:
            return
        left = self.sleep_at - time.time()
        if left <= 0:
            self.sleep_at = None
            self.timer_label = "Wyłącznik"
            if self.active and not self.player.paused:
                self.toggle()
            self.player.set_volume(1.0)
            self.set_status("Wyłącznik czasowy: pauza")
            return
        self.timer_label = f"Wył. {fmt(left)}"
        if self.active and left <= 15:          # wyciszanie przez ostatnie 15 s
            self.player.set_volume(left / 15)

    # --- odtwarzanie
    def play_index(self, i):
        if self.view == "Kolejka":
            self.qi = i
            self.play_current()
            return
        it = self.items[i]
        if it[0] == "__group__":
            self.group = it[1]
            self.animate_list()
            self.refresh()
            return
        if it[0] == "__back__":
            self.group = None
            self.animate_list(-1)
            self.refresh()
            return
        q = [x for x in self.items if not x[0].startswith("__")]
        i -= len(self.items) - len(q)
        if self.shuffle:
            first = q.pop(i)
            random.shuffle(q)
            self.queue, self.qi = [first] + q, 0
        else:
            self.queue, self.qi = q, i
        self.play_current()

    def play_current(self, fade=0):
        t = self.queue[self.qi]
        if self.cast:
            self.cast_play(t)
            return
        if self.apk:
            self.play_remote(t, fade)
            return
        self.player.gain = 1.0
        if self.is_stream(t[0]):
            self.start_stream(t)
            return
        self.stream_token = None
        if self.lib.get_setting("wyrownaj", "0") == "1":
            self.player.gain = replaygain(t[0])
        try:
            self.player.load(t[0], fade=fade)
        except Exception as e:
            self.active = False
            self.set_status(f"Błąd odtwarzania: {e}")
            return
        self.after_start(t)

    def after_start(self, t, cover=None):
        self.active, self.loaded_at = True, time.time()
        self.xf_started = False
        self.now_text = t[1] or "?"
        self.now_sub = t[2] or ""
        if ANIM["on"]:
            self.np_shift, self.np_alpha = dp(60) * self._dir, 0
            anim(self, d=0.4, np_shift=0, np_alpha=1)
        self._dir = 1
        self.play_label = "Pauza"
        if cover is not None and cover.startswith("http"):
            self.cover = ""
            want = t[0]
            self.net_image(cover, None, lambda p: self.current_path() == want
                           and setattr(self, "cover", p))
        elif cover is not None:
            self.cover = cover
        else:
            self.cover = ""
            self.load_cover(t[0])
        if not self.is_stream(t[0]):
            self.lib.add_history(t[0])
        if self.keeps_position(t[0]) and not self.cast:
            saved = self.lib.get_pos(t[0])
            if saved > 15 and self.player.duration() > 600:
                self.player.seek(saved)
                self.set_status(f"Wznowiono od {fmt(saved)}")
        self.update_fav()
        self.refresh()
        self.pulse_start()
        Clock.schedule_once(lambda dt: self.fx_at("np", "track"), 0.15)

    def pulse_start(self):
        """Okładka wskakuje, potem delikatnie 'oddycha' razem z poświatą."""
        self.wake.set(True)
        Animation.cancel_all(self, "cover_k", "glow_a")
        if not ANIM["on"]:
            self.cover_k, self.glow_a = 1, 0.08
            return
        self.cover_k, self.glow_a = 0.6, 0.25
        pop = Animation(cover_k=1, glow_a=0.08, d=0.5, t="out_back")

        def breathe(*_):
            loop = (Animation(cover_k=1.05, glow_a=0.14, d=1.6, t="in_out_sine") +
                    Animation(cover_k=1.0, glow_a=0.06, d=1.6, t="in_out_sine"))
            loop.repeat = True
            loop.start(self)
        pop.bind(on_complete=breathe)
        pop.start(self)

    def pulse_stop(self):
        self.wake.set(False)
        Animation.cancel_all(self, "cover_k", "glow_a")
        anim(self, d=0.4, cover_k=1, glow_a=0)

    def start_stream(self, t):
        token = object()
        self.stream_token = token
        self.player.stop()
        self.active = False
        self.now_text = f"Wczytywanie: {t[1]}"
        self.play_label = "Play"
        path = t[0]

        def work():
            info = {}
            if self.is_radio(path):
                src = path[len("radio:"):]
            elif self.is_youtube(path):
                return self.yt_prepare(path)
            else:
                src = path                        # podcast lub bezpośredni link
            return info, self.player.prepare(src)

        def done(res):
            if self.stream_token is not token:      # użytkownik wybrał coś innego
                if not isinstance(res, Exception):
                    res[1].release()
                return
            self.stream_token = None
            if isinstance(res, Exception):
                self.now_text = "Nic nie gra"
                self.show_error(res, "Błąd odtwarzania")
                return
            info, mp = res
            self.player.attach(mp)
            if info.get("id"):
                cover = f"https://i.ytimg.com/vi/{info['id']}/hqdefault.jpg"
            else:
                cover = t[3] if str(t[3]).startswith("http") else ""
            self.after_start(t, cover=cover)
        self.run_bg(work, done)

    def yt_prepare(self, url):
        """Gotowy odtwarzacz dla YouTube: najpierw strumień z nagłówkami,
        a gdy Android go odrzuci - pobranie dźwięku do pamięci tymczasowej."""
        import yt_dlp
        opts = {"quiet": True, "logger": QUIET, "no_warnings": True, "noplaylist": True,
                "format": FORMATS["najlepsza"]}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if info.get("url"):
            try:
                return info, self.player.prepare(info["url"], info.get("http_headers"))
            except Exception:
                pass
        tmp = Path(self.user_data_dir) / "strumien"
        tmp.mkdir(exist_ok=True)
        old = sorted(tmp.iterdir(), key=lambda f: f.stat().st_mtime)
        for f in old[:-3]:                       # zostaw tylko 3 ostatnie
            try:
                f.unlink()
            except OSError:
                pass
        with yt_dlp.YoutubeDL(dict(opts, outtmpl=str(tmp / "%(id)s.%(ext)s"))) as ydl:
            info = ydl.extract_info(url, download=True)
        return info, self.player.prepare(info["requested_downloads"][0]["filepath"])

    def play_now(self, t):
        """Wstawia pozycję zaraz za bieżącą i od razu ją gra."""
        if self.active:
            self.queue.insert(self.qi + 1, t)
            self.qi += 1
        else:
            self.queue, self.qi = [t], 0
        self.play_current()

    # --- sterowanie usługą (APK)
    def sync_queue(self, play=False, fade=0, gain=1.0):
        if not self.apk:
            return
        f = Path(self.user_data_dir) / "kolejka.json"
        f.write_text(json.dumps([list(x) for x in self.queue]), encoding="utf-8")
        self.player.cmd(cmd="play" if play else "queue", queue_file=str(f), index=self.qi,
                        fade=fade, gain=gain, repeat=self.repeat, xf=self.xf)

    def play_remote(self, t, fade):
        gain = 1.0
        if not self.is_stream(t[0]) and self.lib.get_setting("wyrownaj", "0") == "1":
            gain = replaygain(t[0])
        self.player.paused = False
        self.player.st.update(pos=0.0, dur=float(t[4] or 0), playing=True, t=time.time())
        self.remote_t = time.time()
        self.sync_queue(play=True, fade=fade, gain=gain)
        if self.is_stream(t[0]):
            self.pending_stream = t
            self.now_text = f"Wczytywanie: {t[1]}"
            self.play_label = "Play"
        else:
            self.pending_stream = None
            self.after_start(t)

    def stream_cover(self, t):
        if self.is_youtube(t[0]):
            m = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", t[0])
            return f"https://i.ytimg.com/vi/{m.group(1)}/hqdefault.jpg" if m else ""
        if self.is_stream(t[0]):
            return t[3] if str(t[3]).startswith("http") else ""
        return None

    def check_service(self, *_):
        """Usługa w tle nie odpowiedziała - gramy w samej aplikacji."""
        if not self.apk or self.player.alive:
            return
        rp = self.player
        self.apk = False
        self.player = Player()
        self.player.eq_preset, self.player.bass, self.player.eq_bands = rp.eq_preset, rp.bass, rp.eq_bands
        self.player.on_done = self.bg_done
        self.set_status("Odtwarzanie w tle niedostępne - gram w aplikacji")
        if any(k.get("cmd") == "play" for k in rp.pending) and 0 <= self.qi < len(self.queue):
            self.play_current()

    def on_remote(self, msg):
        """Wiadomości z usługi odtwarzania."""
        ev = msg.get("event")
        i = msg.get("index", -1)
        if ev == "started" and 0 <= i < len(self.queue):
            self.player.st.update(pos=0.0, t=time.time())
            if i != self.qi or self.pending_stream is not None or not self.active:
                self.qi, self.pending_stream = i, None
                self.after_start(self.queue[i], cover=self.stream_cover(self.queue[i]))
        elif ev == "error":
            self.pending_stream = None
            self.now_text = "Nic nie gra"
            self.show_error(RuntimeError(msg.get("msg", "")), "Błąd odtwarzania")
        elif ev == "ended":
            self.active, self.is_fav, self.play_label = False, False, "Play"
            self.now_text = {"timer": "Wyłącznik czasowy: koniec",
                             "quit": "Leox Player"}.get(msg.get("reason"), "Koniec kolejki")
            if msg.get("reason") == "timer":
                self.sleep_end_track, self.timer_label = False, "Wyłącznik"
            self.pulse_stop()
            self.refresh()
        elif ev == "state":                     # aplikacja uruchomiona ponownie, usługa gra dalej
            if self.queue or not msg.get("queue_file") or not msg.get("active"):
                return
            try:
                q = json.loads(Path(msg["queue_file"]).read_text(encoding="utf-8"))
            except Exception:
                return
            self.queue = [tuple(x) for x in q]
            if 0 <= i < len(self.queue):
                self.qi = i
                self.after_start(self.queue[i], cover=self.stream_cover(self.queue[i]))
                if msg.get("paused"):
                    self.player.paused = True
                    self.play_label = "Play"
                    self.pulse_stop()
        elif ev == "status":
            if self.active and time.time() - self.player.last_toggle > 1.5:
                want = "Play" if self.player.paused else "Pauza"
                if self.play_label != want:           # pauza/wznowienie z powiadomienia
                    self.play_label = want
                    self.pulse_stop() if self.player.paused else self.pulse_start()
            # zapasowa synchronizacja numeru utworu
            if (self.active and i != self.qi and 0 <= i < len(self.queue)
                    and not msg.get("loading") and time.time() - self.remote_t > 3):
                self.qi = i
                self.after_start(self.queue[i], cover=self.stream_cover(self.queue[i]))

    def bg_done(self):
        """Pydroid: utwór skończył się, gdy aplikacja była w tle - gramy następny."""
        if not self.in_bg or not self.active:
            return
        if self.sleep_end_track:
            self.player.stop()
            self.bg_changed = True
            return
        if self.repeat == "one":
            nxt = self.qi
        elif self.qi + 1 < len(self.queue):
            nxt = self.qi + 1
        else:
            nxt = 0 if self.repeat == "all" else None
        if nxt is None or self.is_stream(self.queue[nxt][0]):
            return
        try:
            self.player.load(self.queue[nxt][0])
        except Exception:
            return
        self.qi, self.bg_changed = nxt, True

    def on_resume(self):
        self.in_bg = False
        if time.time() - getattr(self, "last_scan", 0) > 20:
            Clock.schedule_once(lambda dt: self.scan(), 0.3)   # nowe pliki, przyznany dostęp
        if self.bg_changed and not self.apk:
            self.bg_changed = False
            if self.sleep_end_track:
                self.sleep_end_track, self.active = False, False
                self.play_label, self.now_text = "Play", "Wyłącznik czasowy: koniec"
                self.timer_label = "Wyłącznik"
                self.refresh()
            elif 0 <= self.qi < len(self.queue):
                self.after_start(self.queue[self.qi])

    def quit_background(self):
        if self.apk:
            self.player.cmd(cmd="quit")
            self.active, self.play_label, self.now_text = False, "Play", "Leox Player"
            self.pulse_stop()
            self.set_status("Odtwarzacz w tle zamknięty")

    def stream(self, v):
        self.play_now((v["url"], v["title"], v["channel"], "YouTube", v["dur"]))

    def next(self, auto=False, fade=0):
        if auto:
            p = self.current_path()
            if self.keeps_position(p):
                self.lib.set_pos(p, 0)        # dosłuchane do końca
        if auto and self.sleep_end_track:
            self.sleep_end_track = False
            self.timer_label = "Wyłącznik"
            self.player.stop()
            self.active, self.is_fav = False, False
            self.play_label, self.now_text = "Play", "Wyłącznik czasowy: koniec"
            self.refresh()
            return
        if auto and self.repeat == "one":
            self.play_current(fade)
            return
        if self.qi + 1 < len(self.queue):
            self.qi += 1
            self.play_current(fade)
        elif self.repeat == "all" and self.queue:
            self.qi = 0
            self.play_current(fade)
        else:
            self.player.stop()
            self.active = False
            self.play_label, self.now_text = "Play", "Koniec kolejki"
            self.wake.set(False)
            self.is_fav = False
            self.refresh()

    def cur_position(self):
        if self.cast:
            return self.cast.status().get("pos", 0)
        return self.player.position()

    def prev(self):
        if not self.active:
            return
        self._dir = -1
        if self.cur_position() > 3 or self.qi <= 0:
            self.seek(0)
        else:
            self.qi -= 1
            self.play_current()

    def toggle(self):
        if self.active and self.cast:
            self.cast_paused = not self.cast_paused
            self.cast.pause() if self.cast_paused else self.cast.resume()
            self.play_label = "Play" if self.cast_paused else "Pauza"
            self.pulse_stop() if self.cast_paused else self.pulse_start()
            return
        if self.active:
            self.player.toggle()
            self.play_label = "Play" if self.player.paused else "Pauza"
            self.pulse_stop() if self.player.paused else self.pulse_start()

    def seek(self, v):
        if self.active and self.cast:
            self.cast.seek(v)
        elif self.active:
            self.player.seek(v)

    def set_shuffle(self, on):
        if on == self.shuffle:
            return
        self.shuffle = on
        if on and self.active:
            rest = self.queue[self.qi + 1:]
            random.shuffle(rest)
            self.queue = self.queue[:self.qi + 1] + rest
            self.sync_queue()

    def tick(self, _dt):
        self.tick_timer()
        self.tick_alarm()
        self.update_dl_label()
        if self.cast:
            self.cast_tick()
            return
        if not self.active:
            return
        d = self.player.duration()
        p = self.current_path()
        live = self.is_radio(p)
        new_pos = self.player.position()
        self.dur = max(d, 1)
        if ANIM["on"] and not self.player.paused and 0 <= new_pos - self.pos < 2:
            anim(self, d=0.5, t="linear", pos=new_pos)
        else:
            Animation.cancel_all(self, "pos")
            self.pos = new_pos
        self.pos_text = fmt(new_pos)
        self.dur_text = "na żywo" if live else fmt(d)
        now = time.time()
        if self.keeps_position(p) and d > 600 and now - self.last_pos_save > 5:
            self.last_pos_save = now
            self.lib.set_pos(p, self.pos)
        if (self.xf and not self.apk and not live and not self.is_stream(p) and d > self.xf * 3
                and 0 < d - new_pos <= self.xf and not self.xf_started
                and not self.player.paused and not self.sleep_end_track):
            if self.repeat == "one":
                nxt = self.qi
            elif self.qi + 1 < len(self.queue):
                nxt = self.qi + 1
            else:
                nxt = 0 if self.repeat == "all" else None
            if nxt is not None and not self.is_stream(self.queue[nxt][0]):
                self.xf_started = True
                self.next(auto=True, fade=self.xf)      # płynne przejście
                return
        if not live and now - self.loaded_at > 1.5 and self.player.finished():
            self.next(auto=True)

    def viz_tick(self, _dt):
        if self.viz and not self.mini and self.root:
            self.root.ids.viz.step(self.active and not self.player.paused)

    def toggle_mini(self):
        self.mini = not self.mini
        anim(self, d=0.35, mini_k=0 if self.mini else 1)

    # --- okładki
    def load_cover(self, path):
        want = path

        def work():
            p = Path(path)
            for c in (p.with_suffix(".jpg"), p.with_suffix(".png"),
                      p.parent / "cover.jpg", p.parent / "folder.jpg"):
                if c.exists():
                    return str(c)
            if not mutagen:
                return ""
            data = None
            f = mutagen.File(p)
            tags = getattr(f, "tags", None)
            if hasattr(f, "pictures") and f.pictures:             # FLAC
                data = f.pictures[0].data
            elif tags is not None and hasattr(tags, "getall"):   # MP3
                pics = tags.getall("APIC")
                data = pics[0].data if pics else None
            elif tags is not None and "covr" in tags:            # M4A
                data = bytes(tags["covr"][0])
            if not data:
                return ""
            ext = ".png" if data[:4] == b"\x89PNG" else ".jpg"
            out = self.cover_dir / (hashlib.md5(path.encode()).hexdigest() + ext)
            if not out.exists():
                out.write_bytes(data)
            return str(out)

        def done(res):
            if self.current_path() == want and isinstance(res, str):
                self.cover = res
        self.run_bg(work, done)

    # --- skan i pobieranie
    def set_status(self, msg):
        self.status = msg

    def run_bg(self, work, done):
        """work() w wątku, done(wynik) w wątku UI."""
        def wrapper():
            try:
                res = work()
            except Exception as e:
                res = e
            Clock.schedule_once(lambda dt: done(res))
            try:
                from jnius import detach      # wątek używający Javy musi się odłączyć
                detach()
            except Exception:
                pass
        threading.Thread(target=wrapper, daemon=True).start()

    def scan(self):
        self.set_status("Skanowanie...")

        self.last_scan = time.time()

        def done(res):
            if isinstance(res, Exception):
                self.set_status(f"Błąd skanu: {res}")
            else:
                self.set_status(f"Skan: +{res[0]} / -{res[1]}")
                if not getattr(self, "restore_checked", False):
                    self.auto_restore()
            self.refresh()
        self.run_bg(self.lib.scan, done)

    # --- automatyczna kopia playlist (przetrwa odinstalowanie aplikacji)
    def autobackup_file(self):
        return self.export_dir / "Leox Player" / "leox-autokopia.json"

    @staticmethod
    def backup_has_data(d):
        return any(d.get(k) for k in ("playlists", "favorites", "channels", "stations", "podcasts"))

    def autobackup(self, *_):
        """Zapisuje playlisty, ulubione, kanały, stacje i podcasty do Music/Leox Player."""
        if not getattr(self, "restore_checked", False):
            return                      # najpierw sprawdzamy, czy jest kopia do wczytania
        try:
            data = self.backup_payload()
        except Exception:
            return
        if data == getattr(self, "_last_backup", None):
            return
        f = self.autobackup_file()
        try:
            if not self.backup_has_data(json.loads(data)) and f.exists():
                return                  # pusta biblioteka nie nadpisuje dobrej kopii
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(data, encoding="utf-8")
            self._last_backup = data
        except (OSError, ValueError):
            pass

    def auto_restore(self):
        """Nowa (pusta) biblioteka, np. po reinstalacji: wczytuje playlisty z kopii."""
        lib = self.lib
        if not lib.tracks():
            return                      # brak dostępu do plików albo pusty folder - spróbujemy po kolejnym skanie
        self.restore_checked = True
        if lib.playlists() or lib.favorites() or lib.channels() or lib.stations() or lib.podcasts():
            return
        n = 0
        cands = [self.autobackup_file()]
        try:
            cands += sorted(self.export_dir.glob("leox-kopia-*.json"), reverse=True)
        except OSError:
            pass
        for f in cands:
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                assert d.get("leox") == 1 and self.backup_has_data(d)
            except Exception:
                continue
            n = self.apply_backup(d)
            break
        try:
            m3u = (self.export_dir / "Playlisty").is_dir() and any(
                (self.export_dir / "Playlisty").glob("*.m3u*"))
        except OSError:
            m3u = False
        if m3u and not lib.playlists():
            self.import_m3u()
        elif n:
            self.set_status(f"Wczytano playlisty i ulubione z kopii ({n} poz.)")
        self.refresh()

    def apply_backup(self, d):
        idx = {((r[1] or "").casefold(), (r[2] or "").casefold()): r[0] for r in self.lib.tracks()}
        n = 0
        for name, items in d.get("playlists", {}).items():
            have = set()
            for t_, a in items:
                p_ = idx.get((t_.casefold(), a.casefold()))
                if p_ and p_ not in have:
                    self.lib.add_to_playlist(name, p_)
                    have.add(p_)
                    n += 1
        for t_, a in d.get("favorites", []):
            p_ = idx.get((t_.casefold(), a.casefold()))
            if p_:
                self.lib.set_fav(p_, True)
                n += 1
        for u, nm in d.get("channels", []):
            self.lib.save_channel(u, nm)
        for u, nm, ic in d.get("stations", []):
            self.lib.save_station(u, nm, ic)
        for u, tt, im in d.get("podcasts", []):
            self.lib.save_podcast(u, tt, im)
        return n

    def ask_all_files(self, *_):
        """APK na Androidzie 11+: dostęp do wszystkich plików (jak w Pydroid),
        żeby widzieć całą muzykę i kopię playlist po reinstalacji."""
        if not self.apk_build or self.lib.get_setting("nie_pytaj_pliki", "0") == "1":
            return
        try:
            from jnius import autoclass
            Build = autoclass("android.os.Build$VERSION")
            if Build.SDK_INT < 30 or autoclass("android.os.Environment").isExternalStorageManager():
                return
        except Exception:
            return

        def open_settings(b):
            try:
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Settings = autoclass("android.provider.Settings")
                Uri = autoclass("android.net.Uri")
                ctx = android_context()
                it = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                            Uri.parse("package:" + ctx.getPackageName()))
                it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                ctx.startActivity(it)
            except Exception as e:
                self.set_status(f"Nie udało się otworzyć ustawień: {e}")

        def never(b):
            self.lib.set_setting("nie_pytaj_pliki", "1")
        self.list_popup("Dostęp do plików", [
            {"text": "Włącz dostęp do wszystkich plików\n(cała muzyka i kopia playlist)",
             "tap": open_settings, "h": 90},
            {"text": "Nie pytaj więcej", "tap": never}])

    def download(self, url, btn=None, on_done=None, quiet=False, kind="yt",
                 title=None, dest=None):
        """Dodaje zadanie do kolejki pobierania (pobierane po jednym)."""
        if btn is not None:
            if getattr(btn, "busy", False):
                return
            btn.busy = True
            title = title or btn.text.split("\n")[0]
            btn.text = f"W kolejce...\n{title}"
        job = {"url": url, "btn": btn, "on_done": on_done, "quiet": quiet, "kind": kind,
               "title": title or url, "dest": dest, "pct": 0, "state": "czeka"}
        with self.dl_lock:
            self.dl_jobs.append(job)
            start = not self.dl_running
            self.dl_running = True
        if start:
            threading.Thread(target=self.dl_worker, daemon=True).start()
        self.update_dl_label()

    def download_url(self, url):
        """Film albo cała playlista z YouTube."""
        if "list=" not in url and "/playlist" not in url:
            self.download(url)
            return
        self.set_status("Wczytywanie playlisty...")

        def work():
            import yt_dlp
            with yt_dlp.YoutubeDL({"quiet": True, "logger": QUIET, "no_warnings": True,
                                   "extract_flat": "in_playlist"}) as ydl:
                info = ydl.extract_info(url, download=False)
            return [self.entry(e) for e in info.get("entries") or []]

        def done(res):
            if isinstance(res, Exception):
                self.show_error(res)
                return
            for v in res:
                self.download(v["url"], title=v["title"], quiet=True)
            self.set_status(f"Dodano do pobierania: {len(res)}")
        self.run_bg(work, done)

    def dl_worker(self):
        while True:
            with self.dl_lock:
                job = next((j for j in self.dl_jobs if j["state"] == "czeka"), None)
                if job is None:
                    self.dl_running = False
                    return
                job["state"] = "pobiera"
            Clock.schedule_once(lambda dt, j=job: self.dl_started(j))
            try:
                res = self.dl_yt(job) if job["kind"] in ("yt", "video") else self.dl_file(job)
                job["state"] = "gotowe"
            except Exception as e:
                res = e
                job["state"] = "błąd"
            Clock.schedule_once(lambda dt, j=job, r=res: self.dl_finished(j, r))
            try:
                from jnius import detach
                detach()
            except Exception:
                pass

    def dl_yt(self, job):
        import yt_dlp

        def hook(d):
            if d.get("status") == "downloading":
                tot = d.get("total_bytes") or d.get("total_bytes_estimate")
                if tot:
                    job["pct"] = min(99, int(d.get("downloaded_bytes", 0) * 100 / tot))
        quality = self.lib.get_setting("jakosc", "najlepsza")
        video = job["kind"] == "video"
        if video:
            self.video_dir().mkdir(parents=True, exist_ok=True)
        # Android (APK) nie pozwala zapisywać plików .part w Music/Movies -
        # pliki tymczasowe idą do prywatnego folderu, gotowy plik jest przenoszony.
        tmp_dl = Path(self.user_data_dir) / "tmp_dl"
        tmp_dl.mkdir(parents=True, exist_ok=True)
        opts = {
            "format": VIDEO_FORMAT if video else FORMATS.get(quality, FORMATS["najlepsza"]),
            "outtmpl": ("%(title)s [%(id)s].%(ext)s" if video else
                        "%(artist,uploader)s - %(title)s [%(id)s].%(ext)s"),
            "paths": {"home": str(self.video_dir() if video else self.dl_dir),
                      "temp": str(tmp_dl)},
            "windowsfilenames": True,   # Android nie przyjmuje : ? " | * < > w nazwach
            "trim_file_name": 150,
            "noplaylist": True,
            "quiet": True, "logger": QUIET,
            "no_warnings": True,
            "retries": 5,
            "fragment_retries": 5,
            "extractor_retries": 3,
            "socket_timeout": 30,
            "progress_hooks": [hook],
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(job["url"], download=True)
        job["title"] = info.get("title") or job["title"]
        if video:
            job["pct"] = 100
            return job["title"]
        try:                                      # zapasowy klient YouTube daje czasem .mp4 z dźwiękiem
            rd = info["requested_downloads"][0]
            if Path(rd["filepath"]).suffix.lower() == ".mp4":
                new = Path(rd["filepath"]).with_suffix(".m4a")
                os.replace(rd["filepath"], new)
                rd["filepath"] = str(new)
        except Exception:
            pass
        try:
            fp = info["requested_downloads"][0]["filepath"]
            t_title, t_artist = split_name(Path(fp).stem)
            title = clean_title(info.get("track") or t_title)
            artist = clean_artist(info.get("artist") or t_artist or info.get("uploader") or "")
            if mutagen:
                f = mutagen.File(fp, easy=True)
                if f is not None:
                    if f.tags is None:
                        f.add_tags()
                    f["title"], f["artist"] = title, artist
                    if info.get("album"):
                        f["album"] = info["album"]
                    f.save()
        except Exception:
            pass                                  # np. format webm nie obsługuje tagów
        try:
            fp = info["requested_downloads"][0]["filepath"]
            urllib.request.urlretrieve(
                f"https://i.ytimg.com/vi/{info['id']}/hqdefault.jpg",
                str(Path(fp).with_suffix(".jpg")))
        except Exception:
            pass                                  # okładka nie jest konieczna
        job["pct"] = 100
        self.lib.scan()
        return job["title"]

    def dl_file(self, job):
        dest = Path(job["dest"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        req = urllib.request.Request(job["url"], headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            got = 0
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if total:
                    job["pct"] = min(99, int(got * 100 / total))
        tmp.replace(dest)
        job["pct"] = 100
        self.lib.scan()
        return job["title"]

    def dl_started(self, job):
        if job["btn"] is not None:
            job["btn"].text = f"Pobieranie...\n{job['title']}"
        self.update_dl_label()

    def dl_finished(self, job, res):
        ok = not isinstance(res, Exception)
        btn = job["btn"]
        if ok:
            self.set_status(f"Pobrano: {job['title']}")
            self.fx_at("dl_btn", "dl")
            if btn is not None:
                btn.text, btn.bg = f"Pobrano\n{job['title']}", list(ACCENT_DIM)
        else:
            job["error"] = str(res)
            self.set_status(f"Błąd pobierania: {job['title']}")
            if not job["quiet"]:
                self.show_error(res)
            if btn is not None:
                btn.text, btn.busy = f"Błąd - dotknij ponownie\n{job['title']}", False
        self.refresh()
        self.update_dl_label()
        if job["on_done"]:
            job["on_done"](ok)

    def update_dl_label(self):
        act = [j for j in self.dl_jobs if j["state"] in ("czeka", "pobiera")]
        if not act:
            self.dl_label = "Pobrane"
            if self.dl_frac:
                anim(self, d=0.3, dl_frac=0)
            return
        cur = next((j for j in act if j["state"] == "pobiera"), None)
        pct = cur["pct"] if cur else 0
        self.dl_label = f"{pct}% ({len(act)})"
        if abs(self.dl_frac - pct / 100) > 0.001:
            anim(self, d=0.45, dl_frac=pct / 100)

    def show_downloads(self):
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter("height"))
        labels = []
        names = {"czeka": "Czeka", "gotowe": "Gotowe", "błąd": "Błąd"}

        def update(*_):
            for lbl, j in labels:
                st = j["state"]
                pre = f"{j['pct']}%" if st == "pobiera" else names[st]
                lbl.text = f"{pre}   {j['title']}"
                lbl.color = ACCENT if st == "pobiera" else (MUTED if st == "gotowe" else TEXT)

        def build_rows():
            grid.clear_widgets()
            labels.clear()
            for j in self.dl_jobs:
                lbl = Label(size_hint_y=None, height=dp(44), halign="left",
                            valign="middle", shorten=True)
                lbl.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0] - dp(12), sz[1])))
                grid.add_widget(lbl)
                labels.append((lbl, j))
            if not labels:
                grid.add_widget(Label(text="Brak pobrań", color=MUTED,
                                      size_hint_y=None, height=dp(44)))
            update()

        def clear(*_):
            with self.dl_lock:
                self.dl_jobs = [j for j in self.dl_jobs if j["state"] in ("czeka", "pobiera")]
            build_rows()
            self.update_dl_label()

        box = BoxLayout(orientation="vertical", spacing=dp(6))
        sv = ScrollView(bar_color=ACCENT_DIM)
        sv.add_widget(grid)
        box.add_widget(sv)
        bar = BoxLayout(size_hint_y=None, height=dp(56))
        pop = RoundPopup(title="Pobieranie", content=box, size_hint=(0.95, 0.85))
        b1 = RoundButton(text="Wyczyść gotowe", bg=list(ACCENT_DIM))
        b1.bind(on_release=clear)
        b2 = RoundButton(text="Zamknij", bg=list(CARD_HI))
        b2.bind(on_release=lambda *_: pop.dismiss())
        bar.add_widget(b1)
        bar.add_widget(b2)
        box.add_widget(bar)
        build_rows()
        ev = Clock.schedule_interval(update, 0.5)
        pop.bind(on_dismiss=lambda *_: ev.cancel())
        pop.open()

    # --- YouTube: wyszukiwanie i kanały
    @staticmethod
    def normalize_channel(s):
        s = s.strip()
        if s.startswith("http"):
            url = s
        elif s.startswith("@"):
            url = "https://www.youtube.com/" + s
        else:
            url = "https://www.youtube.com/@" + s
        url = url.rstrip("/")
        for suf in ("/videos", "/featured", "/streams", "/shorts", "/playlists"):
            if url.endswith(suf):
                url = url[:-len(suf)]
        return url

    @classmethod
    def entry(cls, e):
        url = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id')}"
        ch = e.get("channel_url") or e.get("uploader_url")
        if not ch and e.get("channel_id"):
            ch = f"https://www.youtube.com/channel/{e['channel_id']}"
        return {"id": e.get("id"),
                "ts": e.get("timestamp") or e.get("release_timestamp"),
                "title": e.get("title") or "?",
                "channel": e.get("channel") or e.get("uploader") or "",
                "dur": e.get("duration") or 0, "url": url,
                "ch_url": cls.normalize_channel(ch) if ch else None}

    def video_row(self, v, with_channel):
        row = {"text": f"{v['title']}\n{v['channel']}   [{fmt(v['dur'])}]",
               "tap": lambda b, u=v["url"]: self.download(u, b), "keep": True,
               "sides": [("Graj", lambda b, v=v: self.stream(v))]}
        if with_channel and v["ch_url"]:
            row["sides"].append(("Kanał", lambda b, c=v["ch_url"]: self.open_channel(c)))
        return row

    def yt_search(self, query):
        self.set_status("Szukanie na YouTube...")

        def work():
            import yt_dlp
            opts = {"quiet": True, "logger": QUIET, "extract_flat": True, "skip_download": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch20:{query}", download=False)
            return [self.entry(e) for e in info.get("entries") or []]

        def done(res):
            if isinstance(res, Exception):
                self.set_status(f"Błąd wyszukiwania: {res}")
            elif not res:
                self.set_status("Brak wyników")
            else:
                self.set_status("Dotknij, aby pobrać; Graj - słuchaj bez pobierania")
                self.list_popup(f"YouTube: {query}",
                                [self.video_row(v, True) for v in res])
        self.run_bg(work, done)

    def open_channel(self, url):
        self.set_status("Wczytywanie kanału...")

        def work():
            import yt_dlp
            opts = {"quiet": True, "logger": QUIET, "extract_flat": "in_playlist", "playlistend": 50}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url + "/videos", download=False)
            name = (info.get("channel") or info.get("uploader")
                    or info.get("title") or url)
            vids = [self.entry(e) for e in info.get("entries") or []]
            for v in vids:
                v["channel"] = v["channel"] or name
            return name, vids

        def done(res):
            if isinstance(res, Exception):
                self.set_status(f"Błąd kanału: {res}")
                return
            name, vids = res
            saved = any(u == url for u, _ in self.lib.channels())
            footer = [] if saved else [
                ("Zapisz kanał", lambda b: (self.lib.save_channel(url, name),
                                            self.set_status(f"Zapisano: {name}")))]
            self.set_status(f"{name}: {len(vids)} filmów - dotknij, aby pobrać")
            self.list_popup(name, [self.video_row(v, False) for v in vids], footer)
        self.run_bg(work, done)

    def show_channels(self):
        chans = self.lib.channels()
        rows = [{"text": name, "tap": lambda b, u=u: self.open_channel(u),
                 "side": "Usuń",
                 "side_fn": lambda b, u=u, n=name: (self.lib.remove_channel(u),
                                                    self.set_status(f"Usunięto: {n}"))}
                for u, name in chans]
        footer = [("Nowości", lambda b: self.show_news()),
                  ("Dodaj kanał", lambda b: self.ask(
            "@nazwa lub link kanału",
            lambda s: self.open_channel(self.normalize_channel(s))))]
        if not chans:
            self.set_status("Brak zapisanych kanałów")
        self.list_popup("Kanały", rows, footer)

    @staticmethod
    def explain(err):
        s = str(err)
        low = s.lower()
        if "errno 22" in low or "invalid argument" in low:
            return "Nieprawidłowa nazwa pliku lub ścieżka."
        if "errno 13" in low or "permission denied" in low:
            return "Brak uprawnień do zapisu. Zezwól Pydroid na dostęp do plików w ustawieniach Androida."
        if "certificate" in low:
            return "Problem z certyfikatami SSL. Zainstaluj w Pip pakiet: certifi"
        if "not a bot" in low or "sign in to confirm" in low:
            return "YouTube żąda weryfikacji. Spróbuj później albo przez inną sieć (Wi-Fi/LTE)."
        if "no module named" in low:
            return "Brak modułu. Zainstaluj w Pip: yt-dlp"
        apk = service_available()
        if "format" in low or "javascript" in low or "unavailable" in low:
            if apk:
                return ("YouTube nie udostępnił tego nagrania (próbowano kilku metod). "
                        "Spróbuj później albo zbuduj APK od nowa - pobierze najnowszy yt-dlp.")
            return "Zaktualizuj yt-dlp w Pip (Upgrade), potem uruchom aplikację ponownie."
        if apk:
            return "Spróbuj ponownie. Jeśli błąd wraca, zbuduj APK od nowa (najnowszy yt-dlp)."
        return "Zaktualizuj yt-dlp w Pip i spróbuj ponownie."

    def show_error(self, err, title="Błąd pobierania"):
        try:
            import yt_dlp
            ver = yt_dlp.version.__version__
        except Exception:
            ver = "brak"
        text = (f"{self.explain(err)}\n\nyt-dlp: {ver}\nKatalog: {self.dl_dir}"
                f"\n\nSzczegóły:\n{str(err)[:800]}")
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(4))
        sv = ScrollView(bar_color=ACCENT_DIM)
        lbl = Label(text=text, size_hint_y=None, halign="left", valign="top")
        lbl.bind(width=lambda w, v: setattr(w, "text_size", (v, None)),
                 texture_size=lambda w, v: setattr(w, "height", v[1]))
        sv.add_widget(lbl)
        box.add_widget(sv)
        btn = RoundButton(text="OK", size_hint_y=None, height=dp(54),
                          bg=list(ACCENT_DIM))
        box.add_widget(btn)
        pop = RoundPopup(title=title, content=box, size_hint=(0.92, 0.7))
        btn.bind(on_release=lambda *_: pop.dismiss())
        pop.open()

    def collect_news(self):
        """Najnowsze filmy z zapisanych kanałów; 'new' = jeszcze niewidziany."""
        chans = self.lib.channels()

        def fetch(ch):
            import yt_dlp
            url, name = ch
            opts = {"quiet": True, "logger": QUIET, "no_warnings": True,
                    "extract_flat": "in_playlist", "playlistend": 8}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url + "/videos", download=False)
            vids = [self.entry(e) for e in info.get("entries") or []]
            for v in vids:
                v["channel"] = v["channel"] or name
                v["ch_url"] = v["ch_url"] or url
            return vids

        from concurrent.futures import ThreadPoolExecutor
        per, errors = [], 0
        with ThreadPoolExecutor(max_workers=4) as ex:
            for fut in [ex.submit(fetch, c) for c in chans]:
                try:
                    per.append(fut.result())
                except Exception:
                    errors += 1
        merged = []
        for i in range(max((len(v) for v in per), default=0)):
            merged += [v[i] for v in per if i < len(v)]
        if merged and all(v["ts"] for v in merged):
            merged.sort(key=lambda v: v["ts"], reverse=True)
        new = self.lib.unseen([v["id"] for v in merged])
        for v in merged:
            v["new"] = v["id"] in new
        merged.sort(key=lambda v: not v["new"])
        self.lib.mark_seen([v["id"] for v in merged])
        return merged, errors

    def show_news(self):
        if not self.lib.channels():
            self.set_status("Najpierw zapisz jakiś kanał")
            return
        self.set_status("Sprawdzanie kanałów...")

        def done(res):
            if isinstance(res, Exception):
                self.set_status(f"Błąd nowości: {res}")
                return
            vids, errors = res
            n_new = sum(1 for v in vids if v["new"])
            msg = f"Nowych: {n_new}"
            if errors:
                msg += f", niedostępne kanały: {errors}"
            self.set_status(msg)
            rows = []
            for v in vids:
                r = self.video_row(v, True)
                if v["new"]:
                    r["text"] = "NOWE  " + r["text"]
                rows.append(r)
            self.list_popup("Nowości z kanałów", rows)
        self.run_bg(self.collect_news, done)

    def auto_news(self, init=False):
        """Pobiera nowe filmy (do 20 min) z zapisanych kanałów.
        init=True tylko oznacza obecne jako widziane."""
        if not self.lib.channels():
            return

        def done(res):
            if isinstance(res, Exception):
                self.set_status("Auto-nowości: błąd sprawdzania")
                return
            vids, _ = res
            if init:
                self.set_status("Auto-nowości włączone - od teraz pobiorę nowe filmy")
                return
            new = [v for v in vids if v["new"] and (not v["dur"] or v["dur"] <= 1200)]
            for v in new:
                self.download(v["url"], title=v["title"], quiet=True)
            self.set_status(f"Auto-nowości: pobieram {len(new)}" if new
                            else "Auto-nowości: brak nowych filmów")
        self.run_bg(self.collect_news, done)

    # --- okna
    def list_popup(self, title, rows, footer=()):
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
        grid.bind(minimum_height=grid.setter("height"))
        box = BoxLayout(orientation="vertical", spacing=dp(6))
        pop = RoundPopup(title=title, content=box, size_hint=(0.95, 0.9))

        def handler(fn, keep):
            def h(btn):
                if not keep:
                    pop.dismiss()
                fn(btn)
            return h

        self.build_rows(grid, rows, pop)
        sv = ScrollView(bar_color=ACCENT_DIM)
        sv.add_widget(grid)
        box.add_widget(sv)
        bar = BoxLayout(size_hint_y=None, height=dp(56))
        for text, fn in list(footer) + [("Zamknij", lambda b: None)]:
            fb = RoundButton(text=text,
                             bg=list(ACCENT_DIM if text != "Zamknij" else CARD_HI))
            fb.bind(on_release=handler(fn, False))
            bar.add_widget(fb)
        box.add_widget(bar)
        pop.open()

    def build_rows(self, grid, rows, pop):
        """Wiersze okna: [miniatura] przycisk [przyciski boczne]; pojawiają się po kolei."""
        grid.clear_widgets()

        def handler(fn, keep):
            def h(btn):
                if not keep:
                    pop.dismiss()
                fn(btn)
            return h

        for n, r in enumerate(rows):
            line = BoxLayout(size_hint_y=None, height=dp(r.get("h", 72)), spacing=dp(2))
            if r.get("image"):
                im = TapImage(size_hint_x=None, width=dp(92), fit_mode="contain")
                self.net_image(r["image"], im)
                line.add_widget(im)
            elif "avatar" in r:
                im = TapImage(size_hint_x=None, width=dp(64), fit_mode="contain")
                self.online_avatar(r["avatar"], im)
                line.add_widget(im)
            b = RoundButton(text=r["text"], halign="left", valign="middle",
                            markup=r.get("markup", False), max_lines=3)
            if "bg" in r:
                b.bg = r["bg"]
            b.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0] - dp(28), sz[1])))
            b.bind(on_release=handler(r["tap"], r.get("keep", False)))
            line.add_widget(b)
            sides = list(r.get("sides", []))
            if r.get("side"):
                sides.append((r["side"], r["side_fn"]))
            for text, fn in sides:
                sb = RoundButton(text=text, size_hint_x=None, width=dp(62), bg=list(CARD_HI))
                sb.bind(on_release=handler(fn, False))
                line.add_widget(sb)
            grid.add_widget(line)
            if ANIM["on"] and n < 14:
                line.opacity = 0
                Clock.schedule_once(lambda dt, w=line: anim(w, d=0.3, opacity=1), 0.04 * n + 0.05)

    def live_search_popup(self, title, hint, fetch, footer=(), empty_msg="Brak wyników",
                          render=None, initial=""):
        """Okno z wyszukiwarką: wyniki odświeżają się same w trakcie pisania."""
        box = BoxLayout(orientation="vertical", spacing=dp(6))
        ti = RoundInput(hint_text=hint, multiline=False, size_hint_y=None, height=dp(54),
                        text=initial)
        box.add_widget(ti)
        info = Label(text="", color=MUTED, font_size="13sp", size_hint_y=None, height=dp(24))
        box.add_widget(info)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
        grid.bind(minimum_height=grid.setter("height"))
        sv = ScrollView(bar_color=ACCENT_DIM)
        sv.add_widget(grid)
        box.add_widget(sv)
        bar = BoxLayout(size_hint_y=None, height=dp(56))
        pop = RoundPopup(title=title, content=box, size_hint=(1, 1))
        for text, fn in list(footer) + [("Zamknij", lambda b: None)]:
            fb = RoundButton(text=text, bg=list(ACCENT_DIM if text != "Zamknij" else CARD_HI))
            fb.bind(on_release=lambda _b, fn=fn: (pop.dismiss(), fn(_b)))
            bar.add_widget(fb)
        box.add_widget(bar)
        state = {"token": 0, "ev": None}

        def run(query):
            state["token"] += 1
            tok = state["token"]
            info.text = "Szukanie..."

            def done(res):
                if tok != state["token"]:
                    return                      # przyszło starsze wyszukiwanie
                if isinstance(res, Exception):
                    info.text = f"Błąd: {res}"[:120]
                    return
                info.text = "" if res else empty_msg
                (render or self.build_rows)(grid, res, pop)
                sv.scroll_y = 1
            self.run_bg(lambda: fetch(query), done)

        def typed(_w, txt):
            if state["ev"]:
                state["ev"].cancel()
            q = txt.strip()
            if len(q) == 1:
                return
            state["ev"] = Clock.schedule_once(lambda dt: run(q), 0.7)
        ti.bind(text=typed)
        pop.bind(on_dismiss=lambda *_: state["ev"] and state["ev"].cancel())
        pop.open()
        run(initial.strip())
        return pop

    # --- YouTube
    def yt_rows(self, query):
        import yt_dlp
        q = query or "nowości muzyczne"
        with yt_dlp.YoutubeDL({"quiet": True, "logger": QUIET, "no_warnings": True, "extract_flat": True,
                               "skip_download": True}) as ydl:
            info = ydl.extract_info(f"ytsearch20:{q}", download=False)
        rows = []
        for e in info.get("entries") or []:
            v = self.entry(e)
            r = self.video_row(v, True)
            if v["id"]:
                r["image"] = f"https://i.ytimg.com/vi/{v['id']}/mqdefault.jpg"
            r["h"] = 84
            rows.append(r)
        return rows

    def show_youtube(self):
        self.live_search_popup(
            "YouTube", "Szukaj filmów - wyniki pojawiają się same", self.yt_fetch,
            footer=[("Pełny YouTube", lambda b: open_external("https://m.youtube.com")),
                    ("Moja lista", lambda b: self.show_yt_lists()),
                    ("Kanały", lambda b: self.show_channels())],
            empty_msg="Brak filmów", render=self.yt_cards)

    def yt_fetch(self, query):
        import yt_dlp
        if query:
            with yt_dlp.YoutubeDL({"quiet": True, "logger": QUIET, "no_warnings": True, "extract_flat": True,
                                   "skip_download": True}) as ydl:
                info = ydl.extract_info(f"ytsearch24:{query}", download=False)
            return [self.entry(e) for e in info.get("entries") or [] if e.get("id")]
        return self.yt_home()

    def yt_home(self):
        """Strona główna: polecane (jeśli YouTube je zwróci bez logowania),
        potem najnowsze z zapisanych kanałów, na końcu popularne."""
        import yt_dlp
        opts = {"quiet": True, "logger": QUIET, "no_warnings": True, "extract_flat": "in_playlist",
                "playlistend": 24}
        vids = []
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(":ytrec", download=False)
            vids = [self.entry(e) for e in info.get("entries") or [] if e.get("id")]
        except Exception:
            pass
        if len(vids) < 5:
            for url, name in self.lib.channels()[:6]:
                try:
                    with yt_dlp.YoutubeDL(dict(opts, playlistend=4)) as ydl:
                        info = ydl.extract_info(url + "/videos", download=False)
                    for e in info.get("entries") or []:
                        v = self.entry(e)
                        v["channel"] = v["channel"] or name
                        vids.append(v)
                except Exception:
                    pass
        if len(vids) < 5:
            with yt_dlp.YoutubeDL({"quiet": True, "logger": QUIET, "no_warnings": True, "extract_flat": True,
                                   "skip_download": True}) as ydl:
                info = ydl.extract_info("ytsearch24:popularne dzisiaj", download=False)
            vids += [self.entry(e) for e in info.get("entries") or [] if e.get("id")]
        return vids

    def net_image(self, url, widget, callback=None):
        """Pobiera obrazek do pamięci podręcznej i ustawia go w widżecie."""
        if not url:
            return
        folder = Path(self.user_data_dir) / "miniatury"
        path = folder / (hashlib.md5(url.encode()).hexdigest() + ".jpg")

        def apply(p):
            if widget is not None:
                widget.source = p
            if callback:
                callback(p)
        if path.exists():
            apply(str(path))
            return

        def work():
            folder.mkdir(parents=True, exist_ok=True)
            data = http_get(url)
            tmp = path.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.replace(path)
            return str(path)
        self.run_bg(work, lambda res: isinstance(res, str) and apply(res))

    @staticmethod
    def thumb(v):
        return f"https://i.ytimg.com/vi/{v['id']}/mqdefault.jpg" if v.get("id") else ""

    def video_dir(self):
        return self.export_dir / "Filmy"

    def local_videos(self):
        d = self.video_dir()
        if not d.exists():
            return []
        vids = []
        for f in sorted(d.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix.lower() not in (".mp4", ".webm", ".mkv", ".3gp"):
                continue
            m = YT_ID_RE.search(f.name)
            vid = m.group(1) if m else None
            vids.append({"id": vid, "title": re.sub(r"\s*\[[A-Za-z0-9_-]{11}\]$", "", f.stem),
                         "channel": "Pobrany film", "dur": 0, "ch_url": None, "local": str(f),
                         "url": f"https://www.youtube.com/watch?v={vid}" if vid else ""})
        return vids

    def download_choice(self, v):
        self.list_popup("Pobierz", [
            {"text": "Tylko dźwięk (do biblioteki muzyki)",
             "tap": lambda b: self.download(v["url"], title=v["title"])},
            {"text": "Film z obrazem (do oglądania bez internetu)",
             "tap": lambda b: self.download(v["url"], kind="video", title=v["title"])}])

    def yt_later(self, v):
        self.lib.yt_add("yt_later", v)
        self.set_status(f"Do obejrzenia: {v['title']}")

    def yt_cards(self, grid, vids, pop):
        """Karty filmów jak w aplikacji YouTube: duża miniatura, tytuł, kanał."""
        grid.clear_widgets()
        if not vids:
            grid.add_widget(Label(text="Pusto", color=MUTED, size_hint_y=None, height=dp(60)))
        for n, v in enumerate(vids):
            card = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4),
                             padding=(dp(4), dp(8)))
            card.bind(minimum_height=card.setter("height"))
            img = TapImage(size_hint_y=None, fit_mode="contain")
            self.net_image(self.thumb(v), img)
            img.bind(width=lambda w, val: setattr(w, "height", val * 9 / 16))
            img.bind(on_release=lambda _w, v=v: self.watch(v))
            card.add_widget(img)
            title = Label(text=v["title"], bold=True, font_size="15sp", size_hint_y=None,
                          halign="left", valign="top", max_lines=2, shorten=True)
            title.bind(width=lambda w, val: setattr(w, "text_size", (val - dp(8), None)),
                       texture_size=lambda w, val: setattr(w, "height", val[1]))
            card.add_widget(title)
            sub = v["channel"] + (f"   {fmt(v['dur'])}" if v["dur"] else "")
            sl = Label(text=sub, color=MUTED, font_size="12sp", size_hint_y=None,
                       height=dp(20), halign="left", shorten=True)
            sl.bind(width=lambda w, val: setattr(w, "text_size", (val - dp(8), None)))
            card.add_widget(sl)
            row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(2))
            buttons = [("Oglądaj", lambda b, v=v: self.watch(v), ACCENT_DIM, 1.2)]
            if not v.get("local"):
                buttons += [("Słuchaj", lambda b, v=v: self.stream(v), CARD, 1),
                            ("Pobierz", lambda b, v=v: self.download_choice(v), CARD, 1),
                            ("Kanał", lambda b, v=v: v["ch_url"] and self.open_channel(v["ch_url"]),
                             CARD, 1),
                            ("+", lambda b, v=v: self.yt_later(v), CARD, 0.5)]
            for text, fn, bg, w in buttons:
                b = RoundButton(text=text, bg=list(bg), font_size="13sp", size_hint_x=w)
                b.bind(on_release=fn)
                row.add_widget(b)
            card.add_widget(row)
            grid.add_widget(card)
            if ANIM["on"] and n < 8:
                card.opacity = 0
                Clock.schedule_once(lambda dt, w=card: anim(w, d=0.35, opacity=1), 0.06 * n + 0.05)

    def cards_popup(self, title, vids, table=None):
        box = BoxLayout(orientation="vertical", spacing=dp(6))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
        grid.bind(minimum_height=grid.setter("height"))
        sv = ScrollView(bar_color=ACCENT_DIM)
        sv.add_widget(grid)
        box.add_widget(sv)
        bar = BoxLayout(size_hint_y=None, height=dp(56))
        pop = RoundPopup(title=title, content=box, size_hint=(1, 1))
        if table:
            clr = RoundButton(text="Wyczyść listę", bg=list(ACCENT_DIM))
            clr.bind(on_release=lambda *_: (self.lib.yt_remove(table), pop.dismiss(),
                                            self.set_status("Lista wyczyszczona")))
            bar.add_widget(clr)
        close = RoundButton(text="Zamknij", bg=list(CARD_HI))
        close.bind(on_release=lambda *_: pop.dismiss())
        bar.add_widget(close)
        box.add_widget(bar)
        self.yt_cards(grid, vids, pop)
        pop.open()

    def show_yt_lists(self):
        self.list_popup("Moja lista", [
            {"text": "Historia oglądania",
             "tap": lambda b: self.cards_popup("Historia oglądania",
                                               self.lib.yt_list("yt_history"), "yt_history")},
            {"text": "Do obejrzenia",
             "tap": lambda b: self.cards_popup("Do obejrzenia",
                                               self.lib.yt_list("yt_later"), "yt_later")},
            {"text": "Pobrane filmy",
             "tap": lambda b: self.cards_popup("Pobrane filmy", self.local_videos())}])

    def watch(self, v):
        """Ekran oglądania filmu (z internetu albo pobranego), z napisami."""
        if self.active and not self.player.paused:
            self.toggle()                     # muzyka na pauzę
        if not v.get("local"):
            self.lib.yt_add("yt_history", v)
        pl_audio = self.player.local if self.apk else Player()   # dźwięk filmu, osobno od muzyki
        box = BoxLayout(orientation="vertical", spacing=dp(6))
        area = FloatLayout(size_hint_y=None)
        box.bind(width=lambda w, val: setattr(area, "height", val * 9 / 16))
        thumb_img = TapImage(fit_mode="contain", size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        self.net_image(self.thumb(v), thumb_img)
        area.add_widget(thumb_img)
        msg = MsgLabel(text="Wczytywanie filmu...", bold=True, halign="center",
                       valign="middle", size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        msg.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0] - dp(24), None)))
        area.add_widget(msg)
        sub_lbl = MsgLabel(text="", font_size="15sp", halign="center", valign="middle",
                           size_hint=(1, None), height=dp(60), pos_hint={"x": 0, "y": 0})
        sub_lbl.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0] - dp(20), None)))
        area.add_widget(sub_lbl)
        box.add_widget(area)
        ctrl = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(2))
        b_back = RoundButton(text="-10 s")
        b_play = RoundButton(text="Pauza", bg=list(ACCENT_DIM))
        b_fwd = RoundButton(text="+10 s")
        b_sub = RoundButton(text="Napisy", font_size="13sp", disabled=True)
        tlabel = Label(text="0:00 / 0:00", color=MUTED, size_hint_x=1.3, font_size="13sp")
        for w in (b_back, b_play, b_fwd, b_sub, tlabel):
            ctrl.add_widget(w)
        box.add_widget(ctrl)
        title = Label(text=v["title"], bold=True, font_size="17sp", size_hint_y=None,
                      halign="left", valign="top")
        title.bind(width=lambda w, val: setattr(w, "text_size", (val - dp(12), None)),
                   texture_size=lambda w, val: setattr(w, "height", val[1]))
        box.add_widget(title)
        ch = Label(text=v["channel"], color=MUTED, size_hint_y=None, height=dp(22),
                   halign="left")
        ch.bind(width=lambda w, val: setattr(w, "text_size", (val - dp(12), None)))
        box.add_widget(ch)
        acts = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(2))
        box.add_widget(acts)
        box.add_widget(Widget())
        close = RoundButton(text="Zamknij", size_hint_y=None, height=dp(56), bg=list(CARD_HI))
        box.add_widget(close)
        pop = RoundPopup(title="YouTube", content=box, size_hint=(1, 1))
        st = {"video": None, "ev": None, "open": True, "subs": {}, "lang": None,
              "cues": [], "starts": []}

        def stop_video():
            if st["video"] is not None:
                st["video"].state = "stop"
                st["video"].unload()
            if st.get("audio") is not None:          # osobna ścieżka dźwięku
                try:
                    st["audio"].stop()
                    st["audio"].release()
                except Exception:
                    pass
                st["audio"] = None

        def external(*_):
            stop_video()
            open_external(v["url"])

        def delete_local(*_):
            try:
                Path(v["local"]).unlink()
                self.set_status("Usunięto film")
            except OSError as e:
                self.set_status(f"Nie można usunąć: {e}")
            pop.dismiss()
        acts_list = []
        if v.get("url"):
            acts_list.append(("W aplikacji YT", external))
        if v.get("local"):
            acts_list.append(("Usuń plik", delete_local))
        else:
            acts_list += [("Słuchaj", lambda b: (pop.dismiss(), self.stream(v))),
                          ("Pobierz", lambda b: self.download_choice(v)),
                          ("Później", lambda b: self.yt_later(v)),
                          ("Kanał", lambda b: v["ch_url"] and self.open_channel(v["ch_url"]))]
        if v.get("url"):
            acts_list.append(("Udostępnij", lambda b: self.share_video(v)))
        for text, fn in acts_list:
            b = RoundButton(text=text, font_size="13sp")
            b.bind(on_release=fn)
            acts.add_widget(b)

        def tick(_dt):
            vid = st["video"]
            if vid is None or not vid.duration or vid.duration <= 0:
                return
            tlabel.text = f"{fmt(vid.position)} / {fmt(vid.duration)}"
            aud = st.get("audio")
            if aud is not None and vid.state == "play" and vid.position > 0:
                try:
                    if not st.get("a_started"):
                        aud.seekTo(int(vid.position * 1000))
                        aud.start()
                        st["a_started"] = True
                    elif abs(aud.getCurrentPosition() / 1000 - vid.position) > 0.35:
                        aud.seekTo(int(vid.position * 1000))   # wyrównanie dźwięku z obrazem
                except Exception:
                    pass
            if st["cues"]:
                i = bisect.bisect_right(st["starts"], vid.position) - 1
                cue = st["cues"][i] if i >= 0 else None
                sub_lbl.text = cue[2] if cue and vid.position <= cue[1] + 0.3 else ""

        def seek(delta):
            vid = st["video"]
            if vid is not None and vid.duration and vid.duration > 0:
                target = max(0.0, min(vid.duration, vid.position + delta))
                vid.seek(target / vid.duration)
                if st.get("audio") is not None:
                    try:
                        st["audio"].seekTo(int(target * 1000))
                    except Exception:
                        pass

        def toggle(*_):
            vid = st["video"]
            if vid is None:
                return
            vid.state = "pause" if vid.state == "play" else "play"
            b_play.text = "Play" if vid.state == "pause" else "Pauza"
            aud = st.get("audio")
            if aud is not None and st.get("a_started"):
                try:
                    aud.pause() if vid.state == "pause" else aud.start()
                except Exception:
                    pass

        def cycle_subs(*_):
            langs = [None] + list(st["subs"])
            nxt = langs[(langs.index(st["lang"]) + 1) % len(langs)]
            st["lang"], st["cues"], st["starts"] = nxt, [], []
            sub_lbl.text = ""
            b_sub.text = f"Napisy: {nxt}" if nxt else "Napisy: wył."
            if not nxt:
                return
            url = st["subs"][nxt]

            def work_s():
                return parse_vtt(http_get(url).decode("utf-8", "ignore"))

            def done_s(res):
                if isinstance(res, Exception) or st["lang"] != nxt:
                    return
                st["cues"], st["starts"] = res, [c[0] for c in res]
            self.run_bg(work_s, done_s)
        b_back.bind(on_release=lambda *_: seek(-10))
        b_fwd.bind(on_release=lambda *_: seek(10))
        b_play.bind(on_release=toggle)
        b_sub.bind(on_release=cycle_subs)

        def closed(*_):
            st["open"] = False
            if st["ev"]:
                st["ev"].cancel()
            stop_video()
        pop.bind(on_dismiss=closed)
        close.bind(on_release=lambda *_: pop.dismiss())
        pop.open()

        def work():
            from kivy.core.video import Video as CoreVideo
            if CoreVideo is None:
                raise RuntimeError("brak odtwarzacza wideo w Kivy")
            if v.get("local"):
                return {"video": v["local"]}, {}
            import yt_dlp
            opts = {"quiet": True, "logger": QUIET, "no_warnings": True, "noplaylist": True,
                    "format": "bv*+ba/b/bv/ba"}       # dowolny wybór - formaty wybieramy sami
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(v["url"], download=False)
            fmts = [f for f in info.get("formats") or [] if f.get("url")]

            def has(f, key):
                return f.get(key) not in (None, "none")
            muxed = [f for f in fmts if has(f, "vcodec") and has(f, "acodec")
                     and (f.get("height") or 0) <= 720]
            if muxed:                                  # jeden plik z obrazem i dźwiękiem
                best = max(muxed, key=lambda f: ((f.get("height") or 0), f.get("tbr") or 0))
                media = {"video": best["url"], "vh": best.get("http_headers")}
            else:                                      # obraz i dźwięk osobno
                vids = [f for f in fmts if has(f, "vcodec") and not has(f, "acodec")
                        and (f.get("height") or 0) <= 720]
                h264 = [f for f in vids if str(f.get("vcodec", "")).startswith(("avc1", "h264"))]
                auds = [f for f in fmts if has(f, "acodec") and not has(f, "vcodec")]
                m4a = [f for f in auds if f.get("ext") == "m4a"]
                if not (vids and auds):
                    raise RuntimeError("YouTube nie udostępnił obrazu")
                vbest = max(h264 or vids, key=lambda f: ((f.get("height") or 0), f.get("tbr") or 0))
                abest = max(m4a or auds, key=lambda f: f.get("abr") or f.get("tbr") or 0)
                media = {"video": vbest["url"], "vh": vbest.get("http_headers"),
                         "audio": pl_audio.prepare(abest["url"], abest.get("http_headers"))}
            subs = {}
            for lang in ("pl", "en"):
                for srcmap in (info.get("subtitles") or {}, info.get("automatic_captions") or {}):
                    tracks = srcmap.get(lang) or next(
                        (val for k, val in srcmap.items() if k.startswith(lang + "-")), None)
                    vtt = next((x for x in tracks or [] if x.get("ext") == "vtt"), None)
                    if vtt:
                        subs[lang] = vtt["url"]
                        break
            return media, subs

        def fail(reason):
            msg.text = f"Nie da się odtworzyć tutaj ({reason}).\nDotknij: W aplikacji YT"

        def done(res):
            if not st["open"]:
                if not isinstance(res, Exception) and res[0].get("audio") is not None:
                    res[0]["audio"].release()
                return
            if isinstance(res, Exception):
                fail(str(res)[:60])
                return
            media, subs = res
            st["subs"] = subs
            b_sub.disabled = not subs
            b_sub.text = "Napisy: wył." if subs else "Brak napisów"
            video_headers(media.get("vh"))
            st["audio"], st["a_started"] = media.get("audio"), False
            from kivy.uix.video import Video
            vid = Video(source=media["video"], state="play", fit_mode="contain",
                        volume=0 if st["audio"] is not None else 1, color=(1, 1, 1, 0),
                        size_hint=(1, 1), pos_hint={"x": 0, "y": 0}, options={"eos": "stop"})
            # bez obrazu Kivy rysuje biały prostokąt - pokazujemy wideo dopiero z pierwszą klatką
            vid.bind(texture=lambda w, tex: setattr(w, "color", (1, 1, 1, 1 if tex else 0)))
            msg.text = "Wczytywanie obrazu..."
            area.add_widget(vid)
            area.remove_widget(sub_lbl)
            area.add_widget(sub_lbl)            # napisy nad obrazem
            st["video"] = vid
            vid.bind(texture=lambda w, tex: tex and setattr(msg, "text", ""))
            st["ev"] = Clock.schedule_interval(tick, 0.2)

            def check(_dt):
                if st["open"] and not vid.loaded:
                    fail("brak obrazu")
            Clock.schedule_once(check, 15)
        self.run_bg(work, done)

    def ask(self, title, cb):
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(4))
        ti = RoundInput(multiline=False, size_hint_y=None, height=dp(54))
        btn = RoundButton(text="OK", size_hint_y=None, height=dp(54),
                          bg=list(ACCENT_DIM))
        box.add_widget(ti)
        box.add_widget(btn)
        pop = RoundPopup(title=title, content=box, size_hint=(0.92, None),
                         height=dp(210))

        def ok(*_):
            pop.dismiss()
            if ti.text.strip():
                cb(ti.text.strip())
        btn.bind(on_release=ok)
        ti.bind(on_text_validate=ok)
        pop.open()

    # --- formularz
    def form_popup(self, title, fields, buttons, info=""):
        """fields: [(klucz, podpowiedź, wartość)]; buttons: [(tekst, fn(wartości, okno))]"""
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(4),
                        size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        if info:
            lbl = Label(text=info, color=MUTED, font_size="13sp", size_hint_y=None,
                        halign="left", valign="top")
            lbl.bind(width=lambda w, v: setattr(w, "text_size", (v, None)),
                     texture_size=lambda w, v: setattr(w, "height", v[1]))
            box.add_widget(lbl)
        inputs = {}
        for key, hint, value in fields:
            ti = RoundInput(hint_text=hint, text=value, multiline=False,
                            size_hint_y=None, height=dp(54))
            inputs[key] = ti
            box.add_widget(ti)
        holder = {}
        for text, fn in buttons:
            b = RoundButton(text=text, size_hint_y=None, height=dp(54),
                            bg=list(CARD_HI if text == "Anuluj" else ACCENT_DIM))
            b.bind(on_release=lambda _b, fn=fn: fn(
                {k: v.text.strip() for k, v in inputs.items()}, holder["pop"]))
            box.add_widget(b)
        sv = ScrollView(bar_color=ACCENT_DIM)
        sv.add_widget(box)
        holder["pop"] = RoundPopup(title=title, content=sv, size_hint=(0.94, 0.7))
        holder["pop"].open()

    # --- edycja tagów i usuwanie
    def edit_tags(self, t):
        if self.is_stream(t[0]):
            self.set_status("Można edytować tylko pobrane pliki")
            return

        def save(v, pop):
            pop.dismiss()
            try:
                f = mutagen.File(t[0], easy=True) if mutagen else None
                if f is None:
                    raise RuntimeError("ten format nie obsługuje tagów")
                if f.tags is None:
                    f.add_tags()
                f["title"] = v["title"]
                f["artist"] = v["artist"]
                f.save()
            except Exception as e:
                self.set_status(f"Nie zapisano w pliku ({e}) - zmieniono tylko w bibliotece")
            self.lib.set_tags(t[0], v["title"], v["artist"])
            self.set_status("Zapisano")
            self.refresh()
        self.form_popup("Edytuj utwór",
                        [("title", "Tytuł", t[1] or ""), ("artist", "Wykonawca", t[2] or "")],
                        [("Zapisz", save), ("Anuluj", lambda v, pop: pop.dismiss())])

    def confirm_delete(self, t):
        if self.is_stream(t[0]):
            return

        def delete(b):
            p = Path(t[0])
            if self.current_path() == t[0]:
                self.next()
            try:
                p.unlink()
                for extra in (p.with_suffix(".jpg"), p.with_suffix(".png")):
                    if extra.exists():
                        extra.unlink()
            except OSError as e:
                self.set_status(f"Nie można usunąć: {e}")
                return
            self.lib.forget_track(t[0])
            self.queue = [x for x in self.queue if x[0] != t[0]] or self.queue
            self.set_status(f"Usunięto: {t[1]}")
            self.refresh()
        self.list_popup(f"Usunąć plik?  {t[2] or '?'} - {t[1]}",
                        [{"text": "Tak, usuń plik z telefonu", "tap": delete}])

    # --- menu Więcej
    def show_more(self):
        onoff = lambda key: "wł." if self.lib.get_setting(key, "0") == "1" else "wył."
        alarm = (datetime.datetime.fromtimestamp(self.alarm_at).strftime("%H:%M")
                 if self.alarm_at else "wył.")
        rows = [
            ("Społeczność: czat, wspólna muzyka, profil" + (" (ADMIN)" if self.is_admin() else ""),
             lambda b: self.show_online()),
            ("Szukaj wszędzie (biblioteka, YouTube, radio)", lambda b: self.show_global_search()),
            (f"Wyślij na komputer / telewizor{' (' + self.cast.name + ')' if self.cast else ''}",
             lambda b: self.show_cast_menu()),
            ("Biblioteka w przeglądarce (komputer w tej samej sieci)",
             lambda b: self.show_web_info(False)),
            ("Radio z obecnego utworu", lambda b: self.active and self.radio_from(self.queue[self.qi])),
            ("Podsumowanie roku", lambda b: self.show_year()),
            ("Uzupełnij tagi całej biblioteki (MusicBrainz)", lambda b: self.mb_all()),
            ("Wyślij kopię (Dysk Google, e-mail...)", lambda b: self.backup_share()),
            ("Przywróć kopię z tekstu", lambda b: self.backup_restore()),
            ("Szukaj głosem", lambda b: self.voice_search()),
            (f"Potrząśnij = następny utwór: {onoff('potrzasanie')}", lambda b: self.toggle_shake()),
            (f"Tło w kolorze okładki: {'wł.' if self.lib.get_setting('tlo_okladka', '1') == '1' else 'wył.'}",
             lambda b: self.toggle_tint()),
            ("Quiz: Zgadnij utwór", lambda b: self.show_quiz()),
            ("Kafelki (gra pianino)", lambda b: self.show_tiles()),
            (f"Tryb imprezowy{' (włączony)' if self.party else ''}", lambda b: self.start_party()),
            (f"Płynne przejścia: {str(self.xf) + ' s' if self.xf else 'wył.'}",
             lambda b: self.cycle_xf()),
            ("Efekty w rytm muzyki (zgoda na mikrofon)", lambda b: self.ask_mic()),
        ] + ([("Wyłącz granie w tle (zamknij odtwarzacz)", lambda b: self.quit_background())]
             if self.apk else []) + [
            ("Pobierz z linku (film lub playlista)",
             lambda b: self.ask("Link YouTube", self.download_url)),
            ("Kanały YouTube", lambda b: self.show_channels()),
            ("Podcasty", lambda b: self.show_podcasts()),
            ("Statystyki", lambda b: self.show_stats()),
            ("Korektor dźwięku", lambda b: self.show_eq()),
            (f"Jakość pobierania: {self.lib.get_setting('jakosc', 'najlepsza')}",
             lambda b: self.toggle_quality()),
            (f"Auto-pobieranie nowości z kanałów: {onoff('auto_nowosci')}",
             lambda b: self.toggle_auto_news()),
            (f"Wyrównywanie głośności: {onoff('wyrownaj')}",
             lambda b: self.toggle_setting("wyrownaj", "Wyrównywanie głośności")),
            (f"Wizualizacja: {'wł.' if self.viz else 'wył.'}", lambda b: self.toggle_viz()),
            (f"Motyw: {self.lib.get_setting('motyw', 'Ciepły')}", lambda b: self.show_themes()),
            (f"Animacje: {'wł.' if ANIM['on'] else 'wył.'}", lambda b: self.toggle_anim()),
            (f"Efekty specjalne: {self.lib.get_setting('efekt', 'Świetliki')}",
             lambda b: self.show_fx_menu()),
            ("Tryb samochodowy", lambda b: self.car_mode()),
            (f"Budzik: {alarm}", lambda b: self.ask_alarm()),
            ("Eksportuj playlisty (M3U)", lambda b: self.export_m3u()),
            ("Importuj playlisty (M3U)", lambda b: self.import_m3u()),
            ("Kopia zapasowa biblioteki", lambda b: self.backup_db()),
            ("Przywróć kopię zapasową", lambda b: self.confirm_restore()),
            ("Skanuj bibliotekę", lambda b: self.scan()),
        ]
        self.list_popup("Więcej", [{"text": t, "tap": fn} for t, fn in rows])

    def toggle_setting(self, key, label):
        on = self.lib.get_setting(key, "0") != "1"
        self.lib.set_setting(key, "1" if on else "0")
        self.set_status(f"{label}: {'wł.' if on else 'wył.'}")
        return on

    def toggle_quality(self):
        q = "oszczędna" if self.lib.get_setting("jakosc", "najlepsza") == "najlepsza" else "najlepsza"
        self.lib.set_setting("jakosc", q)
        self.set_status(f"Jakość pobierania: {q}")

    def toggle_auto_news(self):
        if self.toggle_setting("auto_nowosci", "Auto-pobieranie nowości"):
            self.auto_news(init=True)

    def toggle_viz(self):
        self.viz = not self.viz
        anim(self, d=0.35, viz_k=1 if self.viz else 0)
        self.lib.set_setting("wizualizacja", "1" if self.viz else "0")

    def toggle_anim(self):
        ANIM["on"] = self.lib.get_setting("animacje", "1") != "1"
        self.lib.set_setting("animacje", "1" if ANIM["on"] else "0")
        self.setup_fx()
        self.set_status(f"Animacje: {'wł.' if ANIM['on'] else 'wył.'}")

    def show_themes(self):
        cur = self.lib.get_setting("motyw", "Ciepły")

        def hexc(c):
            return "".join(f"{int(x * 255):02x}" for x in c[:3])

        def choose(name):
            self.lib.set_setting("motyw", name)
            apply_theme(name)
            self.theme_now = resolve_theme(name)
            self.rebuild_ui()
            self.set_status(f"Motyw: {name}")
        rows = [{"text": f"[b]{AUTO_THEME}[/b]  dzień / wieczór / noc"
                         + ("  (obecny)" if cur == AUTO_THEME else ""),
                 "markup": True, "tap": lambda b: choose(AUTO_THEME)}]
        for n, t in THEMES.items():
            mark = "  (obecny)" if n == cur else ""
            rows.append({"text": f"[color={hexc(t['ACCENT'])}][b]{n}[/b][/color]"
                                 f"[color={hexc(t['MUTED'])}]{mark}[/color]",
                         "markup": True, "bg": list(t["CARD"]),
                         "tap": lambda b, n=n: choose(n)})
        self.list_popup(f"Motyw ({len(THEMES)})", rows)

    def on_start(self):
        self.setup_fx()
        self.show_splash()
        if self.lib.get_setting("potrzasanie", "0") == "1":
            self.setup_shake(True)

    def on_pause(self):
        self.in_bg = True
        self.autobackup()
        return True                             # muzyka gra dalej po wyjściu z aplikacji

    def setup_fx(self):
        """Tworzy warstwy efektów: tło pod interfejsem i wierzch nad nim."""
        for w in (self.fx_back, self.fx_front):
            if w is not None and w.parent:
                w.parent.remove_widget(w)
        mode = self.lib.get_setting("efekt", "Świetliki") if ANIM["on"] else "Wyłączone"
        self.fx_back = FxBack(mode=mode)
        self.fx_front = FxFront(border=self.lib.get_setting("neon", "1") == "1")
        Window.add_widget(self.fx_back, canvas="before")
        Window.add_widget(self.fx_front)

    def fx_tick(self, dt):
        self.player.fade_step()
        if self.fx_back is None:
            return
        playing = self.active and not self.player.paused
        lvl = 0.0
        if playing:
            lvl = self.player.level()
            if lvl is None:                     # bez pomiaru: symulowany rytm 118 BPM
                self.fx_t += dt
                pulse = abs(math.sin(self.fx_t * math.pi * 118 / 60)) ** 8
                lvl = 0.35 + 0.45 * pulse + random.uniform(0, 0.08)
        self.energy += (lvl - self.energy) * min(1.0, dt * 8)
        self.energy_avg += (self.energy - self.energy_avg) * min(1.0, dt * 1.5)
        now = time.time()
        if playing and self.energy > self.energy_avg * 1.18 + 0.03 and now - self.last_beat > 0.28:
            self.last_beat, self.beat = now, 1.0
        self.beat = max(0.0, self.beat - dt * 3.5)
        if ANIM["on"]:
            self.fx_back.update(dt, self.energy)
            self.fx_front.update(dt, self.beat, playing)

    def fx_at(self, wid, kind):
        """Efekt w miejscu przycisku lub paska."""
        if not ANIM["on"] or self.fx_front is None or not self.root:
            return
        w = self.root.ids.get(wid)
        if w is None or w.height < 2:
            return
        x, y = w.to_window(*w.center)
        f = self.fx_front
        if kind == "track":
            f.ring(x, y)
            f.burst(x, y, n=18, power=0.6, sparkle=True)
            f.flash_c.a = 0.07
        elif kind == "fav":
            f.burst(x, y, n=42)
        elif kind == "dl":
            f.burst(x, y, n=30, power=0.8)
            f.ring(x, y, maxr=dp(160))

    def show_fx_menu(self):
        cur = self.lib.get_setting("efekt", "Świetliki")

        def choose(m):
            self.lib.set_setting("efekt", m)
            self.setup_fx()
            if m != "Wyłączone":
                Clock.schedule_once(lambda dt: self.fx_front.burst(
                    Window.width / 2, Window.height / 2, n=60), 0.4)
            self.set_status(f"Efekt tła: {m}")
        rows = [{"text": ("> " if m == cur else "") + m, "tap": lambda b, m=m: choose(m)}
                for m in FX_MODES]
        neon = self.lib.get_setting("neon", "1") == "1"
        self.list_popup("Efekty specjalne", rows, [
            (f"Neonowa ramka: {'wł.' if neon else 'wył.'}", lambda b: self.toggle_neon())])

    def toggle_neon(self):
        on = self.lib.get_setting("neon", "1") != "1"
        self.lib.set_setting("neon", "1" if on else "0")
        if self.fx_front is not None:
            self.fx_front.border_on = on
        self.set_status(f"Neonowa ramka: {'wł.' if on else 'wył.'}")

    def rebuild_ui(self):
        """Buduje interfejs od nowa w nowych kolorach (bez restartu aplikacji)."""
        Builder.unload_file("muzyka_ui.kv")
        Window.clearcolor = BG
        old = self.root
        new = Builder.load_string(make_kv(), filename="muzyka_ui.kv")
        Window.remove_widget(old)
        self.root = new
        Window.add_widget(new)
        for w in new.walk():
            if isinstance(w, RoundSpinner):
                w.text = self.current_view
            elif isinstance(w, RoundToggle) and self.shuffle:
                w.state = "down"
        self.refresh()
        if self.active and not self.player.paused:
            self.pulse_start()
        self.setup_fx()

    # --- statystyki
    def show_stats(self):
        n, secs, plays = self.lib.totals()
        rows = [f"Utworów: {n}   |   łącznie {int(secs // 3600)} h {int(secs % 3600 // 60)} min",
                f"Odtworzeń: {plays}", "", "Najczęściej grane:"]
        rows += [f"{p}x   {a or '?'} - {t}" for t, a, p in self.lib.top_tracks()]
        rows += ["", "Najczęściej grani wykonawcy:"]
        rows += [f"{p}x   {a}" for a, p in self.lib.top_artists()]
        self.list_popup("Statystyki", [{"text": r, "tap": lambda b: None, "keep": True}
                                       for r in rows])

    # --- korektor
    def show_eq(self):
        try:
            names = self.player.eq_presets()
        except Exception as e:
            self.set_status(f"Korektor niedostępny: {e}")
            return
        if not names:
            self.set_status("Korektor działa tylko na Androidzie")
            return
        cur = self.player.eq_preset
        rows = [{"text": ("> " if cur == -1 else "") + "Wyłączony",
                 "tap": lambda b: self.set_eq(-1)},
                {"text": ("> " if cur == -2 else "") + "Własny (suwaki)",
                 "tap": lambda b: self.show_eq_custom()}]
        rows += [{"text": ("> " if cur == i else "") + n, "tap": lambda b, i=i: self.set_eq(i)}
                 for i, n in enumerate(names)]
        self.list_popup("Korektor", rows,
                        [(f"Bas: {self.player.bass // 10}%", lambda b: self.cycle_bass())])

    def set_eq(self, i):
        self.player.eq_preset = i
        self.player.apply_fx()
        self.lib.set_setting("eq", i)
        self.set_status("Korektor wyłączony" if i < 0 else "Korektor ustawiony")

    def cycle_bass(self):
        levels = [0, 330, 660, 1000]
        nxt = levels[(levels.index(self.player.bass) + 1) % 4] if self.player.bass in levels else 0
        self.player.bass = nxt
        self.player.apply_fx()
        self.lib.set_setting("bas", nxt)
        self.set_status(f"Wzmocnienie basu: {nxt // 10}%")

    # --- tryb samochodowy
    def car_mode(self):
        box = BoxLayout(orientation="vertical", spacing=dp(14), padding=dp(10))
        lbl = Label(text=self.now_text, font_size="30sp", bold=True, color=ACCENT,
                    halign="center", valign="middle")
        lbl.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0] - dp(20), None)))
        box.add_widget(lbl)
        row = BoxLayout(spacing=dp(12), size_hint_y=0.45)
        prev_b = RoundButton(text="|<", font_size="44sp")
        play_b = RoundButton(text=self.play_label, font_size="36sp", bg=list(ACCENT_DIM))
        next_b = RoundButton(text=">|", font_size="44sp")
        prev_b.bind(on_release=lambda *_: self.prev())
        play_b.bind(on_release=lambda *_: self.toggle())
        next_b.bind(on_release=lambda *_: self.next())
        for b in (prev_b, play_b, next_b):
            row.add_widget(b)
        box.add_widget(row)
        close = RoundButton(text="Zamknij", size_hint_y=None, height=dp(64), bg=list(CARD_HI))
        box.add_widget(close)
        pop = RoundPopup(title="Tryb samochodowy", content=box, size_hint=(1, 1))
        f1 = lambda a, v: setattr(lbl, "text", v)
        f2 = lambda a, v: setattr(play_b, "text", v)
        self.bind(now_text=f1, play_label=f2)
        pop.bind(on_dismiss=lambda *_: self.unbind(now_text=f1, play_label=f2))
        close.bind(on_release=lambda *_: pop.dismiss())
        pop.open()

    # --- budzik
    def ask_alarm(self):
        if self.alarm_at:
            self.list_popup("Budzik", [
                {"text": "Wyłącz budzik", "tap": lambda b: self.cancel_alarm()},
                {"text": "Ustaw inną godzinę", "tap": lambda b: self.ask(
                    "Godzina budzika (np. 07:30)", self.set_alarm)}])
        else:
            self.ask("Godzina budzika (np. 07:30)", self.set_alarm)

    def set_alarm(self, txt):
        m = re.match(r"^(\d{1,2})[:.](\d{2})$", txt.strip())
        if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
            self.set_status("Wpisz godzinę jak 07:30")
            return
        now = datetime.datetime.now()
        at = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        if at <= now:
            at += datetime.timedelta(days=1)
        self.alarm_at = at.timestamp()
        self.set_status(f"Budzik: {at:%H:%M} - aplikacja musi zostać otwarta")

    def cancel_alarm(self):
        self.alarm_at = None
        self.set_status("Budzik wyłączony")

    def tick_alarm(self):
        if self.alarm_at and time.time() >= self.alarm_at:
            self.alarm_at = None
            rows = list(self.lib.favorites() or self.lib.daily_mix())
            if not rows:
                self.set_status("Budzik: brak utworów")
                return
            random.shuffle(rows)
            self.player.vol = 0.05
            self.fade_in_start = time.time()
            self.queue, self.qi = rows, 0
            self.play_current()
            self.set_status("Budzik!")
        if self.fade_in_start is not None:
            k = (time.time() - self.fade_in_start) / 30     # 30 s narastania
            if k >= 1:
                self.fade_in_start = None
                self.player.set_volume(1.0)
            else:
                self.player.set_volume(0.05 + 0.95 * k)

    # --- M3U i kopia zapasowa
    def export_m3u(self):
        out = self.export_dir / "Playlisty"
        try:
            out.mkdir(parents=True, exist_ok=True)
            n = 0
            for pid, name in self.lib.playlists():
                lines = ["#EXTM3U"]
                for path, title, artist, _al, dur in self.lib.playlist_tracks(pid):
                    lines += [f"#EXTINF:{int(dur or 0)},{artist or '?'} - {title}", path]
                (out / f"{safe_name(name)}.m3u").write_text("\n".join(lines) + "\n",
                                                            encoding="utf-8")
                n += 1
            self.set_status(f"Wyeksportowano {n} playlist do {out}")
        except OSError as e:
            self.set_status(f"Błąd eksportu: {e}")

    def import_m3u(self):
        folder = self.export_dir / "Playlisty"
        files = sorted(folder.glob("*.m3u")) + sorted(folder.glob("*.m3u8"))
        if not files:
            self.set_status(f"Brak plików .m3u w {folder}")
            return
        known = {r[0] for r in self.lib.tracks()}
        added = 0
        for f in files:
            name = f.stem
            if name in self.SPECIAL:
                name += " (import)"
            have = set()
            pid = next((i for i, n in self.lib.playlists() if n == name), None)
            if pid is not None:
                have = {r[0] for r in self.lib.playlist_tracks(pid)}
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                path = line if line.startswith("/") else str((f.parent / line).resolve())
                if path in known and path not in have:
                    self.lib.add_to_playlist(name, path)
                    have.add(path)
                    added += 1
        self.set_status(f"Zaimportowano utworów do playlist: {added}")
        self.refresh()

    def backup_db(self):
        dest = self.export_dir / f"muzyka-kopia-{datetime.date.today().isoformat()}.db"
        try:
            dst = sqlite3.connect(str(dest))
            with self.lib.lock:
                self.lib.db.backup(dst)
            dst.close()
            self.set_status(f"Kopia zapisana: {dest}")
        except Exception as e:
            self.set_status(f"Błąd kopii: {e}")

    def confirm_restore(self):
        files = sorted(self.export_dir.glob("muzyka-kopia-*.db"))
        if not files:
            self.set_status(f"Brak kopii w {self.export_dir}")
            return
        f = files[-1]

        def restore(b):
            try:
                src = sqlite3.connect(str(f))
                with self.lib.lock:
                    src.backup(self.lib.db)
                src.close()
                self.set_status(f"Przywrócono: {f.name}")
                self.refresh()
            except Exception as e:
                self.set_status(f"Błąd przywracania: {e}")
        self.list_popup(f"Przywrócić {f.name}?",
                        [{"text": "Tak, zastąp obecną bibliotekę", "tap": restore}])

    # --- radio internetowe
    def radio_rows(self, query):
        params = {"limit": 50, "hidebroken": "true", "order": "clickcount", "reverse": "true"}
        if query:
            params["name"] = query
        else:
            params["countrycode"] = "PL"          # bez wpisanej nazwy: popularne polskie
        res, last = None, None
        for host in ("de1", "fi1", "all"):
            try:
                res = json.loads(http_get(f"https://{host}.api.radio-browser.info/json/stations/search?"
                                          + urllib.parse.urlencode(params)))
                break
            except Exception as e:
                last = e
        if res is None:
            raise last
        saved = self.lib.stations()
        saved_urls = {u for u, _, _ in saved}
        rows = []
        if not query:
            for u, name, icon in saved:
                rows.append({"text": f"{name}\nZapisana",
                             "tap": lambda b, u=u, n=name, i=icon: self.play_radio(u, n, i),
                             "side": "Usuń",
                             "side_fn": lambda b, u=u: (self.lib.remove_station(u),
                                                        self.set_status("Usunięto stację"))})
        for st in res:
            url = st.get("url_resolved") or st.get("url")
            if not url or (not query and url in saved_urls):
                continue
            name_, icon = st.get("name", "?").strip(), st.get("favicon") or ""
            info = "  ".join(x for x in (st.get("countrycode", ""),
                                         (st.get("tags") or "").replace(",", ", ")[:40],
                                         f"{st.get('bitrate') or '?'} kbps") if x)
            row = {"text": f"{name_}\n{info}",
                   "tap": lambda b, u=url, n=name_, i=icon: self.play_radio(u, n, i)}
            if url not in saved_urls:
                row["side"] = "Zapisz"
                row["side_fn"] = lambda b, u=url, n=name_, i=icon: (
                    self.lib.save_station(u, n, i), self.set_status(f"Zapisano: {n}"))
            rows.append(row)
        return rows

    def show_radio(self):
        self.live_search_popup("Radio", "Nazwa stacji - wyniki pojawiają się same",
                               self.radio_rows, empty_msg="Nie znaleziono stacji")

    def play_radio(self, url, name, icon):
        self.play_now(("radio:" + url, name, "Radio", icon or "", 0))

    # --- podcasty
    def show_podcasts(self):
        rows = [{"text": title, "tap": lambda b, u=u, t=title: self.open_podcast(u, t),
                 "side": "Usuń", "side_fn": lambda b, u=u: (self.lib.remove_podcast(u),
                                                            self.set_status("Usunięto podcast"))}
                for u, title, _img in self.lib.podcasts()]
        self.list_popup("Podcasty", rows, [
            ("Szukaj", lambda b: self.ask("Nazwa podcastu", self.search_podcasts)),
            ("Dodaj RSS", lambda b: self.ask("Link do kanału RSS",
                                             lambda u: self.open_podcast(u, u)))])

    def search_podcasts(self, term):
        self.set_status("Szukanie podcastów...")

        def work():
            url = ("https://itunes.apple.com/search?media=podcast&limit=25&"
                   + urllib.parse.urlencode({"term": term}))
            return json.loads(http_get(url)).get("results", [])

        def done(res):
            if isinstance(res, Exception):
                self.show_error(res, "Błąd wyszukiwania")
                return
            rows = []
            for r in res:
                feed = r.get("feedUrl")
                if not feed:
                    continue
                title, img = r.get("collectionName", "?"), r.get("artworkUrl600") or ""
                rows.append({"text": f"{title}\n{r.get('artistName', '')}",
                             "tap": lambda b, f=feed, t=title: self.open_podcast(f, t),
                             "side": "Zapisz",
                             "side_fn": lambda b, f=feed, t=title, i=img: (
                                 self.lib.save_podcast(f, t, i),
                                 self.set_status(f"Zapisano: {t}"))})
            self.set_status(f"Podcastów: {len(rows)}")
            self.list_popup("Wyniki podcastów", rows)
        self.run_bg(work, done)

    def open_podcast(self, feed, title):
        self.set_status("Wczytywanie odcinków...")
        itunes = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

        def work():
            root = ET.fromstring(http_get(feed, timeout=30))
            ch = root.find("channel")
            if ch is None:
                raise RuntimeError("to nie jest kanał RSS podcastu")
            ptitle = (ch.findtext("title") or title).strip()
            img_el = ch.find(itunes + "image")
            image = img_el.get("href") if img_el is not None else (ch.findtext("image/url") or "")
            eps = []
            for it in ch.findall("item")[:60]:
                enc = it.find("enclosure")
                if enc is None or not enc.get("url"):
                    continue
                eps.append({"title": (it.findtext("title") or "?").strip(),
                            "url": enc.get("url"),
                            "date": (it.findtext("pubDate") or "")[:16],
                            "dur": parse_duration(it.findtext(itunes + "duration") or 0)})
            return ptitle, image, eps

        def done(res):
            if isinstance(res, Exception):
                self.show_error(res, "Błąd podcastu")
                return
            ptitle, image, eps = res
            rows = []
            for e in eps:
                ext = Path(urllib.parse.urlparse(e["url"]).path).suffix or ".mp3"
                dest = self.export_dir / "Podcasty" / safe_name(ptitle) / (safe_name(e["title"]) + ext)
                t = (e["url"], e["title"], ptitle, image, e["dur"])
                rows.append({"text": f"{e['title']}\n{e['date']}   [{fmt(e['dur'])}]",
                             "tap": lambda b, e=e, d=dest: self.download(
                                 e["url"], b, kind="file", title=e["title"], dest=str(d)),
                             "keep": True,
                             "sides": [("Graj", lambda b, t=t: self.play_now(t))]})
            saved = any(u == feed for u, _, _ in self.lib.podcasts())
            footer = [] if saved else [("Zapisz podcast", lambda b: (
                self.lib.save_podcast(feed, ptitle, image), self.set_status(f"Zapisano: {ptitle}")))]
            self.set_status("Dotknij odcinka, aby pobrać; Graj - słuchaj od razu")
            self.list_popup(ptitle, rows, footer)
        self.run_bg(work, done)

    # --- tekst: słowa pojawiają się w różnych miejscach
    def lyric_query(self, t):
        title, artist = clean_title(t[1] or ""), clean_artist(t[2] or "")
        if artist in ("", "Nieznany wykonawca", "YouTube") or self.is_youtube(t[0]):
            if " - " in title:
                artist, title = [x.strip() for x in title.split(" - ", 1)]
        return artist, clean_title(title)

    def show_lyrics(self, karaoke=False):
        if not self.active:
            self.set_status("Nic nie gra")
            return
        box = BoxLayout(orientation="vertical", spacing=dp(6))
        area = FloatLayout()
        ly_fx = FxFront(border=False, size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        area.add_widget(ly_fx)
        kbox = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10),
                         size_hint=(1, 1), pos_hint={"x": 0, "y": 0},
                         opacity=1 if karaoke else 0)
        klabels = []
        for k in range(4):
            if k == 1:
                lb = WordLabel(markup=True, font_size="26sp", bold=True, halign="center",
                               valign="middle", size_hint_y=1.6)
            else:
                lb = Label(color=MUTED, font_size="17sp", halign="center", valign="middle",
                           opacity=0.55 if k == 0 else 0.8 - 0.25 * (k - 2))
            lb.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0] - dp(10), None)))
            kbox.add_widget(lb)
            klabels.append(lb)
        area.add_widget(kbox)
        msg = Label(text="", color=MUTED, font_size="15sp",
                    pos_hint={"center_x": 0.5, "center_y": 0.5})
        area.add_widget(msg)
        box.add_widget(area)
        bar = BoxLayout(size_hint_y=None, height=dp(56))
        minus = RoundButton(text="-0.5 s", size_hint_x=0.7, font_size="13sp")
        start = RoundButton(text="Start śpiewu", bg=list(ACCENT_DIM), font_size="13sp")
        plus = RoundButton(text="+0.5 s", size_hint_x=0.7, font_size="13sp")
        kbtn = RoundButton(text="Słowa" if karaoke else "Karaoke", font_size="13sp")
        tbtn = RoundButton(text="tekstowo", font_size="13sp")
        close = RoundButton(text="Zamknij", size_hint_x=0.8, bg=list(CARD_HI), font_size="13sp")
        for b in (minus, start, plus, kbtn, tbtn, close):
            bar.add_widget(b)
        tbtn.bind(on_release=lambda *_: self.open_tekstowo())
        kbtn.bind(on_release=lambda b: self.ly_toggle_mode(b))
        box.add_widget(bar)
        minus.bind(on_release=lambda *_: self.ly_shift(-0.5))
        plus.bind(on_release=lambda *_: self.ly_shift(0.5))
        start.bind(on_release=lambda *_: self.ly_mark_start())
        pop = RoundPopup(title=self.now_text, content=box, size_hint=(1, 1))
        self.ly = {"area": area, "msg": msg, "pop": pop, "words": [], "tl": [], "times": [],
                   "i": 0, "line": None, "last": 0.0, "last_word": 0.0, "path": None,
                   "off": 0.0, "fx": ly_fx, "mode": "karaoke" if karaoke else "slowa",
                   "kbox": kbox, "kl": klabels, "klines": [], "kstarts": [], "kcur": None}
        ev = Clock.schedule_interval(self.ly_tick, 1 / 20)

        def closed(*_):
            ev.cancel()
            self.ly = None
        pop.bind(on_dismiss=closed)
        close.bind(on_release=lambda *_: pop.dismiss())
        pop.open()
        self.ly_load()

    def ly_load(self):
        ly = self.ly
        t = self.queue[self.qi]
        ly["path"] = t[0]
        self.ly_fade(list(ly["words"]))
        ly.update(tl=[], times=[], i=0, line=None, last=0.0, klines=[], kstarts=[], kcur=None)
        for lb in ly["kl"]:
            lb.text = ""
        ly["off"] = float(self.lib.get_setting(self.ly_key(t[0]), "0"))
        self.ly_title()
        if self.is_radio(t[0]):
            ly["msg"].text = "Radio nie ma tekstu"
            return
        ly["msg"].text = "Szukanie tekstu..."
        artist, title = self.lyric_query(t)
        dur = self.player.duration() or t[4]
        path = t[0]

        def work():
            text, synced, ldur = fetch_lyrics(artist, title, dur,
                                              Path(self.user_data_dir) / "teksty", path)
            return (lyric_timeline(text, synced, dur) if text else []), synced, ldur

        def done(res):
            if self.ly is not ly or ly["path"] != path:
                return                       # okno zamknięte albo inny utwór
            if isinstance(res, Exception):
                ly["msg"].text = "Nie udało się pobrać tekstu"
                return
            tl, synced, ldur = res
            if not tl:
                ly["msg"].text = "Brak tekstu dla tego utworu"
                return
            ly["msg"].text = "" if synced else "(czas słów przybliżony)"
            ly["tl"], ly["times"] = tl, [x[0] for x in tl]
            ly["i"] = bisect.bisect_left(ly["times"], self.ly_pos())
            groups = {}
            for t_, w, li in tl:
                groups.setdefault(li, []).append((t_, w))
            kl = sorted((ws[0][0], ws) for ws in groups.values())
            ly["klines"], ly["kstarts"], ly["kcur"] = kl, [k[0] for k in kl], None
            if synced and ldur and dur - ldur > 5 and not ly["off"]:
                self.set_status("Ta wersja ma chyba wstęp - dotknij Start śpiewu, "
                                "gdy zacznie się śpiew")
        self.run_bg(work, done)

    def ly_tick(self, _dt):
        ly = self.ly
        if not ly:
            return
        ly["fx"].update(1 / 20)
        if self.active and self.current_path() != ly["path"]:
            self.ly_load()                   # zmienił się utwór
            return
        if not ly["tl"] or not self.active:
            return
        pos = self.ly_pos()
        if ly["mode"] == "karaoke":
            self.karaoke_update(pos)
            ly["last"] = pos
            return
        if pos < ly["last"] - 1 or pos > ly["last"] + 4:     # przewinięcie
            self.ly_fade(list(ly["words"]))
            ly["i"] = bisect.bisect_left(ly["times"], pos)
            ly["line"] = None
        while ly["i"] < len(ly["tl"]) and ly["tl"][ly["i"]][0] <= pos:
            _t, word, line = ly["tl"][ly["i"]]
            if line != ly["line"]:
                self.ly_fade(list(ly["words"]))
                ly["line"] = line
            self.ly_spawn(word)
            ly["last_word"] = pos
            ly["i"] += 1
        if ly["words"] and pos - ly["last_word"] > 5:       # przerwa w śpiewie
            self.ly_fade(list(ly["words"]))
        ly["last"] = pos

    def karaoke_update(self, pos):
        ly = self.ly
        kl = ly["klines"]
        if not kl:
            return
        i = bisect.bisect_right(ly["kstarts"], pos) - 1
        prev_l, cur_l, n1, n2 = ly["kl"]

        def text(j):
            return " ".join(w for _, w in kl[j][1]) if 0 <= j < len(kl) else ""
        if i != ly["kcur"]:
            ly["kcur"] = i
            prev_l.text, n1.text, n2.text = text(i - 1), text(i + 1), text(i + 2)
            if ANIM["on"] and i >= 0:
                cur_l.wscale = 0.85
                anim(cur_l, d=0.35, t="out_back", wscale=1)
                Clock.schedule_once(lambda dt: ly["fx"].burst(
                    cur_l.center_x, cur_l.center_y, n=8, power=0.5, sparkle=True), 0.05)
        if i < 0:
            cur_l.text = "..."
            return
        hexa = "".join(f"{int(c * 255):02x}" for c in ACCENT[:3])
        words = kl[i][1]
        done = " ".join(escape_markup(w) for t_, w in words if t_ <= pos)
        rest = " ".join(escape_markup(w) for t_, w in words if t_ > pos)
        cur_l.text = (f"[color={hexa}]{done}[/color] " if done else "") + rest

    @staticmethod
    def slug(s):
        import unicodedata
        s = s.replace("ł", "l").replace("Ł", "L")
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

    def open_tekstowo(self):
        """Otwiera stronę utworu na tekstowo.pl w przeglądarce (tekst i tłumaczenie)."""
        if not self.active:
            return
        artist, title = self.lyric_query(self.queue[self.qi])
        page = f"https://www.tekstowo.pl/{self.slug(artist)}/{self.slug(title)}"
        search = ("https://www.google.com/search?q=" +
                  urllib.parse.quote_plus(f"site:tekstowo.pl {artist} {title}"))

        def work():
            req = urllib.request.Request(page, method="HEAD", headers=UA)
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status == 200

        def done(ok):
            open_external(page if ok is True else search)
        if artist and title:
            self.run_bg(work, done)
        else:
            open_external(search)

    def ly_toggle_mode(self, btn):
        ly = self.ly
        if not ly:
            return
        kar = ly["mode"] != "karaoke"
        ly["mode"] = "karaoke" if kar else "slowa"
        btn.text = "Słowa" if kar else "Karaoke"
        self.ly_fade(list(ly["words"]))
        anim(ly["kbox"], d=0.3, opacity=1 if kar else 0)
        ly["kcur"], ly["line"] = None, None
        ly["i"] = bisect.bisect_left(ly["times"], self.ly_pos()) if ly["times"] else 0

    LY_LEAD = 0.15        # słowo startuje odrobinę wcześniej, bo pojawia się z animacją

    @staticmethod
    def ly_key(path):
        return "lyoff:" + hashlib.md5(path.encode()).hexdigest()

    def ly_pos(self):
        off = self.ly["off"] if self.ly else 0.0
        return self.player.position() - off + self.LY_LEAD

    def ly_title(self):
        ly = self.ly
        off = ly["off"]
        ly["pop"].title = self.now_text + (f"   (przesunięcie {off:+.1f} s)" if off else "")

    def ly_resync(self):
        ly = self.ly
        self.ly_fade(list(ly["words"]))
        ly["i"] = bisect.bisect_left(ly["times"], self.ly_pos())
        ly["line"] = None
        ly["last"] = self.ly_pos()
        self.lib.set_setting(self.ly_key(ly["path"]), round(ly["off"], 2))
        self.ly_title()

    def ly_shift(self, delta):
        """Plus = tekst później, minus = wcześniej."""
        if not self.ly or not self.ly["tl"]:
            return
        self.ly["off"] += delta
        self.ly_resync()

    def ly_mark_start(self):
        """Dotknięte w chwili, gdy zaczyna się śpiew: pierwsze słowo = teraz."""
        if not self.ly or not self.ly["tl"]:
            return
        self.ly["off"] = self.player.position() - self.ly["tl"][0][0]
        self.ly_resync()
        self.set_status("Tekst dopasowany do początku śpiewu")

    def ly_spawn(self, word):
        ly = self.ly
        area = ly["area"]
        lbl = WordLabel(text=word, font_size=sp(random.choice((22, 26, 30, 34, 40, 48))),
                        bold=random.random() < 0.5,
                        color=random.choice((ACCENT, TEXT, TEXT, MUTED)),
                        size_hint=(None, None), opacity=0,
                        angle=random.choice((0, 0, 0, -8, 8, -4, 4)), wscale=0.4)
        lbl.texture_update()
        lbl.size = lbl.texture_size
        best = None
        for _ in range(14):                  # miejsce, gdzie najmniej zasłania inne słowa
            x = random.uniform(area.x + dp(8), max(area.x + dp(8), area.right - lbl.width - dp(8)))
            y = random.uniform(area.y + dp(8), max(area.y + dp(8), area.top - lbl.height - dp(8)))
            cx, cy = x + lbl.width / 2, y + lbl.height / 2
            hits = sum(1 for w in ly["words"]
                       if abs(w.center_x - cx) < (w.width + lbl.width) / 2
                       and abs(w.center_y - cy) < (w.height + lbl.height) / 2)
            if best is None or hits < best[0]:
                best = (hits, x, y)
            if hits == 0:
                break
        lbl.pos = best[1], best[2]
        area.add_widget(lbl)
        anim(lbl, d=0.4, t="out_back", wscale=1)
        anim(lbl, d=0.25, opacity=1)
        ly["words"].append(lbl)
        ly["fx"].burst(lbl.center_x, lbl.center_y, n=10, power=0.35, sparkle=True)
        if len(ly["words"]) > 16:
            self.ly_fade(ly["words"][:len(ly["words"]) - 16])

    def ly_fade(self, words):
        ly = self.ly
        for w in words:
            if ly and w in ly["words"]:
                ly["words"].remove(w)
            if not ANIM["on"]:
                if w.parent:
                    w.parent.remove_widget(w)
                continue
            Animation.cancel_all(w)
            a = Animation(opacity=0, wscale=1.3, d=0.45, t="in_quad")
            a.bind(on_complete=lambda _a, wd: wd.parent and wd.parent.remove_widget(wd))
            a.start(w)

    # --- wysyłanie na komputer / telewizor
    def ensure_web(self):
        if self.web is None:
            self.web = LeoxWeb(self)
        return self.web

    def show_web_info(self, receiver):
        try:
            web = self.ensure_web()
        except Exception as e:
            self.set_status(f"Serwer nie ruszył: {e}")
            return
        url = web.base + ("/odbiornik" if receiver else "/biblioteka")
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(8))
        try:
            import qrcode
            qr = qrcode.QRCode(border=2)
            qr.add_data(url)
            qr.make(fit=True)
            box.add_widget(QRWidget(qr.get_matrix(), size_hint_y=None, height=dp(220)))
        except Exception:
            pass
        box.add_widget(Label(text=url, font_size="18sp", bold=True, color=ACCENT,
                             size_hint_y=None, height=dp(36)))
        txt = ("Otwórz ten adres na komputerze (ta sama sieć Wi-Fi) i kliknij Połącz. "
               "Od teraz muzyka gra na komputerze, a telefon jest pilotem."
               if receiver else
               "Otwórz ten adres na komputerze w tej samej sieci Wi-Fi - zobaczysz bibliotekę "
               "telefonu i możesz jej słuchać w przeglądarce.")
        info = Label(text=txt, color=MUTED, halign="center", size_hint_y=None)
        info.bind(width=lambda w, v: setattr(w, "text_size", (v - dp(10), None)),
                  texture_size=lambda w, v: setattr(w, "height", v[1]))
        box.add_widget(info)
        state = Label(text="", color=ACCENT, size_hint_y=None, height=dp(28))
        box.add_widget(state)
        box.add_widget(Widget())
        close = RoundButton(text="Zamknij", size_hint_y=None, height=dp(56), bg=list(CARD_HI))
        box.add_widget(close)
        pop = RoundPopup(title="Komputer" if receiver else "Biblioteka w przeglądarce",
                         content=box, size_hint=(0.95, 0.85))

        def watch(_dt):
            if receiver:
                ok = time.time() - web.rx["seen"] < 5
                state.text = "Komputer połączony" if ok else "Czekam na komputer..."
        ev = Clock.schedule_interval(watch, 1)
        pop.bind(on_dismiss=lambda *_: ev.cancel())
        close.bind(on_release=lambda *_: pop.dismiss())
        pop.open()

    def show_cast_menu(self):
        rows = []
        if self.cast:
            rows.append({"text": f"Zakończ wysyłanie ({self.cast.name})",
                         "tap": lambda b: self.stop_cast()})
        rows.append({"text": "Komputer (przeglądarka)\nTa sama sieć Wi-Fi, bez instalowania",
                     "tap": lambda b: self.cast_to_pc()})
        self.set_status("Szukanie telewizorów i głośników w sieci...")

        def done(devs):
            devs = devs if isinstance(devs, list) else []
            for d in devs:
                rows.append({"text": f"{d['name']}\nTelewizor / głośnik (DLNA)",
                             "tap": lambda b, d=d: self.start_cast(CastDLNA(d))})
            self.set_status(f"Znalezione urządzenia DLNA: {len(devs)}")
            self.list_popup("Wyślij na...", rows)
        self.run_bg(ssdp_discover, done)

    def cast_to_pc(self):
        try:
            web = self.ensure_web()
        except Exception as e:
            self.set_status(f"Serwer nie ruszył: {e}")
            return
        self.start_cast(CastPC(self, web))
        self.show_web_info(True)

    def start_cast(self, target):
        pos, was = (self.cur_position() if self.active else 0), self.active
        if self.cast:
            self.cast.stop()
        elif self.active:
            self.player.stop()
        self.cast, self.cast_paused = target, False
        self.set_status(f"Wysyłanie na: {target.name}")
        if was and self.queue:
            self.cast_play(self.queue[self.qi], pos)

    def cast_play(self, t, pos=0):
        self.cast_track += 1
        tid, path = self.cast_track, t[0]
        self.cast_paused, self.cast_end_handled = False, False
        if not self.is_stream(path):
            try:
                self.ensure_web()
            except Exception as e:
                self.set_status(f"Serwer nie ruszył: {e}")
                return
        self.now_text = f"Wysyłanie: {t[1]}"

        def work():
            if self.is_radio(path):
                return path[len("radio:"):]
            if self.is_youtube(path):
                import yt_dlp
                opts = {"quiet": True, "logger": QUIET, "no_warnings": True, "noplaylist": True,
                        "format": "bestaudio[ext=m4a]/bestaudio/best"}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(path, download=False)["url"]
            if self.is_stream(path):
                return path
            return self.web.file_url(path)

        def done(url):
            if tid != self.cast_track or not self.cast:
                return
            if isinstance(url, Exception):
                self.show_error(url, "Błąd wysyłania")
                return
            cover = self.stream_cover(t)
            if cover is None:
                cover = self.web.cover_url(path) if self.web else ""
            self.cast.play(url, t, pos, tid, cover)
            self.cast_started = time.time()
            self.after_start(t, cover=self.stream_cover(t))
        self.run_bg(work, done)

    def cast_tick(self):
        st = self.cast.status()
        if not self.active:
            return
        d = st.get("dur") or 0
        self.pos, self.dur = st.get("pos", 0), max(d, 1)
        self.pos_text, self.dur_text = fmt(self.pos), fmt(d)
        if (st.get("ended") and not self.cast_end_handled
                and time.time() - self.cast_started > 3):
            self.cast_end_handled = True
            self.next(auto=True)

    def stop_cast(self):
        target, self.cast = self.cast, None
        if not target:
            return
        pos = target.status().get("pos", 0)
        target.stop()
        self.set_status("Wysyłanie zakończone - gra telefon")
        if self.active and self.queue:
            self.play_current()
            if pos > 3:
                Clock.schedule_once(lambda dt: self.seek(pos), 1.5)

    # --- radio z utworu
    def radio_from(self, t):
        self.set_status("Tworzenie radia z utworu...")

        def work():
            import yt_dlp
            vid = None
            if self.is_youtube(t[0]):
                m = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", t[0])
                vid = m.group(1) if m else None
            if not vid:
                q = f"{t[2] or ''} {t[1] or ''}".strip()
                with yt_dlp.YoutubeDL({"quiet": True, "logger": QUIET, "extract_flat": True,
                                       "no_warnings": True}) as ydl:
                    ents = ydl.extract_info(f"ytsearch1:{q}", download=False).get("entries") or []
                vid = ents[0].get("id") if ents else None
            if not vid:
                raise RuntimeError("nie znaleziono utworu na YouTube")
            with yt_dlp.YoutubeDL({"quiet": True, "logger": QUIET, "no_warnings": True,
                                   "extract_flat": "in_playlist", "playlistend": 50}) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}&list=RD{vid}",
                                        download=False)
            return vid, [self.entry(e) for e in info.get("entries") or [] if e.get("id")]

        def done(res):
            if isinstance(res, Exception):
                self.show_error(res, "Błąd radia z utworu")
                return
            vid, vids = res
            items = [(v["url"], clean_title(v["title"]), clean_artist(v["channel"]), "YouTube", v["dur"])
                     for v in vids if v["id"] != vid or not self.active]
            if not items:
                self.set_status("YouTube nie zwrócił podobnych utworów")
                return
            if self.active:
                self.queue = self.queue[:self.qi + 1] + items
                self.sync_queue()
                self.refresh()
            else:
                self.queue, self.qi = items, 0
                self.play_current()
            self.set_status(f"Radio z utworu: {len(items)} podobnych w kolejce")
        self.run_bg(work, done)

    # --- własny korektor
    def show_eq_custom(self):
        try:
            info = self.player.eq_info()
        except Exception as e:
            info, err = None, e
        else:
            err = None
        if not info:
            self.set_status(f"Korektor niedostępny{': ' + str(err) if err else ' (tylko Android)'}")
            return
        n, (lo, hi), freqs = info
        bands = list(self.player.eq_bands) if len(self.player.eq_bands) == n else [0] * n
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        sliders = []
        for i in range(n):
            row = BoxLayout(size_hint_y=None, height=dp(48))
            f = freqs[i]
            row.add_widget(Label(text=f"{f // 1000} kHz" if f >= 1000 else f"{f} Hz",
                                 size_hint_x=None, width=dp(70), color=MUTED))
            sl = ThemedSlider(min=lo, max=hi, value=bands[i])
            val = Label(text=f"{bands[i] / 100:+.0f} dB", size_hint_x=None, width=dp(60))
            sl.bind(value=lambda w, v, lb=val: setattr(lb, "text", f"{v / 100:+.0f} dB"))
            sl.bind(on_touch_up=lambda w, t_: w.collide_point(*t_.pos) and apply())
            row.add_widget(sl)
            row.add_widget(val)
            box.add_widget(row)
            sliders.append(sl)

        def apply(*_):
            self.player.eq_bands = [int(sl.value) for sl in sliders]
            self.player.eq_preset = -2
            self.player.apply_fx()
            self.lib.set_setting("eq", -2)
            self.lib.set_setting("eq_bands", json.dumps(self.player.eq_bands))
        box.add_widget(Widget())
        bar = BoxLayout(size_hint_y=None, height=dp(56))
        zero = RoundButton(text="Wyzeruj", bg=list(ACCENT_DIM))
        zero.bind(on_release=lambda *_: ([setattr(sl, "value", 0) for sl in sliders], apply()))
        close = RoundButton(text="Zamknij", bg=list(CARD_HI))
        bar.add_widget(zero)
        bar.add_widget(close)
        box.add_widget(bar)
        pop = RoundPopup(title="Korektor własny", content=box, size_hint=(0.95, 0.8))
        close.bind(on_release=lambda *_: pop.dismiss())
        pop.open()
        apply()

    # --- podsumowanie roku
    def show_year(self):
        year = datetime.date.today().year
        s_ = self.lib.year_summary(year)
        if not s_["plays"]:
            self.set_status("Podsumowanie zbiera dane od tej wersji - posłuchaj trochę muzyki")
            return
        tops = s_["top_tracks"]
        cards = [("Twój rok", str(year), "w Leox Player", ""),
                 ("Słuchałeś przez", s_["minutes"], "minut", ""),
                 ("Odtworzenia", s_["plays"], f"{s_['distinct']} różnych utworów", ""),
                 ("Utwór roku", tops[0][0][0], tops[0][0][1] + f"   ({tops[0][1]}x)",
                  "\n".join(f"{i + 2}. {t[0]} - {t[1]}" for i, (t, _) in enumerate(tops[1:]))),
                 ("Wykonawca roku", s_["top_artists"][0][0], f"{s_['top_artists'][0][1]} odtworzeń",
                  "\n".join(f"{i + 2}. {a}" for i, (a, _) in enumerate(s_["top_artists"][1:]))),
                 ("Twoja godzina", f"{s_['hour']}:00" if s_["hour"] is not None else "-",
                  "o tej porze słuchasz najczęściej", ""),
                 ("To był dobry rok", ":)", "Dziękujemy, że słuchasz z Leox Player", "")]
        root = FloatLayout()
        box = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12),
                        size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        root.add_widget(box)
        fx = FxFront(border=False)
        root.add_widget(fx)
        small = Label(color=MUTED, font_size="18sp", size_hint_y=None, height=dp(40))
        big = WordLabel(font_size="56sp", bold=True, color=ACCENT, halign="center", valign="middle")
        big.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0] - dp(10), None)))
        sub = Label(font_size="17sp", halign="center", size_hint_y=None, height=dp(60))
        sub.bind(width=lambda w, v: setattr(w, "text_size", (v - dp(10), None)))
        extra = Label(color=MUTED, font_size="14sp", halign="center", valign="top")
        extra.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0] - dp(10), None)))
        for w in (Widget(size_hint_y=0.2), small, big, sub, extra):
            box.add_widget(w)
        bar = BoxLayout(size_hint_y=None, height=dp(56))
        back = RoundButton(text="Wstecz", bg=list(CARD_HI))
        fwd = RoundButton(text="Dalej", bg=list(ACCENT_DIM))
        bar.add_widget(back)
        bar.add_widget(fwd)
        box.add_widget(bar)
        pop = RoundPopup(title="Podsumowanie roku", content=root, size_hint=(1, 1))
        st = {"i": 0, "ev": None}

        def show(i):
            st["i"] = i
            c = cards[i]
            small.text, sub.text, extra.text = c[0], c[2], c[3]
            fwd.text = "Zamknij" if i == len(cards) - 1 else "Dalej"
            if st["ev"]:
                st["ev"].cancel()
            if isinstance(c[1], int) and ANIM["on"]:          # licznik nabija się do wyniku
                t0, target = time.time(), c[1]

                def count(_dt):
                    k = min(1.0, (time.time() - t0) / 1.2)
                    big.text = f"{int(target * (1 - (1 - k) ** 3)):,}".replace(",", " ")
                    return k < 1
                st["ev"] = Clock.schedule_interval(count, 1 / 30)
            else:
                big.text = f"{c[1]:,}".replace(",", " ") if isinstance(c[1], int) else str(c[1])
            if ANIM["on"]:
                box.opacity, big.wscale = 0, 0.6
                anim(box, d=0.35, opacity=1)
                anim(big, d=0.5, t="out_back", wscale=1)
            if i == len(cards) - 1 or i == 3:
                Clock.schedule_once(lambda dt: fx.burst(Window.width / 2, Window.height * 0.55,
                                                        n=70), 0.3)
        back.bind(on_release=lambda *_: st["i"] > 0 and show(st["i"] - 1))
        fwd.bind(on_release=lambda *_: pop.dismiss() if st["i"] == len(cards) - 1
                 else show(st["i"] + 1))
        ev = Clock.schedule_interval(lambda dt: fx.update(dt), 1 / 30)
        def closed(*_):
            ev.cancel()
            if st["ev"]:
                st["ev"].cancel()
        pop.bind(on_dismiss=closed)
        pop.open()
        show(0)

    # --- MusicBrainz
    def apply_mb(self, path, info, cover):
        try:
            if mutagen:
                f = mutagen.File(path, easy=True)
                if f is not None:
                    if f.tags is None:
                        f.add_tags()
                    f["title"], f["artist"] = info["title"], info["artist"]
                    if info["album"]:
                        f["album"] = info["album"]
                    f.save()
        except Exception:
            pass
        if cover:
            jpg = Path(path).with_suffix(".jpg")
            try:
                if not jpg.exists():
                    jpg.write_bytes(cover)
            except OSError:
                pass
        self.lib.set_tags(path, info["title"], info["artist"])
        if info["album"]:
            self.lib.set_album(path, info["album"])

    def mb_track(self, t):
        if self.is_stream(t[0]):
            self.set_status("Tagi można uzupełnić tylko w pobranych plikach")
            return
        self.set_status("Szukanie w MusicBrainz...")
        artist, title = self.lyric_query(t)

        def work():
            info = mb_lookup(artist, title)
            return (info, caa_cover(info)) if info else (None, None)

        def done(res):
            if isinstance(res, Exception):
                self.show_error(res, "Błąd MusicBrainz")
                return
            info, cover = res
            if not info:
                self.set_status("MusicBrainz nie zna tego utworu")
                return
            desc = (f"{info['artist']} - {info['title']}\nAlbum: {info['album'] or '-'}   "
                    f"zgodność {info['score']}%" + ("   + okładka" if cover else ""))
            self.list_popup("Znaleziono w MusicBrainz", [
                {"text": desc, "tap": lambda b: None, "keep": True, "bg": [0, 0, 0, 0], "h": 90},
                {"text": "Zapisz te dane w pliku",
                 "tap": lambda b: (self.apply_mb(t[0], info, cover), self.refresh(),
                                   self.set_status("Tagi uzupełnione"))}])
        self.run_bg(work, done)

    def mb_all(self):
        todo = [r for r in self.lib.tracks() if not r[2] or not r[3]]
        if not todo:
            self.set_status("Wszystkie utwory mają wykonawcę i album")
            return
        self.set_status(f"MusicBrainz: sprawdzam {len(todo)} utworów (ok. 1 na sekundę)...")

        def work():
            done_n = 0
            for i, r in enumerate(todo):
                try:
                    info = mb_lookup(*self.lyric_query(r))
                    if info and info["score"] >= 90:
                        self.apply_mb(r[0], info, caa_cover(info))
                        done_n += 1
                except Exception:
                    pass
                Clock.schedule_once(lambda dt, i=i, d=done_n: self.set_status(
                    f"MusicBrainz: {i + 1}/{len(todo)}, uzupełniono {d}"))
                time.sleep(1.1)                 # limit MusicBrainz: 1 zapytanie na sekundę
            return done_n

        def done(res):
            self.refresh()
            self.set_status(f"MusicBrainz: uzupełniono {res if isinstance(res, int) else 0} utworów "
                            "(tylko pewne dopasowania, od 90%)")
        self.run_bg(work, done)

    # --- kopia przez udostępnianie
    def backup_payload(self):
        def ta(rows):
            return [[r[1] or "", r[2] or ""] for r in rows]
        return json.dumps({
            "leox": 1,
            "playlists": {n: ta(self.lib.playlist_tracks(pid)) for pid, n in self.lib.playlists()},
            "favorites": ta(self.lib.favorites()),
            "channels": [list(c) for c in self.lib.channels()],
            "stations": [list(c) for c in self.lib.stations()],
            "podcasts": [list(c) for c in self.lib.podcasts()],
        }, ensure_ascii=False, separators=(",", ":"))

    def backup_share(self):
        data = self.backup_payload()
        try:
            share_text(data, f"Leox Player - kopia {datetime.date.today().isoformat()}")
            self.set_status("Wybierz, gdzie zapisać kopię (np. Dysk Google)")
        except Exception:
            out = self.export_dir / f"leox-kopia-{datetime.date.today().isoformat()}.json"
            try:
                out.write_text(data, encoding="utf-8")
                self.set_status(f"Kopia zapisana: {out}")
            except OSError as e:
                self.set_status(f"Nie udało się zapisać kopii: {e}")

    def backup_restore(self):
        def go(v, pop):
            try:
                d = json.loads(v["data"])
                assert d.get("leox") == 1
            except Exception:
                self.set_status("To nie jest kopia Leox Player")
                return
            pop.dismiss()
            n = self.apply_backup(d)
            self.refresh()
            self.set_status(f"Przywrócono: {n} pozycji playlist i ulubionych + kanały, radio, podcasty")
        self.form_popup("Przywróć kopię",
                        [("data", "Wklej tekst kopii", "")],
                        [("Przywróć", go), ("Anuluj", lambda v, pop: pop.dismiss())],
                        info="Otwórz zapisaną kopię (np. w Dysku Google), skopiuj cały tekst "
                             "i wklej go tutaj. Utwory są dopasowywane po tytule i wykonawcy.")

    # --- wyszukiwanie głosowe
    def voice_search(self):
        try:
            from android import activity
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            RI = autoclass("android.speech.RecognizerIntent")
            act = autoclass("org.kivy.android.PythonActivity").mActivity
            if not self._voice_bound:
                activity.bind(on_activity_result=self._voice_result)
                self._voice_bound = True
            it = Intent(RI.ACTION_RECOGNIZE_SPEECH)
            it.putExtra(RI.EXTRA_LANGUAGE_MODEL, RI.LANGUAGE_MODEL_FREE_FORM)
            it.putExtra(RI.EXTRA_LANGUAGE, "pl-PL")
            it.putExtra(RI.EXTRA_PROMPT, "Powiedz, czego szukasz")
            act.startActivityForResult(it, 4711)
        except Exception:
            self.set_status("Głos działa w wersji APK. W Pydroid dotknij mikrofonu na klawiaturze.")
            self.show_global_search()

    def _voice_result(self, request, result, data):
        if request != 4711 or result != -1 or data is None:
            return
        try:
            from jnius import autoclass
            lst = data.getStringArrayListExtra(autoclass("android.speech.RecognizerIntent").EXTRA_RESULTS)
            if lst is not None and lst.size() > 0:
                txt = str(lst.get(0))
                Clock.schedule_once(lambda dt: self.show_global_search(txt))
        except Exception:
            pass

    # --- potrząśnięcie = następny
    def toggle_shake(self):
        on = self.lib.get_setting("potrzasanie", "0") != "1"
        self.lib.set_setting("potrzasanie", "1" if on else "0")
        self.setup_shake(on)
        self.set_status(f"Potrząśnij = następny: {'wł.' if on else 'wył.'}")

    def setup_shake(self, on):
        try:
            from jnius import PythonJavaClass, autoclass, java_method
            ctx = android_context()
            Context = autoclass("android.content.Context")
            Sensor = autoclass("android.hardware.Sensor")
            SM = autoclass("android.hardware.SensorManager")
            sm = ctx.getSystemService(Context.SENSOR_SERVICE)
            if self.shake is not None:
                sm.unregisterListener(self.shake)
                self.shake = None
            if not on:
                return
            app = self

            class Shake(PythonJavaClass):
                __javainterfaces__ = ["android/hardware/SensorEventListener"]
                __javacontext__ = "app"
                last = 0.0

                @java_method("(Landroid/hardware/SensorEvent;)V")
                def onSensorChanged(self, event):
                    v = event.values
                    g = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) / 9.81
                    now = time.time()
                    if g > 2.6 and now - self.last > 1.2:
                        self.last = now
                        Clock.schedule_once(lambda dt: app.active and app.next())

                @java_method("(Landroid/hardware/Sensor;I)V")
                def onAccuracyChanged(self, sensor, accuracy):
                    pass
            self.shake = Shake()
            sm.registerListener(self.shake, sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER),
                                SM.SENSOR_DELAY_UI)
        except Exception:
            if on:
                self.set_status("Czujnik ruchu niedostępny (tylko Android)")

    # --- tło z okładki i motyw automatyczny
    def toggle_tint(self):
        on = self.lib.get_setting("tlo_okladka", "1") != "1"
        self.lib.set_setting("tlo_okladka", "1" if on else "0")
        self.update_tint()

    def update_tint(self, *_):
        col = None
        if self.lib.get_setting("tlo_okladka", "1") == "1" and self.cover \
                and not self.cover.startswith("http"):
            col = dominant_color(self.cover)
        target = [*col, 0.2] if col else [*self.tint[:3], 0]
        anim(self, d=0.8, t="in_out_sine", tint=target)

    def check_auto_theme(self, _dt):
        if self.lib.get_setting("motyw", "Ciepły") != AUTO_THEME:
            return
        name = resolve_theme(AUTO_THEME)
        if name != self.theme_now:
            self.theme_now = name
            apply_theme(AUTO_THEME)
            self.rebuild_ui()
            self.set_status(f"Motyw automatyczny: {name}")

    # --- ekran Teraz gra
    def show_now_playing(self):
        if not self.active:
            self.set_status("Nic nie gra")
            return
        root = FloatLayout()
        with root.canvas.before:
            Color(*BG)
            bg1 = Rectangle(texture=white_tex())
            tint = Color(*ACCENT[:3], 0.14)
            bg2 = Rectangle(texture=white_tex())

        def lay(*_):
            bg1.pos = bg2.pos = root.pos
            bg1.size = bg2.size = root.size
        root.bind(pos=lay, size=lay)
        box = BoxLayout(orientation="vertical", padding=(dp(18), dp(10)), spacing=dp(10),
                        size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        root.add_widget(box)
        disc = VinylDisc(size_hint_y=None)
        box.bind(width=lambda w, v: setattr(disc, "height",
                                            max(dp(120), min(v - dp(36), Window.height * 0.42))))
        box.add_widget(disc)
        t_lbl = Label(text=self.now_text, font_size="22sp", bold=True, color=ACCENT,
                      size_hint_y=None, height=dp(34), shorten=True, halign="center")
        a_lbl = Label(text=self.now_sub, font_size="15sp", color=MUTED, size_hint_y=None,
                      height=dp(24), shorten=True, halign="center")
        for lb in (t_lbl, a_lbl):
            lb.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
            box.add_widget(lb)
        srow = BoxLayout(size_hint_y=None, height=dp(40))
        p_lbl = Label(text=self.pos_text, color=MUTED, size_hint_x=None, width=dp(56))
        sl = ThemedSlider(min=0, max=self.dur, value=self.pos)
        sl.bind(on_touch_up=lambda w, touch: w.collide_point(*touch.pos) and self.seek(w.value))
        d_lbl = Label(text=self.dur_text, color=MUTED, size_hint_x=None, width=dp(56))
        for w in (p_lbl, sl, d_lbl):
            srow.add_widget(w)
        box.add_widget(srow)
        ctrl = BoxLayout(size_hint_y=None, height=dp(76), spacing=dp(8))
        b_prev = RoundButton(text="|<", font_size="24sp", bg=list(CARD_HI))
        b_play = RoundButton(text=self.play_label, font_size="20sp", bg=list(ACCENT_DIM))
        b_next = RoundButton(text=">|", font_size="24sp", bg=list(CARD_HI))
        for b, fn in ((b_prev, self.prev), (b_play, self.toggle), (b_next, self.next)):
            b.bind(on_release=lambda _b, fn=fn: fn())
            ctrl.add_widget(b)
        box.add_widget(ctrl)
        extra = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(4))
        b_fav = RoundButton(text="Lubię", bg=list(ACCENT if self.is_fav else CARD_HI))
        b_txt = RoundButton(text="Tekst", bg=list(CARD_HI))
        b_kar = RoundButton(text="Karaoke", bg=list(CARD_HI))
        b_shr = RoundButton(text="Udostępnij", bg=list(CARD_HI), font_size="13sp")
        b_close = RoundButton(text="Zamknij", bg=list(CARD_HI))
        b_shr.bind(on_release=lambda *_: self.active and self.share_track(self.queue[self.qi]))
        for b in (b_fav, b_txt, b_kar, b_shr, b_close):
            extra.add_widget(b)
        box.add_widget(extra)
        box.add_widget(Widget(size_hint_y=0.15))
        pop = RoundPopup(title="Teraz gra", content=root, size_hint=(1, 1))
        b_fav.bind(on_release=lambda *_: self.toggle_fav())
        b_txt.bind(on_release=lambda *_: self.show_lyrics())
        b_kar.bind(on_release=lambda *_: self.show_lyrics(karaoke=True))
        b_close.bind(on_release=lambda *_: pop.dismiss())

        def upd_cover(*_):
            local = self.cover if self.cover and not self.cover.startswith("http") else ""
            disc.source = local
            col = dominant_color(local) if local else None
            tint.rgba = (*(col or ACCENT[:3]), 0.3 if col else 0.14)
        binds = dict(
            now_text=lambda a, v: setattr(t_lbl, "text", v),
            now_sub=lambda a, v: setattr(a_lbl, "text", v),
            cover=upd_cover,
            play_label=lambda a, v: setattr(b_play, "text", v),
            is_fav=lambda a, v: setattr(b_fav, "bg", list(ACCENT if v else CARD_HI)),
            pos=lambda a, v: setattr(sl, "value", v),
            dur=lambda a, v: setattr(sl, "max", v),
            pos_text=lambda a, v: setattr(p_lbl, "text", v),
            dur_text=lambda a, v: setattr(d_lbl, "text", v))
        self.bind(**binds)

        def spin(dt):
            if self.active and not self.player.paused:
                disc.angle = (disc.angle + dt * (25 + 60 * self.energy)) % 360
        ev = Clock.schedule_interval(spin, 1 / 30)
        def closed(*_):
            self.unbind(**binds)
            ev.cancel()
        pop.bind(on_dismiss=closed)
        upd_cover()
        pop.open()

    # --- ekran powitalny
    def show_splash(self):
        if not ANIM["on"]:
            return
        ov = FloatLayout()
        with ov.canvas.before:
            Color(*BG)
            rect = Rectangle(texture=white_tex())
        ov.bind(pos=lambda w, v: setattr(rect, "pos", v), size=lambda w, v: setattr(rect, "size", v))
        disc = VinylDisc(size_hint=(None, None), size=(dp(170), dp(170)), opacity=0,
                         pos_hint={"center_x": 0.5, "center_y": 0.6})
        logo = WordLabel(text="LEOX", font_size=sp(54), bold=True, color=ACCENT,
                         size_hint=(None, None), wscale=0.3, opacity=0,
                         pos_hint={"center_x": 0.5, "center_y": 0.4})
        logo.texture_update()
        logo.size = logo.texture_size
        sub = Label(text="Player", font_size=sp(22), color=TEXT, size_hint=(None, None),
                    opacity=0, pos_hint={"center_x": 0.5, "center_y": 0.33})
        sub.texture_update()
        sub.size = sub.texture_size
        fx = FxFront(border=False)
        for w in (disc, logo, sub, fx):
            ov.add_widget(w)
        Window.add_widget(ov)
        Animation(opacity=1, d=0.4).start(disc)
        Animation(angle=540, d=1.8, t="out_cubic").start(disc)
        Animation(opacity=1, wscale=1, d=0.6, t="out_back").start(logo)
        Clock.schedule_once(lambda dt: Animation(opacity=1, d=0.4).start(sub), 0.35)
        ev = Clock.schedule_interval(lambda dt: fx.update(dt), 1 / 30)

        def boom(_dt):
            fx.burst(Window.width / 2, Window.height * 0.6, n=60)
            fx.ring(Window.width / 2, Window.height * 0.6)
        Clock.schedule_once(boom, 0.5)

        def end(_dt):
            a = Animation(opacity=0, d=0.45)
            a.bind(on_complete=lambda *x: (ev.cancel(), Window.remove_widget(ov)))
            a.start(ov)
        Clock.schedule_once(end, 2.0)

    # --- szukaj wszędzie
    @staticmethod
    def header_row(text):
        return {"text": f"[b]{escape_markup(text)}[/b]", "markup": True, "tap": lambda b: None,
                "keep": True, "bg": [0, 0, 0, 0], "h": 38}

    def global_rows(self, query):
        if len(query) < 2:
            return []
        from concurrent.futures import ThreadPoolExecutor
        q = query.casefold()
        tracks = [r for r in self.lib.tracks()
                  if q in " ".join(x or "" for x in r[1:4]).casefold()][:15]
        with ThreadPoolExecutor(max_workers=2) as ex:
            fy, fr = ex.submit(self.yt_fetch, query), ex.submit(self.radio_rows, query)
            try:
                vids = fy.result()[:8]
            except Exception:
                vids = []
            try:
                radios = fr.result()[:6]
            except Exception:
                radios = []
        rows = []
        if tracks:
            rows.append(self.header_row(f"Twoja biblioteka ({len(tracks)})"))
            rows += [{"text": f"{r[1]}\n{r[2] or ''}", "tap": lambda b, r=r: self.play_now(r)}
                     for r in tracks]
        if vids:
            rows.append(self.header_row("YouTube"))
            for v in vids:
                r = self.video_row(v, True)
                r["image"], r["h"] = self.thumb(v), 84
                rows.append(r)
        if radios:
            rows.append(self.header_row("Radio"))
            rows += radios
        return rows

    def show_global_search(self, initial=""):
        self.live_search_popup("Szukaj wszędzie", "Biblioteka, YouTube i radio naraz",
                               self.global_rows, empty_msg="Nic nie znaleziono",
                               initial=initial or "")

    # --- płynne przejścia i mikrofon
    def cycle_xf(self):
        vals = [0, 3, 6, 10]
        self.xf = vals[(vals.index(self.xf) + 1) % 4] if self.xf in vals else 0
        self.lib.set_setting("przejscie", self.xf)
        self.set_status(f"Płynne przejścia: {self.xf} s" if self.xf else "Płynne przejścia: wył.")
        if self.apk:
            self.player.cmd(cmd="set", xf=self.xf)

    def ask_mic(self):
        try:
            from android.permissions import request_permissions
            request_permissions(["android.permission.RECORD_AUDIO"])
            self.set_status("Po zgodzie efekty reagują na prawdziwy dźwięk (od następnego utworu)")
        except Exception:
            self.set_status("Tu nie da się poprosić o zgodę - działa w wersji APK")

    # --- quiz
    def show_quiz(self):
        tracks = [r for r in self.lib.tracks() if (r[4] or 0) >= 30]
        if len(tracks) < 4:
            self.set_status("Quiz potrzebuje co najmniej 4 utworów w bibliotece")
            return
        if self.active:
            self.player.stop()
            self.active = False
            self.play_label = "Play"
            self.pulse_stop()
        pl = self.player.local if self.apk else self.player
        q = {"round": 0, "score": 0, "total": 10, "locked": False, "stop_ev": None}
        root = FloatLayout()
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10),
                        size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        root.add_widget(box)
        fx = FxFront(border=False)
        root.add_widget(fx)
        info = Label(color=MUTED, font_size="16sp", size_hint_y=None, height=dp(30))
        disc = VinylDisc(size_hint_y=None, height=dp(170))
        big = Label(text="Zgadnij utwór!", font_size="22sp", bold=True, color=ACCENT,
                    size_hint_y=None, height=dp(44))
        opts = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None, height=dp(4 * 66))
        btns = []
        for i in range(4):
            b = RoundButton(font_size="15sp", halign="center", valign="middle", max_lines=2)
            b.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0] - dp(24), None)))
            b.bind(on_release=lambda _b, i=i: choose(i))
            opts.add_widget(b)
            btns.append(b)
        for w in (info, disc, big, opts, Widget()):
            box.add_widget(w)
        bar = BoxLayout(size_hint_y=None, height=dp(56))
        again = RoundButton(text="Posłuchaj jeszcze raz", bg=list(ACCENT_DIM))
        close = RoundButton(text="Zamknij", bg=list(CARD_HI))
        bar.add_widget(again)
        bar.add_widget(close)
        box.add_widget(bar)
        pop = RoundPopup(title="Quiz: Zgadnij utwór", content=root, size_hint=(1, 1))

        def play_snippet(*_):
            if q["stop_ev"]:
                q["stop_ev"].cancel()
            if q["locked"] and q["round"] > q["total"]:
                return
            try:
                pl.gain = 1.0
                pl.load(q["answer"][0])
                pl.seek(q["start"])
            except Exception as e:
                big.text = f"Błąd: {e}"[:60]
                return
            q["stop_ev"] = Clock.schedule_once(lambda dt: pl.stop(), 8)

        def new_round():
            q["round"] += 1
            if q["round"] > q["total"]:
                finish()
                return
            ans = random.choice(tracks)
            choices = random.sample([t for t in tracks if t[0] != ans[0]], 3) + [ans]
            random.shuffle(choices)
            q.update(answer=ans, choices=choices, locked=False,
                     start=random.uniform(0.2, 0.6) * (ans[4] or 60))
            for n, (b, c) in enumerate(zip(btns, choices)):
                b.text = f"{c[1]}\n{c[2] or ''}"
                b.bg, b.disabled = list(CARD), False
                if ANIM["on"]:
                    b.opacity = 0
                    Clock.schedule_once(lambda dt, w=b: anim(w, d=0.3, opacity=1), 0.08 * n)
            info.text = f"Runda {q['round']}/{q['total']}     Wynik: {q['score']}"
            big.text = "Co to za utwór?"
            play_snippet()

        def choose(i):
            if q["locked"] or q["round"] > q["total"]:
                return
            q["locked"] = True
            ok = q["choices"][i][0] == q["answer"][0]
            for b, c in zip(btns, q["choices"]):
                if c[0] == q["answer"][0]:
                    b.bg = [0.2, 0.6, 0.3, 1]
                elif b is btns[i]:
                    b.bg = [0.65, 0.2, 0.2, 1]
            if ok:
                q["score"] += 1
                big.text = "Dobrze!"
                x, y = btns[i].to_window(*btns[i].center)
                fx.burst(x, y, n=40)
            else:
                big.text = f"To było: {q['answer'][1]}"
            info.text = f"Runda {q['round']}/{q['total']}     Wynik: {q['score']}"
            Clock.schedule_once(lambda dt: new_round(), 1.8)

        def finish():
            pl.stop()
            best = int(self.lib.get_setting("quiz_best", "0"))
            rec = q["score"] > best
            if rec:
                self.lib.set_setting("quiz_best", q["score"])
            big.text = f"Koniec! {q['score']}/{q['total']}" + ("  Nowy rekord!" if rec else "")
            info.text = f"Rekord: {max(best, q['score'])}"
            for b in btns:
                b.text, b.disabled = "", True
            fx.burst(Window.width / 2, Window.height * 0.6, n=80)
            again.text = "Zagraj od nowa"

        def again_press(*_):
            if q["round"] > q["total"]:
                q.update(round=0, score=0)
                again.text = "Posłuchaj jeszcze raz"
                new_round()
            else:
                play_snippet()
        again.bind(on_release=again_press)

        def spin(dt):
            fx.update(dt)
            if pl.mp is not None or pl.snd is not None:
                disc.angle = (disc.angle + dt * 60) % 360
        ev = Clock.schedule_interval(spin, 1 / 30)

        def closed(*_):
            ev.cancel()
            if q["stop_ev"]:
                q["stop_ev"].cancel()
            pl.stop()
        pop.bind(on_dismiss=closed)
        close.bind(on_release=lambda *_: pop.dismiss())
        pop.open()
        new_round()

    # --- tryb imprezowy
    def start_party(self):
        if self.party:
            self.show_party_info()
            return
        app = self
        page = PARTY_HTML
        for k in ("BG", "CARD", "ACCENT", "MUTED"):
            page = page.replace(f"%{k}%", "#" + "".join(f"{int(c * 255):02x}"
                                                        for c in globals()[k][:3]))
        page_b = page.encode("utf-8")
        ids, last_add = {}, {}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, body, ctype="application/json; charset=utf-8", code=200):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def js(self, obj):
                self.send(json.dumps(obj).encode("utf-8"))

            def do_GET(self):
                u = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(u.query)

                def g(k):
                    return (qs.get(k) or [""])[0][:200]
                try:
                    if u.path == "/":
                        self.send(page_b, "text/html; charset=utf-8")
                    elif u.path == "/api/state":
                        self.js(app.party_state())
                    elif u.path == "/api/search":
                        qq, out = g("q").casefold(), []
                        for r in app.lib.tracks():
                            if qq and qq in " ".join(x or "" for x in r[1:4]).casefold():
                                k = hashlib.md5(r[0].encode()).hexdigest()[:12]
                                ids[k] = r
                                out.append({"id": k, "title": r[1], "sub": r[2] or ""})
                                if len(out) >= 30:
                                    break
                        self.js(out)
                    elif u.path == "/api/yt":
                        vids = app.yt_fetch(g("q"))[:12] if len(g("q")) >= 2 else []
                        self.js([{"id": v["id"], "title": v["title"], "sub": v["channel"]}
                                 for v in vids if v.get("id")])
                    elif u.path == "/api/add":
                        ip, now = self.client_address[0], time.time()
                        if now - last_add.get(ip, 0) < 5:
                            self.js({"ok": False, "msg": "Poczekaj chwilę"})
                            return
                        if g("id") in ids:
                            track = ids[g("id")]
                        elif re.fullmatch(r"[A-Za-z0-9_-]{11}", g("yt")):
                            track = (f"https://www.youtube.com/watch?v={g('yt')}",
                                     g("t") or "YouTube", g("a"), "YouTube", 0)
                        else:
                            self.js({"ok": False, "msg": "Nie znaleziono"})
                            return
                        last_add[ip] = now
                        Clock.schedule_once(lambda dt: app.party_add(track))
                        self.js({"ok": True})
                    else:
                        self.send("Nie ma takiej strony".encode("utf-8"),
                                  "text/plain; charset=utf-8", 404)
                except Exception as e:
                    try:
                        self.js({"ok": False, "msg": str(e)[:80]})
                    except Exception:
                        pass

        srv = None
        for port in range(8080, 8090):
            try:
                srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
                break
            except OSError:
                continue
        if srv is None:
            self.set_status("Nie udało się uruchomić trybu imprezowego (zajęte porty)")
            return
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.party = srv
        self.party_url = f"http://{local_ip()}:{srv.server_address[1]}"
        self.set_status("Tryb imprezowy włączony")
        self.show_party_info()

    def stop_party(self):
        if self.party:
            srv, self.party = self.party, None
            threading.Thread(target=lambda: (srv.shutdown(), srv.server_close()),
                             daemon=True).start()
            self.set_status("Tryb imprezowy wyłączony")

    def party_state(self):
        now = f"{self.now_text} - {self.now_sub}".strip(" -") if self.active else ""
        nxt = self.queue[self.qi + 1:self.qi + 11] if self.active else []
        return {"now": now, "queue": [{"title": t[1], "sub": t[2] or ""} for t in nxt]}

    def party_add(self, track):
        self.queue_add(track, False)
        self.set_status(f"Gość dodał: {track[1]}")
        if self.fx_front is not None and ANIM["on"]:
            self.fx_front.burst(Window.width / 2, Window.height / 2, n=30, power=0.7)

    def show_party_info(self):
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(8))
        try:
            import qrcode
            qr = qrcode.QRCode(border=2)
            qr.add_data(self.party_url)
            qr.make(fit=True)
            box.add_widget(QRWidget(qr.get_matrix(), size_hint_y=None, height=dp(240)))
        except Exception:
            box.add_widget(Label(text="(zainstaluj w Pip: qrcode - pojawi się kod QR)",
                                 color=MUTED, size_hint_y=None, height=dp(30)))
        url = Label(text=self.party_url, font_size="22sp", bold=True, color=ACCENT,
                    size_hint_y=None, height=dp(40))
        box.add_widget(url)
        info = Label(text="Goście w tej samej sieci Wi-Fi otwierają ten adres w przeglądarce "
                          "(albo skanują kod) i dodają utwory do kolejki.",
                     color=MUTED, halign="center", size_hint_y=None)
        info.bind(width=lambda w, v: setattr(w, "text_size", (v - dp(10), None)),
                  texture_size=lambda w, v: setattr(w, "height", v[1]))
        box.add_widget(info)
        box.add_widget(Widget())
        bar = BoxLayout(size_hint_y=None, height=dp(56))
        pop = RoundPopup(title="Tryb imprezowy", content=box, size_hint=(0.95, 0.85))
        stop = RoundButton(text="Zakończ imprezę", bg=list(ACCENT_DIM))
        stop.bind(on_release=lambda *_: (self.stop_party(), pop.dismiss()))
        close = RoundButton(text="Zamknij", bg=list(CARD_HI))
        close.bind(on_release=lambda *_: pop.dismiss())
        bar.add_widget(stop)
        bar.add_widget(close)
        box.add_widget(bar)
        pop.open()

    def on_stop(self):
        self.stop_party()
        if self.cast:
            self.cast.stop()
        if self.web:
            self.web.stop()
        if not self.apk:
            self.player.stop()                  # w APK usługa gra dalej

# =====================================================================
#  LEOX PLAYER - DODATEK YOUTUBE+
#  Strona główna z kategoriami, podpowiedzi wyszukiwania, "Pokaż więcej",
#  zakładka Pobrane i Shorts.
#
#  JAK WKLEIĆ: w pliku leox_player.py usuń dwie ostatnie linijki
#      if __name__ == "__main__":
#          MuzykaApp().run()
#  i w to miejsce wklej cały ten dodatek (ma te dwie linijki na końcu).
# =====================================================================
from kivy.uix.modalview import ModalView

YT_CATS = ("Dla Ciebie", "Subskrypcje", "Na czasie", "Muzyka", "Gry", "Śmieszne", "Pobrane")
YT_TOPICS = {"Muzyka": ("muzyka",), "Gry": ("gry",), "Śmieszne": ("śmieszne",),
             "Na czasie": ("muzyka", "gry", "śmieszne", "nowość")}
YT_WEEK_TOP = "&sp=CAMSBAgDEAE%3D"      # filtr YouTube: z tego tygodnia, od najczęściej oglądanych
YT_SHORT_FILTER = "&sp=EgQQARgB"        # filtr YouTube: filmy do 4 minut
SHORTS_TAGS = ("shorts", "polska", "śmieszne", "ciekawostki", "gry", "zwierzęta")
YT_SUGGEST = "https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&hl=pl&q="


def yt_flat(url, start=1, end=20):
    """Lista filmów spod adresu YouTube (bez wchodzenia w każdy film osobno)."""
    import yt_dlp
    opts = {"quiet": True, "logger": QUIET, "no_warnings": True, "skip_download": True,
            "extract_flat": "in_playlist", "playliststart": start, "playlistend": end}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return [e for e in (info or {}).get("entries") or []
            if e and re.fullmatch(r"[A-Za-z0-9_-]{11}", e.get("id") or "")]


def yt_round_robin(lists):
    """Przeplata kilka list (po jednym z każdej) i usuwa powtórki."""
    out, seen = [], set()
    for i in range(max((len(x) for x in lists), default=0)):
        for x in lists:
            if i < len(x) and x[i]["id"] not in seen:
                seen.add(x[i]["id"])
                out.append(x[i])
    return out


def yt_run_jobs(jobs):
    """Uruchamia zadania równolegle; błąd jednego nie psuje pozostałych."""
    from concurrent.futures import ThreadPoolExecutor
    out = []
    if not jobs:
        return out
    with ThreadPoolExecutor(max_workers=4) as ex:
        for fut in [ex.submit(j) for j in jobs]:
            try:
                out.append(fut.result())
            except Exception:
                out.append([])
    return out


class ShortsArea(FloatLayout):
    """Ekran Shorts: przesunięcie w górę/dół zmienia film, dotknięcie to pauza."""
    swipe_cb = None
    tap_cb = None

    def on_touch_down(self, touch):
        if super().on_touch_down(touch):        # przyciski mają pierwszeństwo
            return True
        if self.collide_point(*touch.pos):
            touch.grab(self)
            touch.ud["short_y"] = touch.y
            return True
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            dy = touch.y - touch.ud.get("short_y", touch.y)
            if abs(dy) > dp(70):
                if self.swipe_cb:
                    self.swipe_cb(1 if dy > 0 else -1)
            elif abs(dy) < dp(14) and self.tap_cb:
                self.tap_cb()
            return True
        return super().on_touch_up(touch)


class YTPlus:
    """Metody dopisywane do aplikacji (na dole pliku)."""

    # --- ostatnio szukane
    def yt_recent(self):
        try:
            return [s for s in json.loads(self.lib.get_setting("yt_szukane", "[]"))
                    if isinstance(s, str)]
        except ValueError:
            return []

    def yt_remember(self, q):
        q = q.strip()
        if len(q) < 2:
            return
        items = [q] + [s for s in self.yt_recent() if s.casefold() != q.casefold()]
        self.lib.set_setting("yt_szukane", json.dumps(items[:12], ensure_ascii=False))

    # --- źródła filmów
    def channel_videos(self, url, name, tab, start, end):
        vids = [self.entry(e) for e in yt_flat(url + tab, start, end)]
        for v in vids:
            v["channel"], v["ch_url"] = v["channel"] or name, v["ch_url"] or url
        return vids

    def topic_videos(self, topic, start, end):
        url = ("https://www.youtube.com/results?search_query="
               + urllib.parse.quote_plus(topic) + YT_WEEK_TOP)
        return [self.entry(e) for e in yt_flat(url, start, end)]

    def yt_home(self, page=0, ctx=None):
        """Strona główna: podobne do ostatnio oglądanych, nowe z zapisanych kanałów
        i popularne w tym tygodniu. ctx pamięta wybór źródeł dla kolejnych stron."""
        ctx = ctx if ctx is not None else {}
        if "seeds" not in ctx:
            hist = [h for h in self.lib.yt_list("yt_history")[:12] if h.get("id")]
            chans = list(self.lib.channels())
            random.shuffle(chans)
            ctx["seeds"] = random.sample(hist, min(3, len(hist)))
            ctx["chans"] = chans[:4]
            n = 1 if (ctx["seeds"] or ctx["chans"]) else 3
            ctx["topics"] = random.sample(YT_TOPICS["Na czasie"], n)
        skip = {h["id"] for h in ctx["seeds"]}
        jobs = []
        for h in ctx["seeds"]:                  # "mix" YouTube = filmy podobne do obejrzanego
            jobs.append(lambda h=h: [self.entry(e) for e in yt_flat(
                f"https://www.youtube.com/watch?v={h['id']}&list=RD{h['id']}",
                page * 8 + 2, page * 8 + 9)])
        for url, name in ctx["chans"]:
            jobs.append(lambda u=url, n=name: self.channel_videos(
                u, n, "/videos", page * 4 + 1, page * 4 + 4))
        for t in ctx["topics"]:
            jobs.append(lambda t=t: self.topic_videos(t, page * 8 + 1, page * 8 + 8))
        vids = [v for v in yt_round_robin(yt_run_jobs(jobs)) if v["id"] not in skip]
        if len(vids) < 5 and page == 0:
            have = {v["id"] for v in vids}
            vids += [v for v in (self.entry(e) for e in yt_flat("ytsearch24:popularne dzisiaj", 1, 24))
                     if v["id"] not in have]
        return vids

    def yt_page(self, query, cat, page, ctx):
        """Jedna strona wyników: wyszukiwanie albo wybrana kategoria."""
        if query:
            n = 20
            return [self.entry(e) for e in yt_flat(f"ytsearch{(page + 1) * n}:{query}",
                                                   page * n + 1, (page + 1) * n)]
        if cat == "Pobrane":
            return self.local_videos() if page == 0 else []
        if cat == "Subskrypcje":
            return yt_round_robin(yt_run_jobs([
                lambda u=u, n=n: self.channel_videos(u, n, "/videos", page * 4 + 1, page * 4 + 4)
                for u, n in self.lib.channels()[:12]]))
        if cat in YT_TOPICS:
            topics = YT_TOPICS[cat]
            per = max(6, 24 // len(topics))
            return yt_round_robin(yt_run_jobs([
                lambda t=t: self.topic_videos(t, page * per + 1, (page + 1) * per)
                for t in topics]))
        return self.yt_home(page, ctx)

    # --- karty filmów
    def yt_card(self, v, n=99):
        """Karta filmu jak w aplikacji YouTube: duża miniatura, tytuł, kanał, przyciski."""
        card = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4),
                         padding=(dp(4), dp(8)))
        card.bind(minimum_height=card.setter("height"))
        img = TapImage(size_hint_y=None, fit_mode="contain")
        self.net_image(self.thumb(v), img)
        img.bind(width=lambda w, val: setattr(w, "height", val * 9 / 16))
        img.bind(on_release=lambda _w, v=v: self.watch(v))
        card.add_widget(img)
        title = Label(text=v["title"], bold=True, font_size="15sp", size_hint_y=None,
                      halign="left", valign="top", max_lines=2, shorten=True)
        title.bind(width=lambda w, val: setattr(w, "text_size", (val - dp(8), None)),
                   texture_size=lambda w, val: setattr(w, "height", val[1]))
        card.add_widget(title)
        sub = v["channel"] + (f"   {fmt(v['dur'])}" if v["dur"] else "")
        sl = Label(text=sub, color=MUTED, font_size="12sp", size_hint_y=None,
                   height=dp(20), halign="left", shorten=True)
        sl.bind(width=lambda w, val: setattr(w, "text_size", (val - dp(8), None)))
        card.add_widget(sl)
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(2))
        buttons = [("Oglądaj", lambda b, v=v: self.watch(v), ACCENT_DIM, 1.2)]
        if not v.get("local"):
            buttons += [("Słuchaj", lambda b, v=v: self.stream(v), CARD, 1),
                        ("Pobierz", lambda b, v=v: self.download_choice(v), CARD, 1),
                        ("Kanał", lambda b, v=v: v["ch_url"] and self.open_channel(v["ch_url"]),
                         CARD, 1),
                        ("+", lambda b, v=v: self.yt_later(v), CARD, 0.5)]
        for text, fn, bg, w in buttons:
            b = RoundButton(text=text, bg=list(bg), font_size="13sp", size_hint_x=w)
            b.bind(on_release=fn)
            row.add_widget(b)
        card.add_widget(row)
        if ANIM["on"] and n < 8:
            card.opacity = 0
            Clock.schedule_once(lambda dt, w=card: anim(w, d=0.35, opacity=1), 0.06 * n + 0.05)
        return card

    def yt_cards(self, grid, vids, pop):
        grid.clear_widgets()
        if not vids:
            grid.add_widget(Label(text="Pusto", color=MUTED, size_hint_y=None, height=dp(60)))
        for n, v in enumerate(vids):
            grid.add_widget(self.yt_card(v, n))

    # --- ekran YouTube
    def show_youtube(self):
        """Strona główna z kategoriami, wyszukiwarka z podpowiedziami i wejście do Shorts."""
        box = BoxLayout(orientation="vertical", spacing=dp(4))
        top = BoxLayout(size_hint_y=None, height=dp(54))
        ti = RoundInput(hint_text="Szukaj w YouTube", multiline=False)
        b_clear = RoundButton(text="X", size_hint_x=None, width=dp(54), bg=list(CARD_HI))
        top.add_widget(ti)
        top.add_widget(b_clear)
        box.add_widget(top)
        strip_sv = ScrollView(size_hint_y=None, height=dp(50), do_scroll_y=False, bar_width=0)
        strip = BoxLayout(size_hint=(None, 1), spacing=dp(2))
        strip.bind(minimum_width=strip.setter("width"))
        strip_sv.add_widget(strip)
        box.add_widget(strip_sv)
        info = Label(text="", color=MUTED, font_size="13sp", size_hint_y=None, height=0)
        info.bind(text=lambda w, t: setattr(w, "height", dp(24) if t else 0))
        box.add_widget(info)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(2))
        grid.bind(minimum_height=grid.setter("height"))
        sv = ScrollView(bar_color=ACCENT_DIM)
        sv.add_widget(grid)
        box.add_widget(sv)
        bar = BoxLayout(size_hint_y=None, height=dp(56))
        box.add_widget(bar)
        pop = RoundPopup(title="YouTube", content=box, size_hint=(1, 1))
        st = {"cat": YT_CATS[0], "query": "", "page": 0, "token": 0, "sug_token": 0,
              "ev": None, "sev": None, "skip": False, "open": True, "shown": set(),
              "ctx": {}, "sug": [], "more": None, "count": 0}
        empty = {"Subskrypcje": "Brak zapisanych kanałów. Otwórz film, dotknij Kanał i Zapisz kanał.",
                 "Pobrane": "Brak pobranych filmów. Dotknij Pobierz przy filmie."}

        def cancel_timers():
            for k in ("ev", "sev"):
                if st[k]:
                    st[k].cancel()
                    st[k] = None

        def chip(text, fn, bg=None):
            b = RoundButton(text=text, size_hint_x=None, width=dp(90), font_size="13sp",
                            bg=list(bg or CARD))
            b.bind(texture_size=lambda w, ts: setattr(w, "width", ts[0] + dp(34)))
            b.bind(on_release=lambda *_: fn())
            strip.add_widget(b)

        def build_strip():
            strip.clear_widgets()
            q = ti.text.strip()
            chip("Shorts", lambda: self.show_shorts(ti.text.strip()), ACCENT_DIM)
            recent = self.yt_recent()
            if q:
                low = q.casefold()
                mine = [s for s in recent if low in s.casefold() and s.casefold() != low][:3]
                rest = [s for s in st["sug"] if s.casefold() != low and s not in mine]
                for s in mine + rest:
                    chip(s, lambda s=s: pick(s), CARD_HI if s in mine else CARD)
            else:
                for name in YT_CATS:
                    chip(name, lambda name=name: select(name),
                         CARD_HI if name == st["cat"] else CARD)
                for s in recent[:5]:
                    chip(s, lambda s=s: pick(s), BG_POP)
            strip_sv.scroll_x = 0

        def more_button():
            b = RoundButton(text="Pokaż więcej", size_hint_y=None, height=dp(56),
                            bg=list(ACCENT_DIM))
            b.bind(on_release=lambda *_: load(False))
            grid.add_widget(b)
            st["more"] = b

        def load(reset=True):
            if reset:
                st["page"], st["shown"], st["ctx"], st["count"] = 0, set(), {}, 0
            else:
                st["page"] += 1
            st["token"] += 1
            tok, page, q, cat = st["token"], st["page"], st["query"], st["cat"]
            info.text = "Szukanie..." if q else "Wczytywanie..."
            if st["more"] is not None:
                st["more"].text, st["more"].disabled = "Wczytywanie...", True
            ctx = st["ctx"]

            def done(res):
                if tok != st["token"] or not st["open"]:
                    return                      # przyszła starsza odpowiedź
                if st["more"] is not None and st["more"].parent:
                    grid.remove_widget(st["more"])
                st["more"] = None
                if isinstance(res, Exception):
                    info.text = f"Błąd: {res}"[:120]
                    if not reset:
                        st["page"] -= 1
                        more_button()
                    return
                vids = [v for v in res
                        if v.get("local") or (v.get("id") and v["id"] not in st["shown"])]
                st["shown"].update(v["id"] for v in vids if v.get("id"))
                top_px = (1 - sv.scroll_y) * max(grid.height - sv.height, 0)
                if reset:
                    grid.clear_widgets()
                info.text = ""
                if not vids:
                    info.text = (("Brak wyników" if q else empty.get(cat, "Brak filmów"))
                                 if reset else "To już wszystko")
                    return
                for n, v in enumerate(vids):
                    grid.add_widget(self.yt_card(v, n if reset else 99))
                st["count"] += len(vids)
                if cat != "Pobrane" or q:
                    if st["count"] < 160:
                        more_button()
                if reset:
                    sv.scroll_y = 1
                else:                           # lista urosła - zostajemy w tym samym miejscu
                    left = [8]

                    def keep(_dt):
                        span = grid.height - sv.height
                        if span > 0:
                            sv.scroll_y = max(0.0, 1 - top_px / span)
                        left[0] -= 1
                        return left[0] > 0
                    Clock.schedule_interval(keep, 0)
            self.run_bg(lambda: self.yt_page(q, cat, page, ctx), done)

        def suggest(q):
            st["sug_token"] += 1
            tok = st["sug_token"]

            def work():
                data = json.loads(http_get(YT_SUGGEST + urllib.parse.quote(q),
                                           timeout=6).decode("utf-8", "ignore"))
                return [s for s in data[1] if isinstance(s, str)][:8]

            def done(res):
                if (tok != st["sug_token"] or not st["open"] or isinstance(res, Exception)
                        or ti.text.strip() != q):
                    return
                st["sug"] = res
                build_strip()
            self.run_bg(work, done)

        def search(q, remember=True):
            q = q.strip()
            if len(q) < 2:
                return
            if remember:
                self.yt_remember(q)
            if q == st["query"]:
                return
            st["query"] = q
            load()

        def pick(s):
            """Dotknięta podpowiedź albo ostatnio szukane hasło."""
            cancel_timers()
            st["skip"] = True
            ti.text = s
            st["skip"] = False
            ti.focus = False
            st["sug"] = []
            build_strip()
            search(s)
            suggest(s)

        def select(name):
            cancel_timers()
            st["cat"], st["query"], st["sug"] = name, "", []
            st["skip"] = True
            ti.text = ""
            st["skip"] = False
            build_strip()
            load()

        def typed(_w, txt):
            if st["skip"]:
                return
            cancel_timers()
            q = txt.strip()
            if not q:
                st["sug"] = []
                build_strip()
                if st["query"]:
                    st["query"] = ""
                    load()
                return
            build_strip()
            if len(q) < 2:
                return
            st["sev"] = Clock.schedule_once(lambda dt: suggest(q), 0.25)
            st["ev"] = Clock.schedule_once(lambda dt: search(q, False), 0.9)

        def entered(*_):
            cancel_timers()
            search(ti.text)
            build_strip()

        def closed(*_):
            st["open"] = False
            cancel_timers()
        ti.bind(text=typed, on_text_validate=entered)
        b_clear.bind(on_release=lambda *_: setattr(ti, "text", ""))
        for text, fn, bg in (("Moja lista", self.show_yt_lists, ACCENT_DIM),
                             ("Kanały", self.show_channels, ACCENT_DIM),
                             ("Pełny YT", lambda: open_external("https://m.youtube.com"), ACCENT_DIM),
                             ("Zamknij", pop.dismiss, CARD_HI)):
            fb = RoundButton(text=text, bg=list(bg), font_size="14sp")
            fb.bind(on_release=lambda _b, fn=fn: fn())
            bar.add_widget(fb)
        pop.bind(on_dismiss=closed)
        pop.open()
        build_strip()
        load()

    # --- Shorts
    def shorts_seen(self):
        try:
            return [s for s in json.loads(self.lib.get_setting("shorts_seen", "[]"))
                    if isinstance(s, str)]
        except ValueError:
            return []

    def shorts_fetch(self, query="", page=0, ctx=None):
        """Lista Shorts: z zapisanych kanałów, z ostatnio szukanych haseł i z hasztagów.
        Z hasłem: Shorts tylko na ten temat."""
        ctx = ctx if ctx is not None else {}
        if "jobs" not in ctx:
            jobs = []
            if query:
                jobs.append(("search", query))
                tag = re.sub(r"\W+", "", query.casefold())
                if tag:
                    jobs.append(("tag", tag))
            else:
                chans = list(self.lib.channels())
                random.shuffle(chans)
                jobs += [("chan", c) for c in chans[:5]]
                jobs += [("search", q) for q in self.yt_recent()[:2]]
                jobs += [("tag", t) for t in random.sample(SHORTS_TAGS, 2)]
            ctx["jobs"] = jobs

        def run(kind, arg):
            if kind == "chan":
                vids = self.channel_videos(arg[0], arg[1], "/shorts", page * 5 + 1, page * 5 + 5)
            elif kind == "tag":
                vids = [self.entry(e) for e in yt_flat(
                    "https://www.youtube.com/hashtag/" + urllib.parse.quote(arg) + "/shorts",
                    page * 10 + 1, page * 10 + 10)]
            else:
                url = ("https://www.youtube.com/results?search_query="
                       + urllib.parse.quote_plus(arg + " #shorts") + YT_SHORT_FILTER)
                vids = [v for v in (self.entry(e) for e in yt_flat(url, page * 20 + 1, page * 20 + 20))
                        if 0 < (v["dur"] or 0) <= 65]
            for v in vids:
                v["url"], v["short"] = f"https://www.youtube.com/shorts/{v['id']}", True
            return vids
        return yt_round_robin(yt_run_jobs([lambda k=k, a=a: run(k, a) for k, a in ctx["jobs"]]))

    def short_thumb(self, vid, cb):
        """Pionowa miniatura Shorta (a gdy jej nie ma - zwykła)."""
        folder = Path(self.user_data_dir) / "miniatury"
        path = folder / f"short_{vid}.jpg"
        if path.exists():
            cb(str(path))
            return

        def work():
            folder.mkdir(parents=True, exist_ok=True)
            for name in ("oar2", "hqdefault"):
                try:
                    data = http_get(f"https://i.ytimg.com/vi/{vid}/{name}.jpg", timeout=8)
                except Exception:
                    continue
                tmp = path.with_suffix(".part")
                tmp.write_bytes(data)
                tmp.replace(path)
                return str(path)
            raise RuntimeError("brak miniatury")
        self.run_bg(work, lambda res: isinstance(res, str) and cb(res))

    def show_shorts(self, query=""):
        """Shorts na cały ekran. W górę = następny, w dół = poprzedni, dotknięcie = pauza."""
        if self.active and not self.player.paused:
            self.toggle()                       # muzyka na pauzę
        area = ShortsArea()
        with area.canvas.before:
            Color(0, 0, 0, 1)
            back = Rectangle(texture=white_tex())
        area.bind(pos=lambda w, v: setattr(back, "pos", v),
                  size=lambda w, v: setattr(back, "size", v))
        full = {"size_hint": (1, 1), "pos_hint": {"x": 0, "y": 0}}
        thumb = AsyncImage(fit_mode="contain", opacity=0, **full)
        stage = FloatLayout(**full)
        msg = MsgLabel(text="Wczytywanie Shorts...", bold=True, halign="center", valign="middle",
                       size_hint=(0.84, None), height=dp(110),
                       pos_hint={"center_x": 0.5, "center_y": 0.5})
        msg.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0] - dp(20), None)))
        meta = BoxLayout(orientation="vertical", size_hint=(0.7, None), height=dp(104),
                         pos_hint={"x": 0.02, "y": 0.02}, padding=(dp(10), dp(6)))
        with meta.canvas.before:
            Color(0, 0, 0, 0.5)
            meta_bg = RoundedRectangle(radius=[dp(14)], texture=white_tex())
        meta.bind(pos=lambda w, v: setattr(meta_bg, "pos", v),
                  size=lambda w, v: setattr(meta_bg, "size", v))
        title = Label(text="", bold=True, font_size="15sp", color=(1, 1, 1, 1),
                      halign="left", valign="middle", max_lines=3, shorten=True)
        title.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0], sz[1])))
        ch = Label(text="", color=(0.82, 0.82, 0.82, 1), font_size="13sp", size_hint_y=None,
                   height=dp(22), halign="left", valign="middle", shorten=True)
        ch.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0], sz[1])))
        meta.add_widget(title)
        meta.add_widget(ch)
        side = BoxLayout(orientation="vertical", size_hint=(None, None), width=dp(84),
                         height=dp(5 * 58), pos_hint={"right": 0.99, "y": 0.02})
        b_dl = RoundButton(text="Pobierz", font_size="13sp")
        b_ch = RoundButton(text="Kanał", font_size="13sp")
        b_later = RoundButton(text="Później", font_size="13sp")
        b_yt = RoundButton(text="W YT", font_size="13sp")
        b_shr = RoundButton(text="Udostęp-\nnij", font_size="12sp", halign="center")
        for b in (b_dl, b_ch, b_later, b_yt, b_shr):
            side.add_widget(b)
        b_close = RoundButton(text="Zamknij", size_hint=(None, None), size=(dp(104), dp(52)),
                              pos_hint={"x": 0.02, "top": 0.99}, bg=list(CARD_HI))
        count = Label(text="Shorts" + (f": {query}" if query else ""), bold=True,
                      color=(1, 1, 1, 1), size_hint=(None, None), size=(dp(190), dp(52)),
                      pos_hint={"right": 0.98, "top": 0.99}, halign="right", valign="middle",
                      shorten=True)
        count.bind(size=lambda w, sz: setattr(w, "text_size", sz))
        prog = Widget(size_hint=(1, None), height=dp(3), pos_hint={"x": 0, "y": 0})
        with prog.canvas:
            Color(*ACCENT)
            prog_bar = Rectangle(texture=white_tex(), size=(0, 0))
        for w in (thumb, stage, msg, meta, side, b_close, count, prog):
            area.add_widget(w)
        view = ModalView(size_hint=(1, 1), background="", background_color=(0, 0, 0, 1))
        view.add_widget(area)
        old_seen = set(self.shorts_seen())
        st = {"items": [], "i": -1, "want": 0, "video": None, "open": True, "token": 0,
              "cache": {}, "pending": {}, "loading": False, "ended": False, "page": 0,
              "misses": 0, "ctx": {}, "new_seen": [], "t0": 0.0, "frac": 0.0}

        def current():
            return st["items"][st["i"]] if 0 <= st["i"] < len(st["items"]) else None

        def flash(text):
            msg.text = text
            Clock.schedule_once(lambda dt: msg.text == text and setattr(msg, "text", ""), 2.5)

        def set_prog(frac):
            st["frac"] = frac
            prog_bar.pos = prog.pos
            prog_bar.size = (prog.width * frac, prog.height)
        prog.bind(pos=lambda *_: set_prog(st["frac"]), size=lambda *_: set_prog(st["frac"]))

        def stop_video():
            vid, st["video"] = st["video"], None
            if vid is not None:
                vid.state = "stop"
                vid.unload()
                stage.remove_widget(vid)

        def pause_video():
            vid = st["video"]
            if vid is not None and vid.state == "play":
                vid.state = "pause"
                msg.text = "Pauza"

        def resolve(v, cb):
            """Adres strumienia filmu; wynik trzymany w pamięci, żeby powrót był natychmiastowy."""
            c = st["cache"].get(v["id"])
            if c and time.time() - c[0] < 1800:
                cb(c[1])
                return
            waiting = st["pending"].setdefault(v["id"], [])
            waiting.append(cb)
            if len(waiting) > 1:
                return

            def work():
                from kivy.core.video import Video as CoreVideo
                if CoreVideo is None:
                    raise RuntimeError("brak odtwarzacza wideo w Kivy")
                import yt_dlp
                opts = {"quiet": True, "logger": QUIET, "no_warnings": True, "noplaylist": True,
                        "format": VIDEO_FORMAT}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(v["url"], download=False)
                if not info.get("url"):
                    raise RuntimeError("brak strumienia wideo")
                cu = info.get("channel_url") or info.get("uploader_url")
                return {"src": info["url"], "title": info.get("title") or v["title"],
                        "channel": info.get("channel") or info.get("uploader") or v["channel"],
                        "ch_url": self.normalize_channel(cu) if cu else v.get("ch_url")}

            def done(res):
                if not isinstance(res, Exception):
                    st["cache"][v["id"]] = (time.time(), res)
                for fn in st["pending"].pop(v["id"], []):
                    fn(res)
            self.run_bg(work, done)

        def start(tok, v, res):
            if tok != st["token"] or not st["open"]:
                return
            if isinstance(res, Exception):
                msg.text = (f"Nie da się odtworzyć tego filmu.\n{self.explain(res)}\n"
                            "Przesuń w górę, aby pominąć.")
                return
            v.update(title=res["title"], channel=res["channel"], ch_url=res["ch_url"])
            title.text, ch.text = v["title"], v["channel"]
            try:
                from kivy.uix.video import Video
                vid = Video(source=res["src"], state="play", fit_mode="contain",
                            options={"eos": "loop"}, **full)
            except Exception as e:
                msg.text = f"Nie da się odtworzyć tutaj ({str(e)[:50]}).\nDotknij: W YT"
                return
            stage.add_widget(vid)
            st["video"], st["t0"] = vid, time.time()
            nxt = st["i"] + 1
            if nxt < len(st["items"]):          # następny film szykuje się w tle
                resolve(st["items"][nxt], lambda r: None)

        def go(i):
            items = st["items"]
            if i < 0:
                return
            if i >= len(items):
                if st["ended"]:
                    flash("To już wszystkie Shorts.\nPrzesuń w dół, aby wrócić.")
                else:
                    st["want"] = i
                    msg.text = "Szukam kolejnych..."
                    fetch_more()
                return
            stop_video()
            st["i"], st["want"], st["token"] = i, None, st["token"] + 1
            tok, v = st["token"], items[i]
            title.text = "" if v["title"] == "?" else v["title"]
            ch.text = v["channel"] or ""
            b_dl.text, b_later.text = "Pobierz", "Później"
            msg.text = "Wczytywanie..."
            set_prog(0)
            thumb.opacity = 0

            def show_thumb(p):
                if tok == st["token"] and st["open"] and not (st["video"] and st["video"].loaded):
                    thumb.source = p
                    thumb.opacity = 1
            self.short_thumb(v["id"], show_thumb)
            if v["id"] not in old_seen:
                old_seen.add(v["id"])
                st["new_seen"].append(v["id"])
            if ANIM["on"]:
                meta.opacity = 0
                anim(meta, d=0.3, opacity=1)
            if len(items) - i <= 3:
                fetch_more()
            resolve(v, lambda res: start(tok, v, res))

        def fetch_more():
            if st["loading"] or st["ended"]:
                return
            st["loading"] = True
            page, ctx = st["page"], st["ctx"]
            seen_before = set(old_seen)

            def done(res):
                st["loading"] = False
                if not st["open"]:
                    return
                if isinstance(res, Exception):
                    if not st["items"]:
                        msg.text = f"Nie udało się wczytać Shorts.\n{self.explain(res)}"
                    return
                have = {v["id"] for v in st["items"]}
                new = [v for v in res if v["id"] not in have]
                st["page"] += 1
                if not new:
                    st["misses"] += 1
                    if st["misses"] >= 2:
                        st["ended"] = True
                        if not st["items"]:
                            msg.text = "Nie znaleziono Shorts na ten temat."
                        elif st["want"] is not None:
                            flash("To już wszystkie Shorts.\nPrzesuń w dół, aby wrócić.")
                    else:
                        Clock.schedule_once(lambda dt: st["open"] and fetch_more(), 0.1)
                    return
                st["misses"] = 0
                fresh = [v for v in new if v["id"] not in seen_before]
                st["items"] += fresh + [v for v in new if v["id"] in seen_before]
                if st["want"] is not None and st["want"] < len(st["items"]):
                    go(st["want"])
            self.run_bg(lambda: self.shorts_fetch(query, page, ctx), done)

        def tick(_dt):
            vid = st["video"]
            if vid is None:
                return
            if vid.loaded:
                thumb.opacity = 0
                if msg.text == "Wczytywanie...":
                    msg.text = ""
            if vid.duration and vid.duration > 0:
                set_prog(max(0.0, min(1.0, vid.position / vid.duration)))
            elif not vid.loaded and time.time() - st["t0"] > 15 and msg.text == "Wczytywanie...":
                msg.text = "Nie da się odtworzyć tutaj.\nDotknij W YT albo przesuń dalej."

        def tap():
            vid = st["video"]
            if vid is None:
                return
            if vid.state == "play":
                vid.state = "pause"
                msg.text = "Pauza"
            else:
                vid.state = "play"
                msg.text = ""

        def do_download(*_):
            v = current()
            if v:
                self.download(v["url"], kind="video", title=v["title"])
                b_dl.text = "W kolejce"

        def do_channel(*_):
            v = current()
            if v and v.get("ch_url"):
                pause_video()
                self.open_channel(v["ch_url"])
            elif v:
                flash("Kanał będzie znany po wczytaniu filmu")

        def do_later(*_):
            v = current()
            if v:
                self.yt_later(v)
                b_later.text = "Dodano"

        def do_external(*_):
            v = current()
            if v:
                pause_video()
                open_external(v["url"])

        def closed(*_):
            st["open"] = False
            ev.cancel()
            stop_video()
            if st["new_seen"]:
                seen = st["new_seen"][::-1] + self.shorts_seen()
                self.lib.set_setting("shorts_seen", json.dumps(seen[:400]))
        area.swipe_cb = lambda d: go(st["i"] + d)     # palec w górę = następny
        area.tap_cb = tap
        b_dl.bind(on_release=do_download)
        b_ch.bind(on_release=do_channel)
        b_later.bind(on_release=do_later)
        b_yt.bind(on_release=do_external)
        b_shr.bind(on_release=lambda *_: current() and self.share_video(current()))
        b_close.bind(on_release=lambda *_: view.dismiss())
        ev = Clock.schedule_interval(tick, 0.25)
        view.bind(on_dismiss=closed)
        view.open()
        fetch_more()
        if not old_seen:
            Clock.schedule_once(lambda dt: st["open"] and st["i"] <= 0 and flash(
                "Przesuń w górę: następny film\nDotknij: pauza"), 4)


for _name, _fn in list(vars(YTPlus).items()):
    if not _name.startswith("__"):
        setattr(MuzykaApp, _name, _fn)


# =====================================================================
#  LEOX PLAYER - DODATEK KAFELKI (gra: dotykaj czarnych kafelków)
# =====================================================================
import array
import wave
from kivy.core.text import Label as CoreLabel

# Melodie z domeny publicznej. "-" po nucie = długi kafelek (przytrzymaj).
TILE_SONGS = {
    "Oda do radości": "E4 E4 F4 G4 G4 F4 E4 D4 C4 C4 D4 E4 E4- D4 D4- "
                      "E4 E4 F4 G4 G4 F4 E4 D4 C4 C4 D4 E4 D4- C4 C4- "
                      "D4 D4 E4 C4 D4 E4 F4 E4 C4 D4 E4 F4 E4 D4 C4 D4 G3- "
                      "E4 E4 F4 G4 G4 F4 E4 D4 C4 C4 D4 E4 D4- C4 C4-",
    "Dla Elizy": "E5 D#5 E5 D#5 E5 B4 D5 C5 A4- C4 E4 A4 B4- E4 G#4 B4 C5- "
                 "E4 E5 D#5 E5 D#5 E5 B4 D5 C5 A4- C4 E4 A4 B4- E4 C5 B4 A4-",
    "Wlazł kotek na płotek": "G4 E4 E4 F4 D4 D4 C4 E4 G4- G4 E4 E4 F4 D4 D4 C4 E4 C4-",
    "Panie Janie": "C4 D4 E4 C4 C4 D4 E4 C4 E4 F4 G4- E4 F4 G4- "
                   "G4 A4 G4 F4 E4 C4 G4 A4 G4 F4 E4 C4 C4 G3 C4- C4 G3 C4-",
    "Mrugaj, gwiazdko": "C4 C4 G4 G4 A4 A4 G4- F4 F4 E4 E4 D4 D4 C4- "
                        "G4 G4 F4 F4 E4 E4 D4- G4 G4 F4 F4 E4 E4 D4- "
                        "C4 C4 G4 G4 A4 A4 G4- F4 F4 E4 E4 D4 D4 C4-",
}
NOTE_IDX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_freq(n):
    m = re.match(r"([A-G])(#?)(\d)", n)
    midi = 12 * (int(m.group(3)) + 1) + NOTE_IDX[m.group(1)] + (1 if m.group(2) else 0)
    return 440.0 * 2 ** ((midi - 69) / 12)


def parse_song(txt):
    return [(tok.rstrip("-"), 2 if tok.endswith("-") else 1) for tok in txt.split()]


def synth_tone(path, freqs, dur, rate=22050):
    """Prosty dźwięk pianina: ton podstawowy + alikwoty, szybkie uderzenie, wygasanie."""
    n = int(dur * rate)
    data = array.array("h", bytes(2 * n))
    attack = int(0.004 * rate)
    amp = 9000 / len(freqs)
    for f in freqs:
        decay = math.exp(-(2.2 + f / 500) / rate)
        ws = [(2 * math.pi * f * k * (1 + 0.0004 * k * k) / rate, a)
              for k, a in ((1, 1.0), (2, 0.45), (3, 0.22), (4, 0.1)) if f * k < rate / 2]
        env = 1.0
        for i in range(n):
            s = 0.0
            for w, a in ws:
                s += a * math.sin(w * i)
            e = env * (i / attack if i < attack else 1.0)
            data[i] = max(-32767, min(32767, data[i] + int(amp * e * s)))
            env *= decay
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(data.tobytes())


class TileSounds:
    """Nuty generowane raz do plików WAV, potem tylko odtwarzane."""

    def __init__(self, folder, notes):
        self.folder = Path(folder)
        self.notes = sorted(set(notes)) + ["BLAD"]
        self.snd, self.turn = {}, {}

    def path(self, n):
        return self.folder / f"{n.replace('#', 's')}.wav"

    def prepare(self):                          # w wątku
        self.folder.mkdir(parents=True, exist_ok=True)
        for n in self.notes:
            p = self.path(n)
            if not p.exists():
                if n == "BLAD":
                    synth_tone(p, [130.81, 138.59, 185.0], 0.6)
                else:
                    synth_tone(p, [note_freq(n)], 1.1)

    def load(self):                             # w wątku UI
        for n in self.notes:
            try:
                pair = [SoundLoader.load(str(self.path(n))) for _ in range(2)]
                self.snd[n] = [s for s in pair if s]
            except Exception:
                pass

    def play(self, n):
        lst = self.snd.get(n)
        if not lst:
            return
        i = self.turn.get(n, 0)
        self.turn[n] = (i + 1) % len(lst)
        try:
            lst[i].stop()
            lst[i].play()
        except Exception:
            pass


def tiles_vgrad(bottom, top, n=64):
    buf = bytearray()
    for i in range(n):
        k = i / (n - 1)
        for c in range(4):
            buf.append(int(255 * (bottom[c] * (1 - k) + top[c] * k)))
    tex = Texture.create(size=(1, n), colorfmt="rgba")
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    return tex


def tiles_blob(n=48):
    buf = bytearray()
    c = (n - 1) / 2
    for y in range(n):
        for x in range(n):
            d = min(1.0, math.hypot(x - c, y - c) / c)
            buf += bytes((255, 255, 255, int(255 * (1 - d) ** 2)))
    tex = Texture.create(size=(n, n), colorfmt="rgba")
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    return tex


class TilesBg(Widget):
    """Tło gry: jasny gradient w kolorach motywu, sieć punktów i miękkie światła."""
    NPTS = 13

    def __init__(self, **kw):
        super().__init__(**kw)
        h, _l, s = colorsys.rgb_to_hls(*ACCENT[:3])
        s = max(0.35, min(0.75, s))
        top = colorsys.hls_to_rgb((h + 0.08) % 1, 0.87, s)
        bot = colorsys.hls_to_rgb((h - 0.05) % 1, 0.72, s)
        blob = tiles_blob()
        self.pts = [[random.random(), random.random(), random.uniform(-0.025, 0.025),
                     random.uniform(-0.025, 0.025)] for _ in range(self.NPTS)]
        self.bok = [[random.random(), random.random(), dp(random.uniform(40, 110)),
                     random.uniform(0.006, 0.02), random.uniform(0.10, 0.22)] for _ in range(7)]
        with self.canvas:
            Color(1, 1, 1, 1)
            self.grad = Rectangle(texture=tiles_vgrad((*bot, 1), (*top, 1)))
            self.bok_g = []
            for b in self.bok:
                Color(1, 1, 1, b[4])
                self.bok_g.append(Ellipse(texture=blob))
            self.lines = []
            for i in range(self.NPTS):
                for j in range(i + 1, self.NPTS):
                    c = Color(1, 1, 1, 0)
                    self.lines.append((i, j, c, Line(points=[0, 0, 0, 0], width=1)))
            Color(1, 1, 1, 0.95)
            self.dots = [Ellipse(texture=blob) for _ in range(self.NPTS)]
        self.bind(pos=self.redraw, size=self.redraw)
        self.ev = Clock.schedule_interval(self.step, 1 / 30)

    def step(self, dt):
        for p in self.pts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            if not -0.05 < p[0] < 1.05:
                p[2] = -p[2]
            if not -0.05 < p[1] < 1.05:
                p[3] = -p[3]
        for b in self.bok:
            b[1] += b[3] * dt
            if b[1] > 1.2:
                b[0], b[1] = random.random(), -0.2
        self.redraw()

    def redraw(self, *_):
        W, H, X, Y = self.width, self.height, self.x, self.y
        self.grad.pos, self.grad.size = self.pos, self.size
        for e, b in zip(self.bok_g, self.bok):
            r = b[2]
            e.pos, e.size = (X + b[0] * W - r, Y + b[1] * H - r), (2 * r, 2 * r)
        P = [(X + p[0] * W, Y + p[1] * H) for p in self.pts]
        D = max(1.0, min(W, H) * 0.55)
        for i, j, c, ln in self.lines:
            (x1, y1), (x2, y2) = P[i], P[j]
            d = math.hypot(x1 - x2, y1 - y2)
            if d < D:
                c.a = 0.55 * (1 - d / D)
                ln.points = [x1, y1, x2, y2]
            else:
                c.a = 0
        r = dp(6)
        for (x, y), e in zip(P, self.dots):
            e.pos, e.size = (x - r, y - r), (2 * r, 2 * r)

    def stop(self):
        self.ev.cancel()


class TilesGame(Widget):
    """4 tory, kafelki zjeżdżają w dół. Dotknięcie gra kolejną nutę melodii."""
    LANES, ROWS = 4, 4

    def __init__(self, song, sounds, on_score, on_over, on_flash, **kw):
        super().__init__(**kw)
        self.notes = parse_song(TILE_SONGS[song])
        self.sounds, self.on_score, self.on_over, self.on_flash = sounds, on_score, on_over, on_flash
        self.tiles, self.rings, self.flashes = [], [], []
        self.scroll, self.state, self.score, self.hits = 0.0, "ready", 0, 0
        self.next_row, self.note_i, self.loop, self.loop_now, self.last_lane = 1, 0, 0, 0, -1
        self.back = None                         # cofnięcie po błędzie, żeby było widać kafelek
        self.body = (0.07, 0.07, 0.09)
        self.fill_tex = tiles_vgrad((*ACCENT_DIM[:3], 0.55), (*ACCENT[:3], 1))
        self.body_tex = tiles_vgrad((*self.body, 1), (0.17, 0.17, 0.21, 1))
        lbl = CoreLabel(text="Start", font_size=sp(24), bold=True)
        lbl.refresh()
        self.start_tex = lbl.texture
        with self.canvas.before:
            Color(1, 1, 1, 0.5)
            self.seps = [Line(points=[0, 0, 0, 0], width=1) for _ in range(self.LANES - 1)]
        self.tile_layer, self.fx_layer = InstructionGroup(), InstructionGroup()
        self.canvas.add(self.tile_layer)
        self.canvas.after.add(self.fx_layer)
        self.bind(pos=self.layout, size=self.layout)
        self.ev = Clock.schedule_interval(self.step, 1 / 60)

    @property
    def rowh(self):
        return max(1.0, self.height / self.ROWS)

    @property
    def lw(self):
        return max(1.0, self.width / self.LANES)

    def layout(self, *_):
        for i, ln in enumerate(self.seps):
            x = self.x + (i + 1) * self.lw
            ln.points = [x, self.y, x, self.top]
        self.spawn()
        self.place()

    def speed(self):                            # rzędy na sekundę
        return min(9.0, (2.7 + 0.04 * self.hits) * (1 + 0.15 * self.loop_now))

    # --- kafelki
    def spawn(self):
        while self.next_row < self.scroll + self.ROWS + 2:
            note, ln = self.notes[self.note_i]
            start = self.next_row == 1
            if start:
                ln = 1
            lane = random.choice([i for i in range(self.LANES) if i != self.last_lane])
            self.last_lane = lane
            t = {"lane": lane, "row": self.next_row, "len": ln, "note": note, "state": "new",
                 "fill": 0.0, "touch": None, "hit_t": 0.0, "start": start,
                 "loop": self.loop if self.note_i == 0 and self.loop > 0 else None}
            self.make(t)
            self.tiles.append(t)
            self.next_row += ln
            self.note_i += 1
            if self.note_i >= len(self.notes):
                self.note_i = 0
                self.loop += 1

    def make(self, t):
        g = InstructionGroup()
        if t["start"]:
            t["c"] = Color(*ACCENT_DIM[:3], 1)
            t["r"] = Rectangle(texture=white_tex())
        else:
            t["c"] = Color(1, 1, 1, 1)
            t["r"] = Rectangle(texture=self.body_tex)
        g.add(t["c"])
        g.add(t["r"])
        if t["start"]:
            g.add(Color(1, 1, 1, 1))
            t["lbl"] = Rectangle(texture=self.start_tex, size=self.start_tex.size)
            g.add(t["lbl"])
        if t["len"] > 1:
            t["fc"] = Color(1, 1, 1, 1)
            t["f"] = Rectangle(texture=self.fill_tex, size=(0, 0))
            t["lc"] = Color(*ACCENT[:3], 0.6)
            t["ln"] = Line(points=[0, 0, 0, 0], width=dp(1.2))
            t["dot"] = Ellipse()
            t["rc"] = Color(*ACCENT[:3], 0.95)
            t["ring"] = Line(circle=(0, 0, 1), width=dp(2))
            for ins in (t["fc"], t["f"], t["lc"], t["ln"], t["dot"], t["rc"], t["ring"]):
                g.add(ins)
        t["g"] = g
        self.tile_layer.add(g)

    def place(self):
        rh, lw = self.rowh, self.lw
        for t in self.tiles:
            x = self.x + t["lane"] * lw
            y = self.y + (t["row"] - self.scroll) * rh
            h = t["len"] * rh
            t["r"].pos, t["r"].size = (x + 1, y + 1), (lw - 2, h - 2)
            if t["start"]:
                tw, th = self.start_tex.size
                t["lbl"].pos = (x + (lw - tw) / 2, y + (h - th) / 2)
            if t["len"] > 1:
                fh = t["fill"] * rh
                t["f"].pos, t["f"].size = (x + 1, y + 1), (lw - 2, max(0.0, fh - 2))
                cx = x + lw / 2
                fy = y + max(fh, rh * 0.35)
                t["ln"].points = [cx, fy, cx, y + h - rh * 0.25]
                rd = dp(5)
                t["dot"].pos, t["dot"].size = (cx - rd, y + h - rh * 0.25 - rd), (2 * rd, 2 * rd)
                t["ring"].circle = (cx, fy, dp(16))

    def step(self, dt):
        dt = min(dt, 0.05)
        now = time.time()
        if self.state == "play":
            self.scroll += self.speed() * dt
            for t in self.tiles:
                if t["state"] == "held":
                    v = (t["touch"].y - self.y) / self.rowh + self.scroll - t["row"]
                    t["fill"] = max(t["fill"], min(float(t["len"]), v))
                    if t["fill"] >= t["len"] - 0.05:
                        self.release(t, True)
                elif t["state"] == "new" and t["row"] - self.scroll < -0.1:
                    self.lose(t)
                    break
            if self.state == "play":
                self.spawn()
        elif self.back:
            a, b, t0 = self.back
            k = min(1.0, (now - t0) / 0.35)
            self.scroll = a + (b - a) * (1 - (1 - k) ** 3)
            if k >= 1:
                self.back = None
        for t in self.tiles:
            if t["state"] == "hit":
                k = min(1.0, (now - t["hit_t"]) / 0.25)
                g = 0.07 + 0.68 * k
                t["c"].rgba = (g, g, g + 0.03, 1 - 0.65 * k)
                if t["len"] > 1:
                    t["fc"].a, t["rc"].a, t["lc"].a = 1 - k, 0.95 * (1 - k), 0.6 * (1 - k)
            elif t["state"] == "miss":
                on = int((now - t["hit_t"]) * 6) % 2 == 0
                t["c"].rgba = (0.92, 0.2, 0.25, 1) if on else (*self.body, 1)
        keep = []
        for t in self.tiles:
            if t["row"] + t["len"] - self.scroll < -1 and t["state"] not in ("new", "held"):
                self.tile_layer.remove(t["g"])
            else:
                keep.append(t)
        self.tiles = keep
        self.fx(now)
        self.place()

    # --- dotyk
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos) or self.state == "over":
            return super().on_touch_down(touch)
        lane = max(0, min(self.LANES - 1, int((touch.x - self.x) / self.lw)))
        r = (touch.y - self.y) / self.rowh + self.scroll
        found = None
        for t in self.tiles:
            if t["lane"] == lane and t["row"] - 0.15 <= r < t["row"] + t["len"] + 0.15:
                found = t
                break
        if self.state == "ready":
            if found is not None and found["start"]:
                self.state = "play"
                self.hit(found, touch)
            return True
        if found is None:
            self.lose_cell(lane, math.floor(r))
        elif found["state"] == "new":
            self.hit(found, touch)
        return True

    def on_touch_up(self, touch):
        t = touch.ud.get("kafel")
        if t is not None and t["state"] == "held":
            self.release(t, False)
            return True
        return super().on_touch_up(touch)

    def hit(self, t, touch):
        self.sounds.play(t["note"])
        self.hits += 1
        if t.get("loop"):
            self.loop_now = t["loop"]
            self.on_flash(f"Szybciej! Runda {t['loop'] + 1}")
        t["hit_t"] = time.time()
        self.add_score(1)
        self.ring(touch.x, touch.y)
        if t["len"] > 1:
            t["state"], t["touch"] = "held", touch
            touch.ud["kafel"] = t
        else:
            t["state"] = "hit"
            t["r"].texture = white_tex()

    def release(self, t, full):
        t["state"], t["touch"], t["hit_t"] = "hit", None, time.time()
        t["r"].texture = white_tex()
        if full:
            self.add_score(t["len"] - 1)
            x = self.x + (t["lane"] + 0.5) * self.lw
            self.ring(x, self.y + (t["row"] + t["len"] - self.scroll) * self.rowh, big=True)

    def add_score(self, n):
        self.score += n
        self.on_score(self.score)

    # --- koniec gry
    def lose(self, t):
        t["state"], t["hit_t"] = "miss", time.time()
        t["r"].texture = white_tex()
        self.game_over(t["row"] - 0.6)

    def lose_cell(self, lane, row):
        g = InstructionGroup()
        c, r = Color(0.92, 0.2, 0.25, 0.85), Rectangle()
        g.add(c)
        g.add(r)
        self.fx_layer.add(g)
        self.flashes.append({"lane": lane, "row": row, "c": c, "r": r, "t": time.time()})
        self.game_over(None)

    def game_over(self, target):
        self.state = "over"
        self.sounds.play("BLAD")
        for t in self.tiles:
            if t["state"] == "held":
                self.release(t, False)
        if target is not None:
            self.back = (self.scroll, max(0.0, target), time.time())
        Clock.schedule_once(lambda dt: self.on_over(self.score), 1.4)

    # --- efekty
    def ring(self, x, y, big=False):
        g = InstructionGroup()
        c, ln = Color(1, 1, 1, 0.6), Line(circle=(x, y, 1), width=dp(2))
        g.add(c)
        g.add(ln)
        self.fx_layer.add(g)
        self.rings.append({"x": x, "row": (y - self.y) / self.rowh + self.scroll, "g": g, "c": c,
                           "l": ln, "t": time.time(), "max": self.lw * (0.9 if big else 0.55)})

    def fx(self, now):
        for r in list(self.rings):
            k = (now - r["t"]) / 0.45
            if k >= 1:
                self.fx_layer.remove(r["g"])
                self.rings.remove(r)
                continue
            y = self.y + (r["row"] - self.scroll) * self.rowh
            r["l"].circle = (r["x"], y, dp(8) + r["max"] * (1 - (1 - k) ** 2))
            r["c"].a = 0.6 * (1 - k)
        for f in self.flashes:
            x = self.x + f["lane"] * self.lw
            y = self.y + (f["row"] - self.scroll) * self.rowh
            f["r"].pos, f["r"].size = (x + 1, y + 1), (self.lw - 2, self.rowh - 2)
            f["c"].a = 0.85 if int((now - f["t"]) * 6) % 2 == 0 else 0.25

    def stop(self):
        self.ev.cancel()


class SharePlus:
    """Udostępnianie: link (YouTube, radio, podcast) albo sam plik muzyczny."""

    @staticmethod
    def yt_short_link(url):
        m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url or "")
        return f"https://youtu.be/{m.group(1)}" if m else url

    def share_video(self, v):
        name = v.get("title") or "Film"
        self.share_send(f"{name}\n{self.yt_short_link(v['url'])}", name)

    def share_track(self, t):
        path, title, artist = t[0], t[1] or "?", t[2] or ""
        name = f"{artist} - {title}" if artist else title
        if self.is_youtube(path):
            self.share_send(f"{name}\n{self.yt_short_link(path)}", name)
        elif self.is_radio(path):
            self.share_send(f"Słucham radia: {title}\n{path[len('radio:'):]}", title)
        elif self.is_stream(path):
            self.share_send(f"{name}\n{path}", name)
        else:
            q = urllib.parse.quote_plus(f"{artist} {title}".strip())
            link = f"https://www.youtube.com/results?search_query={q}"
            self.list_popup(f"Udostępnij: {name}", [
                {"text": "Link (ten utwór w YouTube)\nOdbiorca posłucha bez pobierania",
                 "tap": lambda b: self.share_send(f"{name}\n{link}", name)},
                {"text": "Sam plik muzyczny\nOdbiorca dostanie plik do zapisania",
                 "tap": lambda b: self.share_file(path, name, link)}])

    def share_send(self, text, subject):
        try:
            share_text(text, subject)
        except Exception:
            try:
                from kivy.core.clipboard import Clipboard
                Clipboard.copy(text)
                self.set_status("Link skopiowany - wklej go w wiadomości")
            except Exception as e:
                self.set_status(f"Nie da się udostępnić: {e}")

    def share_file(self, path, name, link, retry=True):
        try:
            from jnius import autoclass, cast
            ctx = android_context()
            Media = autoclass("android.provider.MediaStore$Audio$Media")
            cur = ctx.getContentResolver().query(Media.EXTERNAL_CONTENT_URI, ["_id"],
                                                 "_data=?", [str(path)], None)
            found = cur is not None and cur.moveToFirst()
            if not found:
                if cur is not None:
                    cur.close()
                if retry:                       # Android jeszcze nie zna pliku - dopisujemy go
                    autoclass("android.media.MediaScannerConnection").scanFile(
                        ctx, [str(path)], None, None)
                    self.set_status("Przygotowanie pliku...")
                    Clock.schedule_once(lambda dt: self.share_file(path, name, link, False), 2)
                    return
                raise RuntimeError("Android nie widzi pliku")
            uri = autoclass("android.content.ContentUris").withAppendedId(
                Media.EXTERNAL_CONTENT_URI, cur.getLong(0))
            cur.close()
            Intent = autoclass("android.content.Intent")
            JString = autoclass("java.lang.String")
            it = Intent(Intent.ACTION_SEND)
            it.setType(AUDIO_TYPES.get(Path(path).suffix.lower(), "audio/*"))
            it.putExtra(Intent.EXTRA_STREAM, cast("android.os.Parcelable", uri))
            it.putExtra(Intent.EXTRA_SUBJECT, cast("java.lang.CharSequence", JString(name)))
            it.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            ch = Intent.createChooser(it, cast("java.lang.CharSequence", JString(f"Udostępnij: {name}")))
            ch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            ch.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            ctx.startActivity(ch)
        except Exception as e:
            self.set_status(f"Pliku nie da się wysłać ({str(e)[:50]}) - wysyłam link")
            self.share_send(f"{name}\n{link}", name)


for _name, _fn in list(vars(SharePlus).items()):
    if not _name.startswith("__"):
        setattr(MuzykaApp, _name, _fn)


class TilesPlus:
    def show_tiles(self):
        paused = False
        if getattr(self, "active", False) and not self.player.paused:
            self.toggle()                       # muzyka cichnie na czas gry
            paused = True
        root = FloatLayout()
        bg = TilesBg(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        root.add_widget(bg)
        score = Label(text="", font_size="52sp", bold=True, color=(0.93, 0.27, 0.33, 1),
                      size_hint=(1, None), height=dp(80), pos_hint={"x": 0, "top": 0.98})
        banner = Label(text="", font_size="22sp", bold=True, color=(1, 1, 1, 1),
                       size_hint=(1, None), height=dp(40), pos_hint={"x": 0, "top": 0.86})
        fx = FxFront(border=False, size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        for w in (score, banner, fx):
            root.add_widget(w)
        pop = RoundPopup(title="Kafelki", content=root, size_hint=(1, 1))
        songs = list(TILE_SONGS)
        last = self.lib.get_setting("kafelki_utwor", songs[0])
        st = {"game": None, "panel": None, "open": True,
              "song": last if last in TILE_SONGS else songs[0]}
        notes = [n for s in TILE_SONGS.values() for n, _ in parse_song(s)]
        snd = TileSounds(Path(self.user_data_dir) / "kafelki_v1", notes)

        def record(song):
            try:
                return int(self.lib.get_setting(f"kafelki_rekord_{song}", "0"))
            except ValueError:
                return 0

        def mk(text, size, color, bold, h):
            lb = Label(text=text, font_size=size, color=color, bold=bold, halign="center",
                       valign="middle", size_hint_y=None, height=h)
            lb.bind(width=lambda w, v: setattr(w, "text_size", (v, None)))
            return lb

        def panel(widgets, buttons):
            if st["panel"] is not None:
                root.remove_widget(st["panel"])
            box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(18),
                            size_hint=(0.88, None), pos_hint={"center_x": 0.5, "center_y": 0.5})
            with box.canvas.before:
                Color(*BG_POP[:3], 0.93)
                rr = RoundedRectangle(radius=[dp(22)])
            box.bind(pos=lambda w, v: setattr(rr, "pos", v), size=lambda w, v: setattr(rr, "size", v))
            h = 0
            for w in widgets:
                box.add_widget(w)
                h += w.height
            for text, cb, hi in buttons:
                b = RoundButton(text=text, size_hint_y=None, height=dp(54),
                                bg=list(ACCENT_DIM if hi else CARD_HI))
                b.bind(on_release=lambda *_, cb=cb: cb())
                box.add_widget(b)
                h += dp(54)
            n = len(widgets) + len(buttons)
            box.height = h + dp(36) + dp(8) * max(0, n - 1)
            root.add_widget(box, index=1)       # nad grą, pod konfetti
            st["panel"] = box
            if ANIM["on"]:
                box.opacity = 0
                anim(box, d=0.3, opacity=1)

        def stop_game():
            if st["game"] is not None:
                st["game"].stop()
                root.remove_widget(st["game"])
                st["game"] = None

        def set_score(n):
            score.text = str(n)
            if ANIM["on"]:
                score.font_size = sp(62)
                anim(score, d=0.18, font_size=sp(52))

        def flash(text):
            banner.text = text
            banner.opacity = 1
            Animation.cancel_all(banner)
            (Animation(d=1.0) + Animation(opacity=0, d=0.8)).start(banner)

        def menu():
            stop_game()
            score.text = ""
            panel([mk("Kafelki", "30sp", ACCENT, True, dp(48)),
                   mk("Dotykaj czarnych kafelków. Nie przepuść żadnego i nie dotykaj pustych "
                      "pól. Długie kafelki przytrzymaj.", "14sp", MUTED, False, dp(66))],
                  [(f"{s}   (rekord {record(s)})", lambda s=s: start(s), s == st["song"])
                   for s in songs] + [("Zamknij", pop.dismiss, False)])

        def start(song):
            st["song"] = song
            self.lib.set_setting("kafelki_utwor", song)
            if st["panel"] is not None:
                root.remove_widget(st["panel"])
                st["panel"] = None
            stop_game()
            set_score(0)
            g = TilesGame(song, snd, on_score=set_score, on_over=over, on_flash=flash,
                          size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
            root.add_widget(g, index=len(root.children) - 1)   # tuż nad tłem
            st["game"] = g

        def over(n):
            if not st["open"]:
                return
            best = record(st["song"])
            new = n > best
            if new:
                self.lib.set_setting(f"kafelki_rekord_{st['song']}", n)
            panel([mk("Nowy rekord!" if new else "Koniec gry", "26sp", ACCENT, True, dp(44)),
                   mk(str(n), "56sp", TEXT, True, dp(80)),
                   mk(f"{st['song']}   rekord: {max(n, best)}", "14sp", MUTED, False, dp(30))],
                  [("Jeszcze raz", lambda: start(st["song"]), True),
                   ("Inna melodia", menu, False), ("Zamknij", pop.dismiss, False)])
            if new and n > 0:
                fx.burst(root.center_x, root.center_y + dp(120), n=80)

        ev = Clock.schedule_interval(lambda dt: fx.update(dt), 1 / 30)

        def closed(*_):
            st["open"] = False
            stop_game()
            bg.stop()
            ev.cancel()
            if paused and getattr(self, "active", False) and self.player.paused:
                self.toggle()
        pop.bind(on_dismiss=closed)
        pop.open()

        panel([mk("Przygotowanie dźwięków pianina...", "16sp", MUTED, False, dp(40))], [])

        def work():
            snd.prepare()
            return True

        def done(_res):
            snd.load()
            if st["open"]:
                menu()
        self.run_bg(work, done)


for _name, _fn in list(vars(TilesPlus).items()):
    if not _name.startswith("__"):
        setattr(MuzykaApp, _name, _fn)


# =====================================================================
#  LEOX PLAYER - SPOŁECZNOŚĆ (Supabase)
#  Konta i profile, czat publiczny, wspólna muzyka na serwerze,
#  panel admina: akceptacja kont, bany, wyciszanie, przerwa techniczna,
#  ogłoszenia, statystyki, dodawanie i usuwanie utworów.
#  Konfiguracja: wpisz adres projektu i klucz "anon public" poniżej.
#  Baza: plik supabase/schema.sql (uruchom raz w SQL Editor).
# =====================================================================
import uuid
import urllib.error

SUPABASE_URL = "https://wawckouwxagilnwqogcw.supabase.co"
SUPABASE_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indhd2Nrb3V3eGFnaWxud3FvZ2N3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTM5MjYwMzMsImV4cCI6MjEwOTUwMjAzM30"
                ".-rCp4uOKSpFeXBNWdrsU1IOLlaLNtT1J7um9Tr3nlzQ")   # klucz publiczny (anon) - dane chroni RLS
LOGIN_DOMAIN = "leox.app"  # konto = nazwa@leox.app (bez prawdziwej skrzynki)

AUDIO_MIME = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac",
              ".ogg": "audio/ogg", ".opus": "audio/opus", ".flac": "audio/flac",
              ".wav": "audio/wav", ".webm": "audio/webm"}


class SupaError(Exception):
    def __init__(self, msg, code=0):
        super().__init__(msg)
        self.code = code


def supa_message(raw):
    try:
        d = json.loads(raw)
    except Exception:
        return raw[:200] if raw else "błąd serwera"
    if isinstance(d, dict):
        for k in ("msg", "message", "error_description", "error"):
            if d.get(k):
                return str(d[k])
    return str(d)[:200]


PL_ERRORS = {
    "invalid login credentials": "Zła nazwa albo hasło",
    "user already registered": "Taka nazwa jest już zajęta",
    "password should be at least": "Hasło musi mieć co najmniej 6 znaków",
    "duplicate key": "Taka nazwa jest już zajęta",
    "row-level security": "Brak uprawnień (konto nieaktywne?)",
    "jwt expired": "Sesja wygasła - zaloguj się ponownie",
}


def pl_error(e):
    s = str(e)
    low = s.lower()
    for k, v in PL_ERRORS.items():
        if k in low:
            return v
    if isinstance(e, urllib.error.URLError) or "urlopen" in low or "timed out" in low:
        why = getattr(e, "reason", None) or s
        return f"Brak połączenia z serwerem ({str(why)[:120]})"
    return s


class Supa:
    """Mały klient Supabase (logowanie, baza REST, pliki) na samym urllib."""

    def __init__(self, url, key, load, save):
        self.url, self.key = url.rstrip("/"), key
        self._save_fn = save
        try:
            self.session = json.loads(load() or "{}")
        except ValueError:
            self.session = {}
        self.lock = threading.Lock()

    # --- sesja
    @property
    def uid(self):
        return (self.session.get("user") or {}).get("id")

    def logged_in(self):
        return bool(self.session.get("refresh_token"))

    def _store(self, s):
        if s.get("expires_in"):
            s["expires_at"] = time.time() + int(s["expires_in"])
        self.session = s
        self._save_fn(json.dumps(s))

    def clear(self):
        self.session = {}
        self._save_fn("")

    def _ensure_fresh(self):
        if self.logged_in() and self.session.get("expires_at", 0) - 60 < time.time():
            self.refresh()

    def refresh(self):
        with self.lock:
            if self.session.get("expires_at", 0) - 60 > time.time():
                return
            s = self._raw("POST", "/auth/v1/token?grant_type=refresh_token",
                          {"refresh_token": self.session.get("refresh_token")}, token=self.key)
            self._store(s)

    # --- zapytania
    def _raw(self, method, path, body=None, token=None, headers=None, data=None, timeout=25):
        h = {"apikey": self.key, "Authorization": f"Bearer {token or self.key}"}
        if data is None and body is not None:
            data = json.dumps(body).encode("utf-8")
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        req = urllib.request.Request(self.url + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                txt = r.read()
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            raise SupaError(supa_message(raw), e.code)
        return json.loads(txt) if txt else None

    def req(self, method, path, body=None, headers=None, data=None, timeout=25):
        self._ensure_fresh()
        try:
            return self._raw(method, path, body, self.session.get("access_token"), headers, data,
                             timeout)
        except SupaError as e:
            if e.code == 401 and self.logged_in():
                self.session["expires_at"] = 0
                self.refresh()
                return self._raw(method, path, body, self.session.get("access_token"), headers,
                                 data, timeout)
            raise

    # --- konto
    def signup(self, username, password, display):
        s = self._raw("POST", "/auth/v1/signup", {
            "email": f"{username}@{LOGIN_DOMAIN}", "password": password,
            "data": {"username": username, "display_name": display or username}})
        if not s or not s.get("access_token"):
            raise SupaError("Serwer wymaga potwierdzenia e-mail. Admin musi wyłączyć "
                            "\"Confirm email\" w Supabase (Authentication -> Sign In / Providers -> Email).")
        self._store(s)

    def login(self, username, password):
        s = self._raw("POST", "/auth/v1/token?grant_type=password",
                      {"email": f"{username}@{LOGIN_DOMAIN}", "password": password})
        self._store(s)

    def change_password(self, password):
        self.req("PUT", "/auth/v1/user", {"password": password})

    def logout(self):
        try:
            self.req("POST", "/auth/v1/logout", timeout=8)
        except Exception:
            pass
        self.clear()

    # --- baza
    def select(self, table, query):
        return self.req("GET", f"/rest/v1/{table}?{query}") or []

    def insert(self, table, row):
        return self.req("POST", f"/rest/v1/{table}", row,
                        headers={"Prefer": "return=representation"})

    def update(self, table, filt, values):
        res = self.req("PATCH", f"/rest/v1/{table}?{filt}", values,
                       headers={"Prefer": "return=representation"})
        if not res:
            raise SupaError("Nic nie zmieniono (brak uprawnień?)")
        return res

    def delete(self, table, filt):
        return self.req("DELETE", f"/rest/v1/{table}?{filt}")

    def rpc(self, fn, args=None):
        return self.req("POST", f"/rest/v1/rpc/{fn}", args or {})

    # --- pliki
    def upload(self, obj, path, mime, bucket="music"):
        data = Path(path).read_bytes()
        self.req("POST", f"/storage/v1/object/{bucket}/{urllib.parse.quote(obj)}", data=data,
                 headers={"Content-Type": mime, "x-upsert": "false"}, timeout=600)
        return len(data)

    def remove_object(self, obj, bucket="music"):
        self.req("DELETE", f"/storage/v1/object/{bucket}", {"prefixes": [obj]})

    def signed_urls(self, objs, expires=12 * 3600, bucket="music"):
        if not objs:
            return {}
        res = self.req("POST", f"/storage/v1/object/sign/{bucket}",
                       {"expiresIn": expires, "paths": list(objs)}) or []
        out = {}
        for r in res:
            if r.get("signedURL"):
                out[r.get("path")] = self.url + "/storage/v1" + r["signedURL"]
        return out


class ChatLine(ButtonBehavior, Label):
    pass


class OnlinePlus:
    # ------------------------------------------------------------ start i blokada
    def online_ready(self):
        return bool(SUPABASE_URL and SUPABASE_KEY)

    def online_start(self, *_):
        self.online_lock_view = None
        self.online_me = None
        self.online_settings = {}
        if not self.online_ready():
            return
        self.supa = Supa(SUPABASE_URL, SUPABASE_KEY,
                         lambda: self.lib.get_setting("supa_sesja", ""),
                         lambda v: self.lib.set_setting("supa_sesja", v))
        saved = self.lib.get_setting("blokada", "")
        if saved:
            self.online_lock(saved)
        if not self.supa.logged_in():
            self.online_login()
        else:
            self.online_check()
        Clock.schedule_interval(self.online_check, 60)

    def online_check(self, *_):
        if not self.online_ready() or not self.supa.logged_in():
            return
        supa = self.supa

        def work():
            me = supa.select("profiles", f"id=eq.{supa.uid}&select=*")
            st = supa.select("app_settings", "id=eq.1&select=*")
            try:
                supa.rpc("touch")
            except Exception:
                pass
            return (me[0] if me else None), (st[0] if st else {})

        def done(res):
            if isinstance(res, Exception):
                if isinstance(res, SupaError) and res.code in (400, 401, 403):
                    self.supa.clear()
                    self.online_login("Sesja wygasła - zaloguj się ponownie")
                return                          # brak sieci - zostaje ostatni znany stan
            me, st = res
            self.online_me, self.online_settings = me, st
            if me is None:
                self.online_lock("Konto nie istnieje albo zostało usunięte.", relogin=True)
            elif me["status"] == "banned" and not ban_expired(me):
                msg = "Zostałeś zablokowany przez administratora."
                if me.get("ban_reason"):
                    msg += f"\nPowód: {me['ban_reason']}"
                if me.get("ban_until"):
                    msg += f"\nDo: {local_time(me['ban_until'])}"
                self.lib.set_setting("blokada", msg)      # zostaje po wylogowaniu
                self.online_lock(msg, relogin=True)
            elif st.get("maintenance") and me.get("role") != "admin":
                self.online_lock(st.get("maintenance_msg") or "Przerwa techniczna.")
            elif me["status"] == "pending":
                if self.lib.get_setting("blokada", ""):
                    self.online_lock("To urządzenie było zablokowane. Nowe konto musi "
                                     "zatwierdzić administrator.", relogin=True)
                else:
                    self.online_unlock()
                    self.set_status("Konto czeka na akceptację administratora")
            else:
                self.lib.set_setting("blokada", "")
                self.online_unlock()
        self.run_bg(work, done)

    def online_lock(self, msg, relogin=False):
        try:
            if self.apk:
                self.player.cmd(cmd="quit")
            else:
                self.player.stop()
        except Exception:
            pass
        if self.online_lock_view is not None:
            self.online_lock_view.msg.text = msg
            return
        mv = ModalView(auto_dismiss=False, size_hint=(1, 1), background_color=(0, 0, 0, 0.96))
        box = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(14))
        box.add_widget(Label(text="Leox Player", font_size="30sp", color=ACCENT, bold=True,
                             size_hint_y=None, height=dp(60)))
        lbl = Label(text=msg, color=TEXT, font_size="17sp", halign="center", valign="middle")
        lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        box.add_widget(lbl)
        b1 = RoundButton(text="Sprawdź ponownie", size_hint_y=None, height=dp(56),
                         bg=list(ACCENT_DIM))
        b1.bind(on_release=lambda *_: self.online_check())
        box.add_widget(b1)
        if relogin:
            b2 = RoundButton(text="Zaloguj na inne konto", size_hint_y=None, height=dp(56),
                             bg=list(CARD_HI))
            b2.bind(on_release=lambda *_: self.online_logout())
            box.add_widget(b2)
        mv.add_widget(box)
        mv.msg = lbl
        self.online_lock_view = mv
        mv.open()

    def online_unlock(self):
        if self.online_lock_view is not None:
            self.online_lock_view.dismiss()
            self.online_lock_view = None

    # ------------------------------------------------------------ logowanie
    def online_login(self, info=""):
        mv = getattr(self, "online_login_view", None)
        if mv is not None:
            return
        mv = ModalView(auto_dismiss=False, size_hint=(1, 1), background_color=(0, 0, 0, 0.97))
        self.online_login_view = mv
        box = BoxLayout(orientation="vertical", padding=dp(22), spacing=dp(10))
        box.add_widget(Label(text="Leox Player", font_size="30sp", color=ACCENT, bold=True,
                             size_hint_y=None, height=dp(56)))
        msg = Label(text=info or "Zaloguj się albo załóż konto.", color=MUTED, font_size="14sp",
                    size_hint_y=None, height=dp(52), halign="center", valign="middle")
        msg.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        box.add_widget(msg)
        user = RoundInput(hint_text="Nazwa (a-z, 0-9, _ ; 3-20 znaków)", multiline=False,
                          size_hint_y=None, height=dp(54))
        pw = RoundInput(hint_text="Hasło (min. 6 znaków)", multiline=False, password=True,
                        size_hint_y=None, height=dp(54))
        disp = RoundInput(hint_text="Wyświetlana nazwa (tylko przy rejestracji)", multiline=False,
                          size_hint_y=None, height=dp(54))
        for w in (user, pw, disp):
            box.add_widget(w)
        b_login = RoundButton(text="Zaloguj", size_hint_y=None, height=dp(56), bg=list(ACCENT_DIM))
        b_reg = RoundButton(text="Załóż konto", size_hint_y=None, height=dp(56), bg=list(CARD_HI))
        box.add_widget(b_login)
        box.add_widget(b_reg)
        box.add_widget(Widget())

        def go(register):
            u = user.text.strip().lower()
            p = pw.text
            if not re.fullmatch(r"[a-z0-9_]{3,20}", u):
                msg.text = "Nazwa: 3-20 znaków, tylko małe litery, cyfry i _"
                return
            if len(p) < 6:
                msg.text = "Hasło musi mieć co najmniej 6 znaków"
                return
            msg.text = "Łączenie..."
            b_login.disabled = b_reg.disabled = True

            def work():
                if register:
                    self.supa.signup(u, p, disp.text.strip()[:40])
                else:
                    self.supa.login(u, p)
                return True

            def done(res):
                b_login.disabled = b_reg.disabled = False
                if isinstance(res, Exception):
                    msg.text = pl_error(res)
                    return
                mv.dismiss()
                self.online_login_view = None
                if register:
                    self.set_status("Konto założone - czeka na akceptację administratora")
                self.online_check()
            self.run_bg(work, done)
        b_login.bind(on_release=lambda *_: go(False))
        b_reg.bind(on_release=lambda *_: go(True))
        mv.add_widget(box)
        mv.open()

    def online_logout(self):
        self.online_unlock()

        def work():
            self.supa.logout()
            return True
        self.run_bg(work, lambda res: self.online_login("Wylogowano."))

    # ------------------------------------------------------------ menu
    def is_admin(self):
        me = getattr(self, "online_me", None)
        return bool(me and me.get("role") == "admin" and me.get("status") == "active")

    def is_active_user(self):
        me = getattr(self, "online_me", None)
        return bool(me and (me.get("status") == "active" or ban_expired(me)))

    def show_online(self):
        if not self.online_ready():
            self.list_popup("Społeczność", [{
                "text": "Nie skonfigurowano serwera.\nWpisz SUPABASE_URL i SUPABASE_KEY w kodzie.",
                "tap": lambda b: None, "h": 90}])
            return
        if not self.supa.logged_in():
            self.online_login()
            return
        me = self.online_me or {}
        name = me.get("display_name") or me.get("username") or "?"
        st = {"pending": "czeka na akceptację", "active": "aktywne",
              "banned": "zablokowane"}.get(me.get("status"), "?")
        rows = [{"text": f"{name}  (@{me.get('username', '?')})\nKonto: {st}"
                         f"{'  -  ADMIN' if self.is_admin() else ''}",
                 "tap": lambda b: self.online_edit_profile(), "h": 80,
                 "avatar": me.get("avatar_path", "")}]
        if self.is_active_user():
            rows += [{"text": "Czat publiczny", "tap": lambda b: self.online_chat()},
                     {"text": "Wspólna muzyka", "tap": lambda b: self.online_music()},
                     {"text": "Kto jest online", "tap": lambda b: self.online_who()},
                     {"text": "Użytkownicy", "tap": lambda b: self.online_users("active")}]
        rows += [{"text": "Mój profil (nazwa, opis)", "tap": lambda b: self.online_edit_profile()},
                 {"text": "Ustaw zdjęcie profilowe", "tap": lambda b: self.online_set_avatar()}]
        if me.get("avatar_path"):
            rows.append({"text": "Usuń zdjęcie profilowe",
                         "tap": lambda b: self.online_remove_avatar(me)})
        rows.append({"text": "Zmień hasło", "tap": lambda b: self.online_password()})
        if self.is_admin():
            rows.append({"text": "PANEL ADMINA", "tap": lambda b: self.online_admin(),
                         "bg": list(ACCENT_DIM)})
        rows.append({"text": "Wyloguj", "tap": lambda b: self.online_logout()})
        self.list_popup("Społeczność", rows)
        self.online_check()

    # ------------------------------------------------------------ profil
    def online_edit_profile(self):
        me = self.online_me or {}

        def save(v, pop):
            pop.dismiss()
            vals = {"display_name": v["display"][:40], "bio": v["bio"][:300]}
            self.run_bg(lambda: self.supa.update("profiles", f"id=eq.{self.supa.uid}", vals),
                        lambda res: self.set_status(pl_error(res) if isinstance(res, Exception)
                                                    else "Profil zapisany") or self.online_check())
        self.form_popup("Mój profil", [("display", "Wyświetlana nazwa", me.get("display_name", "")),
                                       ("bio", "O mnie", me.get("bio", ""))],
                        [("Zapisz", save), ("Anuluj", lambda v, pop: pop.dismiss())],
                        info=f"Konto: @{me.get('username', '?')}")

    def online_password(self):
        def save(v, pop):
            if len(v["pw"]) < 6 or v["pw"] != v["pw2"]:
                self.set_status("Hasła różne albo krótsze niż 6 znaków")
                return
            pop.dismiss()
            self.run_bg(lambda: self.supa.change_password(v["pw"]),
                        lambda res: self.set_status(pl_error(res) if isinstance(res, Exception)
                                                    else "Hasło zmienione"))
        self.form_popup("Zmień hasło", [("pw", "Nowe hasło", ""), ("pw2", "Powtórz hasło", "")],
                        [("Zapisz", save), ("Anuluj", lambda v, pop: pop.dismiss())])

    def online_profile_popup(self, p):
        joined = (p.get("created_at") or "")[:10]
        tags = []
        if p.get("role") == "admin":
            tags.append("admin")
        if p.get("muted"):
            tags.append("wyciszony")
        if p.get("status") != "active":
            tags.append({"pending": "oczekuje", "banned": "zablokowany"}.get(p.get("status"), ""))
        if is_online(p):
            tags.append("online")
        rows = [{"text": f"{p.get('display_name') or p.get('username')}  (@{p.get('username')})"
                         f"{'  [' + ', '.join(tags) + ']' if tags else ''}\nOd: {joined}",
                 "tap": lambda b: self.online_big_avatar(p), "h": 110,
                 "avatar": p.get("avatar_path", "")}]
        if p.get("status") == "banned" and (p.get("ban_reason") or p.get("ban_until")):
            rows.append({"text": f"Ban: {p.get('ban_reason') or '-'}\n"
                                 f"Do: {local_time(p['ban_until']) if p.get('ban_until') else 'na zawsze'}",
                         "tap": lambda b: None, "h": 80})
        if p.get("bio"):
            rows.append({"text": p["bio"], "tap": lambda b: None, "h": 100})
        if self.is_admin() and p.get("id") != self.supa.uid:
            rows += self.online_admin_actions(p)
        self.list_popup("Profil", rows)

    # ------------------------------------------------------------ czat
    def online_chat(self):
        supa = self.supa
        st = {"last": 0, "open": True, "busy": False, "ev": None, "profiles": {}}
        box = BoxLayout(orientation="vertical", spacing=dp(6))
        ann = Label(text="", color=ACCENT, font_size="14sp", size_hint_y=None, height=0,
                    halign="left", valign="middle", markup=True)
        ann.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        box.add_widget(ann)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4), padding=(dp(2), dp(2)))
        grid.bind(minimum_height=grid.setter("height"))
        sv = ScrollView(bar_color=ACCENT_DIM)
        sv.add_widget(grid)
        box.add_widget(sv)
        bar = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(4))
        ti = RoundInput(hint_text="Napisz wiadomość... (@nazwa = wzmianka)", multiline=False)
        send = RoundButton(text="Wyślij", size_hint_x=None, width=dp(90), bg=list(ACCENT_DIM))
        close = RoundButton(text="X", size_hint_x=None, width=dp(56), bg=list(CARD_HI))
        bar.add_widget(ti)
        bar.add_widget(send)
        bar.add_widget(close)
        box.add_widget(bar)
        pop = RoundPopup(title="Czat publiczny", content=box, size_hint=(1, 1))

        def add_line(m):
            p = m.get("profiles") or {}
            st["profiles"][m["user_id"]] = dict(p, id=m["user_id"])
            name = escape_markup(p.get("display_name") or p.get("username") or "?")
            when = (m.get("created_at") or "")[11:16]
            badge = " [color=#e08f52](admin)[/color]" if p.get("role") == "admin" else ""
            text = "[i]wiadomość usunięta[/i]" if m.get("deleted") else escape_markup(m["content"])
            me_name = "@" + ((self.online_me or {}).get("username") or "~")
            if not m.get("deleted") and me_name.lower() in m["content"].lower():
                text = f"[color=#e08f52][b]{text}[/b][/color]"       # ktoś Cię wspomniał
            row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
            av = TapImage(size_hint=(None, None), size=(dp(40), dp(40)), fit_mode="contain",
                          pos_hint={"top": 1})
            self.online_avatar(p.get("avatar_path", ""), av)
            av.bind(on_release=lambda *_: self.online_open_profile(m["user_id"]))
            line = ChatLine(text=f"[b]{name}[/b]{badge}  [size=11sp]{when}[/size]\n{text}",
                            markup=True, color=TEXT if not m.get("deleted") else MUTED,
                            font_size="15sp", halign="left", valign="top", size_hint_y=None)
            line.bind(width=lambda w, v: setattr(w, "text_size", (v - dp(8), None)),
                      texture_size=lambda w, v: (setattr(w, "height", v[1] + dp(8)),
                                                 setattr(row, "height", max(dp(48), v[1] + dp(8)))))
            line.bind(on_release=lambda *_: self.online_msg_menu(m, st["profiles"][m["user_id"]],
                                                                 lambda: refresh(True)))
            row.add_widget(av)
            row.add_widget(line)
            grid.add_widget(row)

        def refresh(full=False):
            if st["busy"] or not st["open"]:
                return
            st["busy"] = True
            if full:
                st["last"] = 0
            last = st["last"]

            def work():
                sel = "select=id,content,created_at,deleted,user_id," \
                      "profiles(username,display_name,role,avatar_path)"
                if last:
                    msgs = supa.select("messages", f"{sel}&id=gt.{last}&order=id.asc&limit=100")
                else:
                    msgs = list(reversed(supa.select("messages", f"{sel}&order=id.desc&limit=60")))
                sets = supa.select("app_settings", "id=eq.1&select=announcement")
                return msgs, (sets[0] if sets else {})

            def done(res):
                st["busy"] = False
                if isinstance(res, Exception):
                    pop.title = f"Czat publiczny - {pl_error(res)}"[:60]
                    return
                pop.title = "Czat publiczny"
                msgs, sets = res
                if not last:
                    grid.clear_widgets()
                at_bottom = sv.scroll_y < 0.05 or not last
                for m in msgs:
                    add_line(m)
                    st["last"] = max(st["last"], m["id"])
                a = (sets.get("announcement") or "").strip()
                ann.text = f"[b]Ogłoszenie:[/b] {escape_markup(a)}" if a else ""
                ann.height = dp(48) if a else 0
                if msgs and at_bottom:
                    Clock.schedule_once(lambda dt: setattr(sv, "scroll_y", 0), 0.05)
            self.run_bg(work, done)

        def do_send(*_):
            txt = ti.text.strip()
            if not txt:
                return
            if (self.online_me or {}).get("muted"):
                self.set_status("Jesteś wyciszony na czacie")
                return
            ti.text = ""
            send.disabled = True

            def done(res):
                send.disabled = False
                if isinstance(res, Exception):
                    ti.text = txt
                    pop.title = pl_error(res)[:60]
                    return
                refresh()
            self.run_bg(lambda: supa.insert("messages", {"user_id": supa.uid, "content": txt[:500]}),
                        done)

        def closed(*_):
            st["open"] = False
            if st["ev"]:
                st["ev"].cancel()
        send.bind(on_release=do_send)
        ti.bind(on_text_validate=do_send)
        close.bind(on_release=lambda *_: pop.dismiss())
        pop.bind(on_dismiss=closed)
        st["ev"] = Clock.schedule_interval(lambda dt: refresh(), 3)
        pop.open()
        refresh(True)

    def online_msg_menu(self, m, p, after):
        rows = [{"text": f"Profil: {p.get('display_name') or p.get('username')}",
                 "tap": lambda b: self.online_open_profile(m["user_id"])}]
        if self.is_admin():
            if not m.get("deleted"):
                rows.append({"text": "Usuń wiadomość", "tap": lambda b: self.online_do(
                    lambda: self.supa.update("messages", f"id=eq.{m['id']}", {"deleted": True}),
                    "Wiadomość usunięta", after)})
            else:
                rows.append({"text": "Przywróć wiadomość", "tap": lambda b: self.online_do(
                    lambda: self.supa.update("messages", f"id=eq.{m['id']}", {"deleted": False}),
                    "Przywrócono", after)})
        self.list_popup("Wiadomość", rows)

    def online_open_profile(self, uid):
        self.run_bg(lambda: self.supa.select("profiles", f"id=eq.{uid}&select=*"),
                    lambda res: self.set_status(pl_error(res)) if isinstance(res, Exception)
                    else (res and self.online_profile_popup(res[0])))

    def online_do(self, work, ok_msg, after=None):
        """Akcja na serwerze w tle + komunikat."""
        def done(res):
            if isinstance(res, Exception):
                self.set_status(pl_error(res))
                return
            self.set_status(ok_msg)
            if after:
                after()
        self.run_bg(work, done)

    # ------------------------------------------------------------ wspólna muzyka
    def online_music(self):
        supa = self.supa
        admin = self.is_admin()
        cache = {}

        def fetch(q):
            flt = "select=*&order=created_at.desc&limit=200"
            if q:
                qq = urllib.parse.quote(f"*{q}*")
                flt += f"&or=(title.ilike.{qq},artist.ilike.{qq})"
            rows = supa.select("tracks", flt)
            cache["rows"] = rows
            out = []
            for i, t in enumerate(rows):
                r = {"text": f"{t['artist'] or '?'} - {t['title']}\n{fmt(t['duration'])}",
                     "tap": lambda b, i=i: self.online_play_shared(cache["rows"], i),
                     "sides": [("Pobierz", lambda b, t=t: self.online_download_shared(t))]}
                if admin:
                    r["sides"].append(("Usuń", lambda b, t=t: self.online_delete_track(t)))
                out.append(r)
            return out
        footer = [("Graj wszystko", lambda b: cache.get("rows") and
                   self.online_play_shared(cache["rows"], 0))]
        if admin:
            footer.append(("Z biblioteki", lambda b: self.online_pick_upload()))
            footer.append(("Z pliku", lambda b: self.online_upload_file()))
        self.live_search_popup("Wspólna muzyka", "Szukaj na serwerze", fetch, footer,
                               empty_msg="Brak utworów na serwerze")

    def online_play_shared(self, rows, i):
        if not rows:
            return
        self.set_status("Wczytywanie wspólnej muzyki...")

        def work():
            return self.supa.signed_urls([t["object_path"] for t in rows])

        def done(res):
            if isinstance(res, Exception):
                self.set_status(pl_error(res))
                return
            q = [(res[t["object_path"]], t["title"], t["artist"] or "", "Wspólna muzyka",
                  float(t["duration"] or 0)) for t in rows if t["object_path"] in res]
            if not q:
                self.set_status("Nie udało się pobrać linków do utworów")
                return
            self.queue, self.qi = q, min(i, len(q) - 1)
            self.play_current()
        self.run_bg(work, done)

    def online_download_shared(self, t):
        def work():
            return self.supa.signed_urls([t["object_path"]])

        def done(res):
            if isinstance(res, Exception) or not res:
                self.set_status(pl_error(res) if isinstance(res, Exception) else "Brak pliku")
                return
            ext = Path(t["object_path"]).suffix or ".mp3"
            name = safe_name(f"{t['artist'] or '?'} - {t['title']}") + ext
            self.download(res[t["object_path"]], kind="file", title=t["title"],
                          dest=str(self.dl_dir / name))
            self.set_status(f"Pobieranie: {t['title']}")
        self.run_bg(work, done)

    def online_delete_track(self, t):
        def go(b):
            def work():
                self.supa.delete("tracks", f"id=eq.{t['id']}")
                try:
                    self.supa.remove_object(t["object_path"])
                except Exception:
                    pass
                return True
            self.online_do(work, f"Usunięto z serwera: {t['title']}")
        self.list_popup(f"Usunąć z serwera?  {t['title']}",
                        [{"text": "Tak, usuń dla wszystkich", "tap": go}])

    def online_pick_upload(self):
        def fetch(q):
            ql = q.casefold()
            rows = [t for t in self.lib.tracks()
                    if not ql or ql in f"{t[1]} {t[2]}".casefold()][:200]
            return [{"text": f"{t[2] or '?'} - {t[1]}\n{fmt(t[4])}",
                     "tap": lambda b, t=t: self.online_upload(t)} for t in rows]
        self.live_search_popup("Wyślij na serwer", "Szukaj w swojej bibliotece", fetch,
                               empty_msg="Brak plików w bibliotece")

    def online_upload(self, t, cleanup=False):
        path = Path(t[0])
        ext = path.suffix.lower()
        mime = AUDIO_MIME.get(ext)
        if not mime:
            self.set_status("Ten format nie jest obsługiwany")
            return
        try:
            size = path.stat().st_size
        except OSError as e:
            self.set_status(f"Brak pliku: {e}")
            return
        if size > 50 * 1024 * 1024:
            self.set_status("Plik większy niż 50 MB")
            return
        self.set_status(f"Wysyłanie: {t[1]} ({size // 1048576 or 1} MB)...")

        def work():
            obj = uuid.uuid4().hex + ext
            n = self.supa.upload(obj, path, mime)
            try:
                self.supa.insert("tracks", {"title": (t[1] or path.stem)[:200],
                                            "artist": (t[2] or "")[:200],
                                            "duration": float(t[4] or 0), "object_path": obj,
                                            "size_bytes": n, "uploaded_by": self.supa.uid})
            except Exception:
                self.supa.remove_object(obj)
                raise
            finally:
                if cleanup:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            return True
        self.online_do(work, f"Wysłano na serwer: {t[1]}")

    # ------------------------------------------------------------ panel admina
    def online_admin(self):
        s = self.online_settings or {}
        maint = bool(s.get("maintenance"))
        rows = [
            {"text": "Statystyki", "tap": lambda b: self.online_stats()},
            {"text": "Kto jest online", "tap": lambda b: self.online_who()},
            {"text": "Dziennik admina (kto co zmienił)", "tap": lambda b: self.online_admin_log()},
            {"text": "Oczekujące konta (akceptacja)", "tap": lambda b: self.online_users("pending")},
            {"text": "Aktywni użytkownicy", "tap": lambda b: self.online_users("active")},
            {"text": "Zablokowani (unban)", "tap": lambda b: self.online_users("banned")},
            {"text": f"Wyłącz aplikację wszystkim (przerwa): {'WŁĄCZONA' if maint else 'wył.'}",
             "tap": lambda b: self.online_toggle_maintenance(not maint)},
            {"text": "Ogłoszenie na czacie", "tap": lambda b: self.online_announce()},
            {"text": "Wspólna muzyka (dodaj / usuń)", "tap": lambda b: self.online_music()},
            {"text": "Wyczyść cały czat", "tap": lambda b: self.online_clear_chat()},
        ]
        self.list_popup("Panel admina", rows)

    def online_stats(self):
        def done(res):
            if isinstance(res, Exception):
                self.set_status(pl_error(res))
                return
            d = res or {}
            self.list_popup("Statystyki", [{"text": t, "tap": lambda b: None} for t in (
                f"Konta: {d.get('users', 0)}",
                f"Aktywne: {d.get('active', 0)}   Oczekujące: {d.get('pending', 0)}",
                f"Zablokowane: {d.get('banned', 0)}",
                f"Online (5 min): {d.get('online', 0)}",
                f"Wiadomości na czacie: {d.get('messages', 0)}",
                f"Utwory na serwerze: {d.get('tracks', 0)}  ({d.get('mb', 0)} MB z 1024 MB)")])
        self.run_bg(lambda: self.supa.rpc("admin_stats"), done)

    def online_users(self, status):
        titles = {"pending": "Oczekujące konta", "active": "Użytkownicy", "banned": "Zablokowani"}

        def done(res):
            if isinstance(res, Exception):
                self.set_status(pl_error(res))
                return
            rows = []
            for p in res:
                tags = []
                if p.get("role") == "admin":
                    tags.append("admin")
                if p.get("muted"):
                    tags.append("wyciszony")
                if p.get("last_seen") and status == "active" and not is_online(p):
                    tags.append("widziany " + local_time(p["last_seen"]))
                if status == "banned":
                    extra = (f"\nPowód: {p.get('ban_reason') or '-'}  do: "
                             f"{local_time(p['ban_until']) if p.get('ban_until') else 'na zawsze'}")
                else:
                    extra = "\n" + ", ".join(tags) if tags else ""
                dot = "  [online]" if is_online(p) else ""
                r = {"text": f"{p.get('display_name') or p['username']}  (@{p['username']}){dot}{extra}",
                     "tap": lambda b, p=p: self.online_profile_popup(p), "h": 80,
                     "avatar": p.get("avatar_path", "")}
                if self.is_admin() and status == "pending":
                    r["sides"] = [("OK", lambda b, p=p: self.online_set(
                        p, {"status": "active"}, "Zatwierdzono"))]
                if self.is_admin() and status == "banned":
                    r["sides"] = [("Unban", lambda b, p=p: self.online_set(
                        p, {"status": "active", "ban_reason": "", "ban_until": None}, "Odblokowano"))]
                rows.append(r)
            if not rows:
                rows = [{"text": "Brak", "tap": lambda b: None}]
            self.list_popup(titles[status], rows)
        self.run_bg(lambda: self.supa.select(
            "profiles", f"status=eq.{status}&select=*&order=created_at.desc&limit=300"), done)

    def online_admin_actions(self, p):
        rows = []
        st = p.get("status")
        if st == "pending":
            rows.append({"text": "Zatwierdź konto", "tap": lambda b: self.online_set(
                p, {"status": "active"}, "Zatwierdzono")})
        if st != "banned":
            rows.append({"text": "Zbanuj (blokada aplikacji)", "tap": lambda b: self.online_ban(p)})
        else:
            rows.append({"text": "Odbanuj", "tap": lambda b: self.online_set(
                p, {"status": "active", "ban_reason": "", "ban_until": None}, "Odblokowano")})
        rows.append({"text": "Edytuj profil (nazwa, opis)", "tap": lambda b: self.online_admin_edit(p)})
        if p.get("avatar_path"):
            rows.append({"text": "Usuń zdjęcie profilowe", "tap": lambda b: self.online_remove_avatar(p)})
        rows.append({"text": "Odcisz na czacie" if p.get("muted") else "Wycisz na czacie",
                     "tap": lambda b: self.online_set(p, {"muted": not p.get("muted")},
                                                      "Zmieniono wyciszenie")})
        if p.get("role") == "admin":
            rows.append({"text": "Odbierz uprawnienia admina", "tap": lambda b: self.online_set(
                p, {"role": "user"}, "Odebrano admina")})
        else:
            rows.append({"text": "Nadaj uprawnienia admina", "tap": lambda b: self.online_set(
                p, {"role": "admin"}, "Nadano admina")})
        rows.append({"text": "Ustaw nowe hasło (zapomniał)", "tap": lambda b: self.ask(
            f"Nowe hasło dla @{p['username']} (min. 6 znaków)", lambda pw: self.online_do(
                lambda: self.supa.rpc("admin_set_password", {"target": p["id"], "new_password": pw}),
                f"Nowe hasło @{p['username']}: {pw}"))})
        rows.append({"text": "Usuń wszystkie jego wiadomości", "tap": lambda b: self.online_do(
            lambda: self.supa.update("messages", f"user_id=eq.{p['id']}&deleted=eq.false",
                                     {"deleted": True}), "Wiadomości usunięte")})
        rows.append({"text": "Usuń konto na zawsze", "tap": lambda b: self.list_popup(
            f"Usunąć konto @{p['username']}?", [{"text": "Tak, usuń konto i jego wiadomości",
                                                 "tap": lambda b2: self.online_do(
                lambda: self.supa.rpc("admin_delete_user", {"target": p["id"]}),
                f"Usunięto konto @{p['username']}")}])})
        return rows

    def online_ban(self, p):
        opts = [("1 godzina", 1), ("1 dzień", 24), ("7 dni", 24 * 7), ("30 dni", 24 * 30),
                ("Na zawsze", 0)]

        def pick(hours):
            until = None
            if hours:
                until = (datetime.datetime.now(datetime.timezone.utc)
                         + datetime.timedelta(hours=hours)).isoformat()
            self.ask(f"Powód bana dla @{p['username']}", lambda r: self.online_set(
                p, {"status": "banned", "ban_reason": r[:200], "ban_until": until},
                "Zablokowano" + (f" do {local_time(until)}" if until else " na zawsze")))
        self.list_popup(f"Ban: @{p['username']} - na jak długo?",
                        [{"text": t, "tap": lambda b, h=h: pick(h)} for t, h in opts])

    def online_admin_edit(self, p):
        def save(v, pop):
            pop.dismiss()
            self.online_set(p, {"display_name": v["display"][:40], "bio": v["bio"][:300]},
                            "Profil zmieniony")
        self.form_popup(f"Edytuj @{p['username']}",
                        [("display", "Wyświetlana nazwa", p.get("display_name", "")),
                         ("bio", "Opis", p.get("bio", ""))],
                        [("Zapisz", save), ("Anuluj", lambda v, pop: pop.dismiss())],
                        info="Nazwy konta (loginu) nie da się zmienić.")

    def online_set(self, p, values, ok_msg):
        self.online_do(lambda: self.supa.update("profiles", f"id=eq.{p['id']}", values), ok_msg)

    def online_toggle_maintenance(self, on):
        def apply(msg):
            vals = {"maintenance": on, "updated_at": datetime.datetime.utcnow().isoformat() + "Z"}
            if msg:
                vals["maintenance_msg"] = msg[:300]
            self.online_do(lambda: self.supa.update("app_settings", "id=eq.1", vals),
                           "Aplikacja wyłączona dla wszystkich poza adminami" if on
                           else "Aplikacja znowu działa dla wszystkich", self.online_check)
        if on:
            self.form_popup("Przerwa techniczna",
                            [("msg", "Komunikat dla użytkowników",
                              (self.online_settings or {}).get("maintenance_msg", ""))],
                            [("Wyłącz aplikację", lambda v, pop: (pop.dismiss(), apply(v["msg"]))),
                             ("Anuluj", lambda v, pop: pop.dismiss())],
                            info="Wszyscy poza adminami zobaczą ten komunikat zamiast aplikacji.")
        else:
            apply("")

    def online_announce(self):
        cur = (self.online_settings or {}).get("announcement", "")

        def save(v, pop):
            pop.dismiss()
            self.online_do(lambda: self.supa.update("app_settings", "id=eq.1",
                                                    {"announcement": v["a"][:300]}),
                           "Ogłoszenie zapisane" if v["a"] else "Ogłoszenie usunięte",
                           self.online_check)
        self.form_popup("Ogłoszenie", [("a", "Treść (puste = brak)", cur)],
                        [("Zapisz", save), ("Anuluj", lambda v, pop: pop.dismiss())])

    def online_clear_chat(self):
        self.list_popup("Wyczyścić cały czat?", [{"text": "Tak, ukryj wszystkie wiadomości",
                                                  "tap": lambda b: self.online_do(
            lambda: self.supa.update("messages", "deleted=eq.false", {"deleted": True}),
            "Czat wyczyszczony")}])


    # ------------------------------------------------------------ zdjęcia profilowe
    def online_avatar(self, path, widget):
        """Zdjęcie profilowe z serwera (pamięć podręczna wg ścieżki - nowa ścieżka = nowe zdjęcie)."""
        if not path or not self.online_ready():
            return
        folder = Path(self.user_data_dir) / "awatary"
        f = folder / (re.sub(r"[^A-Za-z0-9_.-]", "_", path))
        if f.exists():
            widget.source = str(f)
            return
        pend = self.__dict__.setdefault("_av_pending", {})
        if path in pend:
            pend[path].append(widget)
            return
        pend[path] = [widget]

        def work():
            url = self.supa.signed_urls([path], 3600, bucket="avatars").get(path)
            if not url:
                raise RuntimeError("brak zdjęcia")
            folder.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(".part")
            tmp.write_bytes(http_get(url))
            tmp.replace(f)
            return str(f)

        def done(res):
            for w in pend.pop(path, []):
                if isinstance(res, str):
                    w.source = res
        self.run_bg(work, done)

    def online_big_avatar(self, p):
        if not p.get("avatar_path"):
            return
        im = TapImage(fit_mode="contain")
        pop = RoundPopup(title=p.get("display_name") or p.get("username") or "", content=im,
                         size_hint=(0.92, 0.6))
        im.bind(on_release=lambda *_: pop.dismiss())
        self.online_avatar(p["avatar_path"], im)
        pop.open()

    def pick_file(self, mime, cb):
        """Systemowe okno wyboru pliku (galeria / menedżer plików). cb(ścieżka, nazwa) albo cb(None, błąd)."""
        try:
            from android import activity
            from jnius import autoclass, cast
        except ImportError:
            self.ask("Ścieżka do pliku", lambda t: cb(t, Path(t).name) if Path(t).exists()
                     else cb(None, "Nie ma takiego pliku"))
            return
        Intent = autoclass("android.content.Intent")
        String = autoclass("java.lang.String")
        Files = autoclass("pl.leox.media.LeoxFiles")
        act = autoclass("org.kivy.android.PythonActivity").mActivity
        req = 4711

        def on_result(request, result, data):
            if request != req:
                return
            activity.unbind(on_activity_result=on_result)
            if result != -1 or data is None or data.getData() is None:
                Clock.schedule_once(lambda dt: cb(None, "Anulowano"))
                return
            uri = data.getData()

            def copy():
                try:
                    name = Files.displayName(act, uri) or "plik"
                    dest = Path(self.user_data_dir) / "wybrane"
                    dest.mkdir(parents=True, exist_ok=True)
                    out = dest / (uuid.uuid4().hex + Path(name).suffix.lower())
                    n = Files.copyUri(act, uri, str(out))
                    if n < 0:
                        Clock.schedule_once(lambda dt: cb(None, "Nie udało się odczytać pliku"))
                    else:
                        Clock.schedule_once(lambda dt: cb(str(out), name))
                finally:
                    try:
                        from jnius import detach
                        detach()
                    except Exception:
                        pass
            Clock.schedule_once(lambda dt: self.set_status("Wczytywanie pliku..."))
            threading.Thread(target=copy, daemon=True).start()
        activity.bind(on_activity_result=on_result)
        it = Intent(Intent.ACTION_GET_CONTENT)
        it.setType(mime)
        it.addCategory(Intent.CATEGORY_OPENABLE)
        act.startActivityForResult(
            Intent.createChooser(it, cast("java.lang.CharSequence", String("Wybierz plik"))), req)

    def online_set_avatar(self):
        def picked(path, name):
            if not path:
                self.set_status(name)
                return
            self.set_status("Wysyłanie zdjęcia...")
            old = (self.online_me or {}).get("avatar_path", "")

            def work():
                jpg = str(Path(path).with_suffix(".avatar.jpg"))
                try:
                    from jnius import autoclass
                    ok = autoclass("pl.leox.media.LeoxFiles").squareJpeg(path, jpg, 512)
                except Exception:
                    ok = False
                src, mime = (jpg, "image/jpeg") if ok else (path, {
                    ".png": "image/png", ".webp": "image/webp"}.get(Path(path).suffix.lower(), "image/jpeg"))
                if Path(src).stat().st_size > 2 * 1024 * 1024:
                    raise RuntimeError("Zdjęcie większe niż 2 MB")
                obj = f"{self.supa.uid}/{uuid.uuid4().hex}{Path(src).suffix or '.jpg'}"
                self.supa.upload(obj, src, mime, bucket="avatars")
                self.supa.update("profiles", f"id=eq.{self.supa.uid}", {"avatar_path": obj})
                if old:
                    try:
                        self.supa.remove_object(old, bucket="avatars")
                    except Exception:
                        pass
                for x in (path, jpg):
                    try:
                        os.remove(x)
                    except OSError:
                        pass
                return True
            self.online_do(work, "Zdjęcie profilowe ustawione", self.online_check)
        self.pick_file("image/*", picked)

    def online_remove_avatar(self, p):
        path = p.get("avatar_path", "")
        if not path:
            return

        def work():
            self.supa.update("profiles", f"id=eq.{p['id']}", {"avatar_path": ""})
            try:
                self.supa.remove_object(path, bucket="avatars")
            except Exception:
                pass
            return True
        self.online_do(work, "Zdjęcie usunięte", self.online_check)

    # ------------------------------------------------------------ online, dziennik, pliki
    def online_who(self):
        since = (datetime.datetime.now(datetime.timezone.utc)
                 - datetime.timedelta(minutes=5)).isoformat()

        def done(res):
            if isinstance(res, Exception):
                self.set_status(pl_error(res))
                return
            rows = [{"text": f"{p.get('display_name') or p['username']}  (@{p['username']})",
                     "tap": lambda b, p=p: self.online_profile_popup(p),
                     "avatar": p.get("avatar_path", "")} for p in res]
            self.list_popup(f"Online: {len(rows)}", rows or [{"text": "Nikogo", "tap": lambda b: None}])
        self.run_bg(lambda: self.supa.select(
            "profiles", "select=*&last_seen=gte." + urllib.parse.quote(since)
            + "&order=last_seen.desc&limit=200"), done)

    def online_admin_log(self):
        def done(res):
            if isinstance(res, Exception):
                self.set_status(pl_error(res))
                return
            rows = []
            for e in res:
                who = ((e.get("admin") or {}).get("username")) or "?"
                rows.append({"text": f"{local_time(e['created_at'])}  @{who} -> @{e.get('target_name') or '?'}\n"
                                     f"{e['action']}: {e.get('details') or ''}",
                             "tap": lambda b: None, "h": 90})
            self.list_popup("Dziennik admina", rows or [{"text": "Pusto", "tap": lambda b: None}])
        self.run_bg(lambda: self.supa.select(
            "admin_log", "select=*,admin:profiles!admin_log_admin_id_fkey(username)"
            "&order=created_at.desc&limit=200"), done)

    def online_upload_file(self):
        def picked(path, name):
            if not path:
                self.set_status(name)
                return
            title, artist = split_name(Path(name).stem)
            dur = 0.0
            if mutagen:
                try:
                    f = mutagen.File(path, easy=True)
                    if f is not None:
                        title = (f.get("title") or [title])[0]
                        artist = (f.get("artist") or [artist])[0]
                        dur = float(getattr(f.info, "length", 0) or 0)
                except Exception:
                    pass
            ext = Path(name).suffix.lower() or ".mp3"
            tmp = Path(path)
            if tmp.suffix.lower() != ext:
                tmp = tmp.rename(tmp.with_suffix(ext))
            self.online_upload((str(tmp), title, artist, "", dur), cleanup=True)
        self.pick_file("audio/*", picked)


def ban_expired(p):
    if not p or p.get("status") != "banned" or not p.get("ban_until"):
        return False
    try:
        until = datetime.datetime.fromisoformat(str(p["ban_until"]).replace("Z", "+00:00"))
        return until < datetime.datetime.now(datetime.timezone.utc)
    except ValueError:
        return False


def is_online(p):
    try:
        t = datetime.datetime.fromisoformat(str(p.get("last_seen") or "").replace("Z", "+00:00"))
        return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() < 300
    except ValueError:
        return False


def local_time(iso):
    try:
        t = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return t.astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return str(iso)[:16].replace("T", " ")


for _name, _fn in list(vars(OnlinePlus).items()):
    if not _name.startswith("__"):
        setattr(MuzykaApp, _name, _fn)



if __name__ == "__main__":
    MuzykaApp().run()
