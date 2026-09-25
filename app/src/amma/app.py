"""Amma - Tamil calendar, good-morning cards and stories for Amma.

The UI is a single local web page (resources/web/index.html) shown in a Toga
WebView. Python does the native work: downloading data, sharing to WhatsApp,
saving to the gallery, Tamil text-to-speech and the daily 6:30 AM alarm.
The page queues requests; we collect them with `amma.drain()` every 300 ms.
"""
import asyncio
import json
import shutil
import threading
import urllib.request
from pathlib import Path

import toga
from toga.style import Pack

from . import pmtext

RAW = "https://raw.githubusercontent.com/santh0sh/amma-app/data/"
ASSET_URL = "https://appassets.androidplatform.net/cache/amma/index.html"
UA = {"User-Agent": "AmmaApp/1.0 (Android)"}

try:  # Android only
    from java import dynamic_proxy, jclass
    from android.speech.tts import TextToSpeech
    ANDROID = True
except ImportError:  # desktop dev run
    ANDROID = False


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


if ANDROID:
    class _TtsInit(dynamic_proxy(TextToSpeech.OnInitListener)):
        def __init__(self, app):
            super().__init__()
            self.app = app

        def onInit(self, status):
            self.app.tts_ready = status == TextToSpeech.SUCCESS
            if self.app.tts_ready:
                Locale = jclass("java.util.Locale")
                self.app.tts.setLanguage(Locale("ta", "IN"))
                self.app.tts.setSpeechRate(0.85)


class Amma(toga.App):
    def startup(self):
        self.root = Path(self.paths.cache) / "amma"
        self.root.mkdir(parents=True, exist_ok=True)
        self._install_web()
        self.tts = None
        self.tts_ready = False
        self.web = toga.WebView(style=Pack(flex=1))
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = self.web
        self.main_window.show()
        self.web._impl.set_url(ASSET_URL)
        self.loop.create_task(self._poll())
        self.loop.create_task(self._sync())
        if ANDROID:
            try:
                self._schedule_alarm()
            except Exception as e:  # never block the UI on alarm setup
                print("alarm setup failed", e)

    # ---------- files ----------
    def _install_web(self):
        web = Path(__file__).parent / "resources" / "web"
        for f in web.rglob("*"):
            if f.is_file():
                dest = self.root / f.relative_to(web)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, dest)
        for sub in ("data", "cards", "texts"):
            (self.root / sub).mkdir(exist_ok=True)

    async def _sync(self):
        """Pull today's data + cards from the data branch, then tell the page."""
        def work():
            got = []
            for name in ("today", "month", "notify", "new"):
                try:
                    (self.root / "data" / f"{name}.json").write_bytes(fetch(RAW + f"data/{name}.json"))
                    got.append(name)
                except Exception as e:
                    print("sync", name, e)
            cat = self.root / "data" / "catalog.json"
            try:
                today = json.loads((self.root / "data" / "today.json").read_text("utf-8"))
                for c in today.get("cards", []):
                    p = self.root / c["file"]
                    if not p.exists():
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_bytes(fetch(RAW + c["file"]))
                new = json.loads((self.root / "data" / "new.json").read_text("utf-8"))
                if not cat.exists() or new.get("updated", "") > self._mtime_day(cat):
                    cat.write_bytes(fetch(RAW + "data/catalog.json", timeout=60))
            except Exception as e:
                print("sync cards/catalog", e)
            if ANDROID and "notify" in got:
                ctx = self._ctx()
                shutil.copyfile(self.root / "data" / "notify.json",
                                Path(ctx.getFilesDir().getAbsolutePath()) / "notify.json")
            return got

        await self.loop.run_in_executor(None, work)
        self._js("amma.reload()")

    @staticmethod
    def _mtime_day(p):
        import datetime as dt
        return dt.date.fromtimestamp(p.stat().st_mtime).isoformat()

    # ---------- bridge ----------
    def _js(self, code):
        try:
            self.web.evaluate_javascript(code)
        except Exception as e:
            print("js", e)

    async def _poll(self):
        while True:
            await asyncio.sleep(0.3)
            try:
                raw = await self.web.evaluate_javascript("window.amma ? amma.drain() : '[]'")
                items = json.loads(json.loads(raw) if isinstance(raw, str) and raw.startswith('"') else raw or "[]")
            except Exception:
                continue
            for it in items:
                try:
                    getattr(self, "act_" + it.pop("action"))(**it)
                except Exception as e:
                    print("action failed", e)
                    self._js(f"amma.toast({json.dumps('பிழை: ' + str(e)[:60])})")

    # ---------- Android helpers ----------
    def _ctx(self):
        return self._impl.native

    def _start(self, intent):
        intent.addFlags(jclass("android.content.Intent").FLAG_ACTIVITY_NEW_TASK)
        self._ctx().startActivity(intent)

    def _file(self, rel):
        return self.root / rel

    # ---------- actions ----------
    def act_share(self, file, caption="", app="whatsapp"):
        Intent = jclass("android.content.Intent")
        FileProvider = jclass("androidx.core.content.FileProvider")
        File = jclass("java.io.File")
        ctx = self._ctx()
        shared = Path(ctx.getCacheDir().getAbsolutePath()) / "shared"
        shared.mkdir(exist_ok=True)
        dest = shared / "kaalai_vanakkam.jpg"
        shutil.copyfile(self._file(file), dest)
        uri = FileProvider.getUriForFile(ctx, ctx.getPackageName() + ".fileprovider", File(str(dest)))
        i = Intent(Intent.ACTION_SEND)
        i.setType("image/jpeg")
        i.putExtra(Intent.EXTRA_STREAM, uri)
        if caption:
            i.putExtra(Intent.EXTRA_TEXT, caption)
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        if app == "whatsapp":
            i.setPackage("com.whatsapp")
            try:
                self._start(i)
                return
            except Exception:
                i.setPackage(None)
        self._start(Intent.createChooser(i, "அனுப்பு"))

    def act_download(self, file):
        ctx = self._ctx()
        Build = jclass("android.os.Build")
        name = "amma_" + Path(file).name
        data = self._file(file).read_bytes()
        if Build.VERSION.SDK_INT >= 29:
            MediaStore = jclass("android.provider.MediaStore")
            ContentValues = jclass("android.content.ContentValues")
            v = ContentValues()
            v.put(MediaStore.MediaColumns.DISPLAY_NAME, name)
            v.put(MediaStore.MediaColumns.MIME_TYPE, "image/jpeg")
            v.put(MediaStore.MediaColumns.RELATIVE_PATH, "Pictures/Amma")
            resolver = ctx.getContentResolver()
            uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, v)
            out = resolver.openOutputStream(uri)
            out.write(data)
            out.close()
        else:
            Env = jclass("android.os.Environment")
            d = Path(Env.getExternalStoragePublicDirectory(Env.DIRECTORY_PICTURES).getAbsolutePath()) / "Amma"
            d.mkdir(parents=True, exist_ok=True)
            (d / name).write_bytes(data)
        self._js("amma.toast('படம் Gallery-ல் சேமிக்கப்பட்டது ✅')")

    def act_open_url(self, url):
        Intent = jclass("android.content.Intent")
        Uri = jclass("android.net.Uri")
        self._start(Intent(Intent.ACTION_VIEW, Uri.parse(url)))

    def act_load_story(self, id, parts="[]"):
        urls = json.loads(parts)

        def work():
            try:
                text = ""
                for u in urls:
                    raw = fetch(u, timeout=60).decode("utf-8", "replace")
                    text += ("\n\n" if text else "") + pmtext.html_to_text(raw)
                pages = pmtext.paginate(text)
                if not pages:
                    raise ValueError("empty")
                (self.root / "texts" / f"{id}.json").write_text(
                    json.dumps({"id": id, "pages": pages}, ensure_ascii=False), "utf-8")
                ok, msg = True, ""
            except Exception as e:
                ok, msg = False, "இணையம் இல்லை அல்லது கதை கிடைக்கவில்லை"
                print("story", id, e)
            self.loop.call_soon_threadsafe(
                self._js, f"amma.onStory({json.dumps(id)},{str(ok).lower()},{json.dumps(msg)})")

        threading.Thread(target=work, daemon=True).start()

    def act_tts_speak(self, text):
        if self.tts is None:
            self.tts = TextToSpeech(self._ctx(), _TtsInit(self))
            self.loop.call_later(1.5, self.act_tts_speak, text)
            return
        if not self.tts_ready:
            self._js("amma.speaking(false);amma.toast('தமிழ் குரல் இல்லை - அமைப்பில் பதிவிறக்குங்கள்')")
            return
        self.tts.stop()
        for n, para in enumerate(p for p in text.split("\n\n") if p.strip()):
            for k in range(0, len(para), 3500):
                self.tts.speak(para[k:k + 3500], TextToSpeech.QUEUE_ADD, None, f"p{n}_{k}")

    def act_tts_stop(self):
        if self.tts:
            self.tts.stop()
        self._js("amma.speaking(false)")

    def act_notif_permission(self):
        Build = jclass("android.os.Build")
        if Build.VERSION.SDK_INT >= 33:
            self._impl.request_permissions(
                ["android.permission.POST_NOTIFICATIONS"],
                lambda perms, res: self._js("amma.toast('நன்றி ✅')"))
        else:
            self._js("amma.toast('ஏற்கனவே அனுமதி உள்ளது ✅')")

    def act_battery(self):
        Intent = jclass("android.content.Intent")
        Uri = jclass("android.net.Uri")
        Settings = jclass("android.provider.Settings")
        try:
            self._start(Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                               Uri.parse("package:" + self._ctx().getPackageName())))
        except Exception:
            self._start(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))

    def act_app_settings(self):
        Intent = jclass("android.content.Intent")
        Uri = jclass("android.net.Uri")
        Settings = jclass("android.provider.Settings")
        self._start(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                           Uri.parse("package:" + self._ctx().getPackageName())))

    def act_tts_settings(self):
        Intent = jclass("android.content.Intent")
        self._start(Intent("com.android.settings.TTS_SETTINGS"))

    def act_test_notify(self):
        jclass("io.github.santh0sh.amma.AlarmReceiver").showNow(self._ctx())

    def _schedule_alarm(self):
        jclass("io.github.santh0sh.amma.AmmaAlarm").schedule(self._ctx())


def main():
    return Amma("அம்மா", "io.github.santh0sh.amma")
