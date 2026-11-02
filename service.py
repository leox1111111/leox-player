"""Leox Player - usługa odtwarzania w tle (tylko APK).

Gra kolejkę także po zamknięciu aplikacji, pokazuje panel w powiadomieniu
(poprzedni / pauza / następny / zamknij), obsługuje przyciski słuchawek
i Bluetooth oraz pauzuje przy rozmowie telefonicznej.
Sterowanie: polecenia JSON przez UDP od main.py (port 17401),
stan wraca do aplikacji na port 17402.
"""
import hashlib
import json
import os
import queue
import socket
import threading
import time
import urllib.request
from pathlib import Path

try:                                    # certyfikaty SSL w APK
    import certifi
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
except ImportError:
    pass

from jnius import autoclass

SVC_PORT, APP_PORT = 17401, 17402
YT_FORMAT = "bestaudio[ext=m4a]/bestaudio/best[ext=mp4]/best"

SVC = autoclass("org.kivy.android.PythonService").mService
Media = autoclass("pl.leox.media.LeoxMedia")
MediaPlayer = autoclass("android.media.MediaPlayer")
Uri = autoclass("android.net.Uri")
HashMap = autoclass("java.util.HashMap")
PowerManager = autoclass("android.os.PowerManager")
try:
    PlaybackParams = autoclass("android.media.PlaybackParams")
except Exception:
    PlaybackParams = None
try:
    Equalizer = autoclass("android.media.audiofx.Equalizer")
    BassBoost = autoclass("android.media.audiofx.BassBoost")
except Exception:
    Equalizer = BassBoost = None

CACHE = Path(SVC.getCacheDir().getAbsolutePath())


def log(*a):
    print("[leox-usluga]", *a)


class Quiet:
    def debug(self, msg):
        pass

    info = warning = error = debug


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


def is_stream(p):
    return bool(p) and (p.startswith("http") or p.startswith("radio:"))


def is_youtube(p):
    return bool(p) and p.startswith("http") and ("youtube.com" in p or "youtu.be" in p)


def fetch_art(url):
    """Pobiera okładkę do pamięci podręcznej; zwraca ścieżkę albo ''."""
    if not url or not url.startswith("http"):
        return ""
    d = CACHE / "okladki"
    try:
        d.mkdir(parents=True, exist_ok=True)
        f = d / (hashlib.md5(url.encode("utf-8")).hexdigest() + ".jpg")
        if not f.exists():
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            tmp = f.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.rename(f)
        return str(f)
    except Exception:
        return ""


class Usluga:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", SVC_PORT))
        self.sock.settimeout(0.05)
        self.out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.queue, self.queue_file, self.index = [], "", -1
        self.mp, self.mp_id, self.old = None, None, None
        self.fade_in, self.duck = 1.0, 1.0
        self.paused = self.active = self.loading = False
        self.vol, self.gain, self.speed = 1.0, 1.0, 1.0
        self.eq, self.bass, self.bands, self.fx = -1, 0, [], []
        self.repeat, self.xf, self.stop_after = "off", 0, False
        self.token, self.ready = 0, queue.Queue()
        self.art, self.focus_paused, self.xf_started = "", False, False
        self.last_status, self.last_notif, self.notif_key = 0.0, 0.0, None
        Media.init(SVC)

    # ------------------------------------------------------------ komunikacja
    def send(self, **m):
        try:
            self.out.sendto(json.dumps(m).encode("utf-8"), ("127.0.0.1", APP_PORT))
        except Exception:
            pass

    def handle(self, m):
        c = m.get("cmd")
        if c == "hello":
            self.send(event="state", queue_file=self.queue_file, active=self.active,
                      index=self.index, paused=self.paused)
        elif c in ("play", "queue"):
            if m.get("queue_file"):
                self.load_queue(m["queue_file"])
            self.apply_settings(m)
            idx = int(m.get("index", -1))
            if c == "play":
                self.play(idx, fade=float(m.get("fade") or 0), gain=float(m.get("gain") or 1.0))
            else:
                self.index = idx
        elif c == "stop":
            self.stop_mp()
            self.active = self.paused = self.loading = False
            self.token += 1
            Media.remove()
            self.notif_key = None
        elif c == "pause":
            self.pause()
        elif c == "resume":
            self.resume()
        elif c == "speed":
            self.speed = float(m.get("v") or 1.0)
            self.apply_speed()
            self.notif_key = None
        elif c == "fx":
            self.eq = int(m.get("eq", -1))
            self.bass = int(m.get("bass", 0))
            self.bands = list(m.get("bands") or [])
            self.apply_fx()
        elif c == "seek":
            self.seek(float(m.get("sec") or 0))
        elif c == "volume":
            self.vol = max(0.0, min(1.0, float(m.get("v", 1.0))))
            self.apply_vol()
        elif c == "set":
            self.apply_settings(m)
        elif c == "stop_after":
            self.stop_after = bool(m.get("on"))
        elif c == "quit":
            self.end("quit")

    def apply_settings(self, m):
        if m.get("repeat") in ("off", "all", "one"):
            self.repeat = m["repeat"]
        if m.get("xf") is not None:
            try:
                self.xf = int(m["xf"])
            except (TypeError, ValueError):
                pass

    def load_queue(self, path):
        try:
            q = json.loads(Path(path).read_text(encoding="utf-8"))
            self.queue = [list(x) for x in q]
            self.queue_file = path
        except Exception as e:
            log("kolejka:", e)

    # ------------------------------------------------------------ odtwarzanie
    def prepare(self, src, headers=None):
        mp = MediaPlayer()
        try:
            Media.watch(mp)
            try:
                mp.setWakeMode(SVC, PowerManager.PARTIAL_WAKE_LOCK)
            except Exception:
                pass
            if headers:
                h = HashMap()
                for k, v in headers.items():
                    h.put(str(k), str(v))
                mp.setDataSource(SVC, Uri.parse(src), h)
            else:
                mp.setDataSource(src)
            mp.prepare()
        except Exception:
            mp.release()
            raise
        return mp

    def yt_prepare(self, url):
        import yt_dlp
        opts = {"quiet": True, "logger": Quiet(), "no_warnings": True, "noplaylist": True,
                "format": YT_FORMAT}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if info.get("url"):
            try:
                return info, self.prepare(info["url"], info.get("http_headers"))
            except Exception:
                pass
        tmp = CACHE / "strumien"
        tmp.mkdir(parents=True, exist_ok=True)
        for f in sorted(tmp.iterdir(), key=lambda f: f.stat().st_mtime)[:-3]:
            try:
                f.unlink()
            except OSError:
                pass
        with yt_dlp.YoutubeDL(dict(opts, outtmpl=str(tmp / "%(id)s.%(ext)s"))) as ydl:
            info = ydl.extract_info(url, download=True)
        return info, self.prepare(info["requested_downloads"][0]["filepath"])

    def load_stream(self, tok, index, t):
        path = t[0]
        try:
            cover = str(t[3]) if len(t) > 3 and str(t[3]).startswith("http") else ""
            if path.startswith("radio:"):
                mp = self.prepare(path[len("radio:"):])
            elif is_youtube(path):
                info, mp = self.yt_prepare(path)
                if info.get("id"):
                    cover = f"https://i.ytimg.com/vi/{info['id']}/hqdefault.jpg"
            else:
                mp = self.prepare(path)
            self.ready.put((tok, index, mp, fetch_art(cover)))
        except Exception as e:
            self.ready.put((tok, index, e, ""))

    def play(self, index, fade=0.0, gain=1.0):
        if not (0 <= index < len(self.queue)):
            return
        self.token += 1
        tok = self.token
        self.index, self.gain, self.xf_started = index, gain, False
        self.active, self.paused, self.focus_paused = True, False, False
        t = self.queue[index]
        if is_stream(t[0]):
            self.stop_mp()
            self.loading, self.art = True, ""
            threading.Thread(target=self.load_stream, args=(tok, index, t), daemon=True).start()
        else:
            self.loading = False
            try:
                mp = self.prepare(t[0])
            except Exception as e:
                self.fail(f"Nie można otworzyć pliku: {e}")
                return
            self.attach(mp, fade, "")
            self.send(event="started", index=index)
        self.refresh_notif(force=True)

    def attach(self, mp, fade, art):
        if fade > 0 and self.mp is not None and not self.paused:
            self.kill_old()
            self.release_fx()
            self.old = (self.mp, time.time(), float(fade))
            self.fade_in = 0.0
        else:
            self.stop_mp()
            self.fade_in = 1.0
        self.mp, self.mp_id, self.art, self.paused = mp, Media.id(mp), art, False
        self.apply_vol()
        Media.requestFocus()
        mp.start()
        self.apply_speed()
        self.apply_fx()

    def fail(self, msg):
        self.stop_mp()
        self.active = self.loading = False
        Media.remove()
        self.notif_key = None
        self.send(event="error", msg=str(msg))

    def end(self, reason):
        self.token += 1
        self.stop_mp()
        self.active = self.paused = self.loading = False
        self.stop_after = False
        Media.remove()
        self.notif_key = None
        if reason:
            self.send(event="ended", reason=reason)
        else:
            self.send(event="ended")

    def release_fx(self):
        for fx in self.fx:
            try:
                fx.release()
            except Exception:
                pass
        self.fx = []

    def kill_old(self):
        if self.old:
            try:
                self.old[0].stop()
            except Exception:
                pass
            try:
                self.old[0].release()
            except Exception:
                pass
            self.old = None

    def stop_mp(self):
        self.kill_old()
        self.release_fx()
        if self.mp is not None:
            try:
                self.mp.stop()
            except Exception:
                pass
            try:
                self.mp.release()
            except Exception:
                pass
        self.mp, self.mp_id = None, None

    def pause(self):
        if self.mp is not None and not self.paused:
            try:
                self.mp.pause()
            except Exception:
                pass
            self.kill_old()
            self.paused = True
            self.refresh_notif(force=True)

    def resume(self):
        if self.mp is not None and self.paused:
            Media.requestFocus()
            try:
                self.mp.start()
            except Exception:
                pass
            self.paused, self.focus_paused = False, False
            self.apply_speed()
            self.refresh_notif(force=True)
        elif self.mp is None and not self.loading and 0 <= self.index < len(self.queue):
            self.play(self.index)

    def toggle(self):
        if self.mp is not None and not self.paused:
            self.pause()
        else:
            self.resume()

    def seek(self, sec):
        if self.mp is not None:
            try:
                self.mp.seekTo(int(sec * 1000))
            except Exception:
                pass
            self.refresh_notif(force=True)

    def position(self):
        try:
            return self.mp.getCurrentPosition() / 1000 if self.mp is not None else 0.0
        except Exception:
            return 0.0

    def duration(self):
        try:
            d = self.mp.getDuration() if self.mp is not None else 0
            return d / 1000 if d > 0 else 0.0
        except Exception:
            return 0.0

    def next_index(self, auto):
        n = len(self.queue)
        if auto and self.repeat == "one":
            return self.index
        if self.index + 1 < n:
            return self.index + 1
        if self.repeat == "all" and n:
            return 0
        return None

    def skip_next(self):
        nxt = self.next_index(auto=False)
        if nxt is not None:
            self.play(nxt)

    def skip_prev(self):
        if self.position() > 5:
            self.seek(0)
            return
        n = len(self.queue)
        if not n:
            return
        i = self.index - 1
        if i < 0:
            i = n - 1 if self.repeat == "all" else 0
        self.play(i)

    def track_ended(self):
        if self.stop_after:
            self.end("timer")
            return
        nxt = self.next_index(auto=True)
        if nxt is None:
            self.end(None)
        else:
            self.play(nxt)

    # ------------------------------------------------------------ dźwięk
    def apply_vol(self):
        real = self.vol * self.gain * self.fade_in * self.duck
        if self.mp is not None:
            try:
                self.mp.setVolume(real, real)
            except Exception:
                pass

    def fade_step(self):
        old, t0, dur = self.old
        k = (time.time() - t0) / dur
        if k >= 1:
            self.kill_old()
            self.fade_in = 1.0
            self.apply_vol()
            return
        try:
            v = (1 - k) * self.vol * self.duck
            old.setVolume(v, v)
        except Exception:
            pass
        self.fade_in = k
        self.apply_vol()

    def apply_speed(self):
        if self.mp is None or PlaybackParams is None:
            return
        try:
            self.mp.setPlaybackParams(PlaybackParams().setSpeed(float(self.speed)))
            if self.paused:
                self.mp.pause()
        except Exception:
            pass

    def apply_fx(self):
        self.release_fx()
        if self.mp is None or Equalizer is None:
            return
        try:
            sid = self.mp.getAudioSessionId()
            if self.eq >= 0:
                eq = Equalizer(0, sid)
                eq.usePreset(self.eq)
                eq.setEnabled(True)
                self.fx.append(eq)
            elif self.eq == -2 and self.bands:
                eq = Equalizer(0, sid)
                for i, lvl in enumerate(self.bands):
                    eq.setBandLevel(i, int(lvl))
                eq.setEnabled(True)
                self.fx.append(eq)
            if self.bass > 0:
                bb = BassBoost(0, sid)
                bb.setStrength(int(self.bass))
                bb.setEnabled(True)
                self.fx.append(bb)
        except Exception:
            pass

    # ------------------------------------------------------------ zdarzenia Androida
    def media_event(self, ev):
        if ev == "play":
            self.resume()
        elif ev == "pause":
            self.pause()
        elif ev == "toggle":
            self.toggle()
        elif ev == "next":
            self.skip_next()
        elif ev == "prev":
            self.skip_prev()
        elif ev == "quit":
            self.end("quit")
        elif ev.startswith("seek:"):
            self.seek(int(ev[5:]) / 1000)
        elif ev == "focus_loss":
            self.focus_paused = False
            self.pause()
        elif ev == "focus_pause":
            if self.mp is not None and not self.paused:
                self.pause()
                self.focus_paused = True
        elif ev == "focus_duck":
            self.duck = 0.3
            self.apply_vol()
        elif ev == "focus_gain":
            self.duck = 1.0
            self.apply_vol()
            if self.focus_paused:
                self.focus_paused = False
                self.resume()
        elif ev.startswith("done:"):
            if self.mp is not None and int(ev[5:]) == self.mp_id and not self.paused:
                self.track_ended()
        elif ev.startswith("err:"):
            parts = ev.split(":", 2)
            if self.mp is not None and int(parts[1]) == self.mp_id:
                self.fail(f"Błąd odtwarzacza Androida ({parts[2] if len(parts) > 2 else '?'})")

    def check_ready(self):
        while True:
            try:
                tok, index, res, art = self.ready.get_nowait()
            except queue.Empty:
                return
            if tok != self.token:
                if not isinstance(res, Exception):
                    try:
                        res.release()
                    except Exception:
                        pass
                continue
            self.loading = False
            if isinstance(res, Exception):
                self.fail(res)
                continue
            self.attach(res, 0, art)
            self.send(event="started", index=index)
            self.refresh_notif(force=True)

    def check_crossfade(self):
        if (self.xf <= 0 or self.mp is None or self.paused or self.loading or self.old
                or self.xf_started or self.stop_after):
            return
        if not (0 <= self.index < len(self.queue)) or is_stream(self.queue[self.index][0]):
            return
        dur = self.duration()
        if dur <= self.xf * 2 or self.position() < dur - self.xf:
            return
        nxt = self.next_index(auto=True)
        if nxt is None or is_stream(self.queue[nxt][0]):
            return
        self.xf_started = True
        self.play(nxt, fade=self.xf)

    # ------------------------------------------------------------ powiadomienie
    def refresh_notif(self, force=False):
        if not self.active or not (0 <= self.index < len(self.queue)):
            return
        t = self.queue[self.index]
        playing = not self.paused
        dur = self.duration()
        key = (self.index, playing, self.loading, self.art, int(dur), self.speed)
        now = time.time()
        if not force and key == self.notif_key and now - self.last_notif < 15:
            return
        self.notif_key, self.last_notif = key, now
        title = str(t[1] or "?") if len(t) > 1 else "?"
        if self.loading:
            title = "Wczytywanie: " + title
        artist = str(t[2] or "") if len(t) > 2 else ""
        src = t[0] if not is_stream(t[0]) else ""
        try:
            Media.update(title, artist, int(dur * 1000), int(self.position() * 1000),
                         playing, float(self.speed), self.art, src)
        except Exception as e:
            log("powiadomienie:", e)

    # ------------------------------------------------------------ pętla
    def run(self):
        self.send(event="state", queue_file=self.queue_file, active=False, index=-1, paused=False)
        while True:
            try:
                try:
                    data, _ = self.sock.recvfrom(65535)
                    self.handle(json.loads(data.decode("utf-8")))
                    self.sock.setblocking(False)
                    try:
                        while True:
                            data, _ = self.sock.recvfrom(65535)
                            self.handle(json.loads(data.decode("utf-8")))
                    except (BlockingIOError, socket.timeout):
                        pass
                    finally:
                        self.sock.settimeout(0.05)
                except socket.timeout:
                    pass
                while True:
                    ev = Media.poll()
                    if ev is None:
                        break
                    self.media_event(ev)
                self.check_ready()
                if self.old:
                    self.fade_step()
                self.check_crossfade()
                now = time.time()
                if now - self.last_status >= 0.5:
                    self.last_status = now
                    playing = False
                    try:
                        playing = self.mp is not None and bool(self.mp.isPlaying())
                    except Exception:
                        pass
                    self.send(event="status", pos=self.position(), dur=self.duration(),
                              playing=playing, paused=self.paused, index=self.index,
                              loading=self.loading)
                    self.refresh_notif()
            except Exception as e:
                log("pętla:", e)
                time.sleep(0.1)


patch_ytdlp()
Usluga().run()
