"""English Adventure (mobile) - Grade 8 / Prospect 2 (lessons 1-7).  Kivy app with sound effects + audio.
Desktop test:  python main.py        Android APK: see README.txt (buildozer)
"""
import datetime
import json
import math
import os
import random
import re

import arabic_reshaper
from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Mesh, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex as hexc
from kivy.utils import platform

try:
    from bidi import get_display
except ImportError:  # older python-bidi
    from bidi.algorithm import get_display

BASE = os.path.dirname(os.path.abspath(__file__))
LabelBase.register(name="Vazir", fn_regular=os.path.join(BASE, "fonts", "Vazirmatn.ttf"),
                   fn_bold=os.path.join(BASE, "fonts", "Vazirmatn.ttf"))

BG, CARD, ACC = "#1b2540", "#2b3a67", "#ffb703"
GOOD, BAD, TXT, MUTED, DARK = "#2ecc71", "#e74c3c", "#ffffff", "#aab4d4", "#111111"
DAILY_GOAL = 10
BADGES = {
    "first": ("First Steps", "Finish your first game"),
    "xp100": ("100 XP", "Earn 100 XP"),
    "streak3": ("3-Day Streak", "Practice 3 days in a row"),
    "words20": ("Word Collector", "Review 20 flashcards"),
    "perfect": ("Perfect!", "Get a perfect score"),
}


# ------------------------------------------------------------ text helpers
def fa(text, width=24):
    """Shape + reorder Persian text for Kivy (which has no RTL support); wraps manually."""
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return "\n".join(get_display(arabic_reshaper.reshape(l)) for l in lines)


def load_lessons():
    out = []
    d = os.path.join(BASE, "data")
    for name in sorted(os.listdir(d)):
        if name.startswith("lesson") and name.endswith(".json"):
            with open(os.path.join(d, name), encoding="utf-8") as f:
                out.append(json.load(f))
    return out


# ------------------------------------------------------------ storage
class Store:
    def __init__(self, path):
        self.path = path
        self.d = {"xp": 0, "streak": 0, "last_day": "", "badges": [], "reviewed": 0,
                  "boxes": {}, "mission_day": "", "mission_n": 0, "sfx": True}
        try:
            with open(path, encoding="utf-8") as f:
                self.d.update(json.load(f))
        except Exception:
            pass

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False)
        except Exception:
            pass

    xp = property(lambda s: s.d["xp"])
    level = property(lambda s: s.d["xp"] // 100 + 1)
    streak = property(lambda s: s.d["streak"])

    def box(self, w):
        return self.d["boxes"].get(w, 1)

    def set_box(self, w, b):
        self.d["boxes"][w] = b

    def unlock(self, key, new):
        if key not in self.d["badges"]:
            self.d["badges"].append(key)
            new.append(key)

    def _touch_streak(self):
        today = datetime.date.today()
        last = self.d["last_day"]
        if last == today.isoformat():
            return
        if last and (today - datetime.date.fromisoformat(last)).days == 1:
            self.d["streak"] += 1
        else:
            self.d["streak"] = 1
        self.d["last_day"] = today.isoformat()

    def add_xp(self, n, perfect=False):
        new = []
        self._touch_streak()
        self.d["xp"] += n
        self.unlock("first", new)
        if self.xp >= 100:
            self.unlock("xp100", new)
        if self.streak >= 3:
            self.unlock("streak3", new)
        if perfect:
            self.unlock("perfect", new)
        if self.d["reviewed"] >= 20:
            self.unlock("words20", new)
        self.save()
        return new

    def mission_count(self):
        if self.d["mission_day"] != datetime.date.today().isoformat():
            return 0
        return self.d["mission_n"]

    def add_mission(self):
        before = self.mission_count()
        self.d["mission_day"] = datetime.date.today().isoformat()
        self.d["mission_n"] = before + 1
        return 20 if before + 1 == DAILY_GOAL else 0


# ------------------------------------------------------------ sound + speech
class Sfx:
    def __init__(self, store):
        self.store, self.cache = store, {}

    def play(self, name):
        if not self.store.d.get("sfx", True):
            return
        snd = self.cache.get(name)
        if snd is None:
            snd = SoundLoader.load(os.path.join(BASE, "sounds", name + ".wav"))
            self.cache[name] = snd or False
        if snd:
            snd.stop()
            snd.play()

    def buzz(self):
        if platform == "android" and self.store.d.get("sfx", True):
            try:
                from plyer import vibrator
                vibrator.vibrate(0.12)
            except Exception:
                pass


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:80]


_voices, _current = {}, [None]


def speak(text):
    """Plays the pre-recorded pronunciation audio/<slug>.ogg (made by make_audio.py).
    Falls back to the phone's text-to-speech only if the recording is missing."""
    path = os.path.join(BASE, "audio", slug(text) + ".ogg")
    if os.path.exists(path):
        snd = _voices.get(path)
        if snd is None:
            snd = _voices[path] = SoundLoader.load(path) or False
        if snd:
            if _current[0] and _current[0] is not snd:
                _current[0].stop()
            snd.stop()
            snd.play()
            _current[0] = snd
            return
    try:
        from plyer import tts
        tts.speak(text)
    except Exception:
        pass


# ------------------------------------------------------------ widgets
class T(Label):
    """Label with the Persian-capable font; wrap=True makes it auto-height and wrapping."""

    def __init__(self, wrap=False, **kw):
        kw.setdefault("font_name", "Vazir")
        kw.setdefault("color", hexc(TXT))
        kw.setdefault("font_size", sp(16))
        kw.setdefault("halign", "center")
        kw.setdefault("valign", "middle")
        super().__init__(**kw)
        if wrap:
            self.size_hint_y = None
            self.bind(width=lambda i, w: setattr(i, "text_size", (w, None)))
            self.bind(texture_size=lambda i, ts: setattr(i, "height", ts[1] + dp(8)))
        else:
            self.bind(size=lambda i, s: setattr(i, "text_size", s))


class Btn(ButtonBehavior, Label):
    def __init__(self, text="", bg=ACC, fg=DARK, silent=False, **kw):
        kw.setdefault("font_name", "Vazir")
        kw.setdefault("font_size", sp(17))
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(52))
        kw.setdefault("halign", "center")
        kw.setdefault("valign", "middle")
        super().__init__(text=text, color=hexc(fg), **kw)
        self.silent = silent
        with self.canvas.before:
            self._c = Color(*hexc(bg))
            self._r = RoundedRectangle(radius=[dp(14)])
        self.bind(pos=self._upd, size=self._upd)
        self.bind(size=lambda i, s: setattr(i, "text_size", (s[0] - dp(10), s[1])))

    def _upd(self, *_):
        self._r.pos, self._r.size = self.pos, self.size

    def set_bg(self, bg, fg=None):
        self._c.rgba = hexc(bg)
        if fg:
            self.color = hexc(fg)

    def on_press(self):
        if not self.silent:
            App.get_running_app().sfx.play("click")


class Panel(BoxLayout):
    def __init__(self, bg=CARD, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*hexc(bg))
            self._r = RoundedRectangle(radius=[dp(18)])
        self.bind(pos=lambda *_: setattr(self._r, "pos", self.pos),
                  size=lambda *_: setattr(self._r, "size", self.size))


class StarRow(Widget):
    def __init__(self, n, total=3, **kw):
        super().__init__(size_hint=(None, None), size=(dp(60) * total, dp(56)), **kw)
        self.n, self.total = n, total
        self.bind(pos=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            for i in range(self.total):
                Color(*hexc(ACC if i < self.n else "#44527f"))
                cx, cy, r = self.x + dp(30) + i * dp(60), self.center_y, dp(26)
                v = [cx, cy, 0, 0]
                for k in range(11):
                    a = math.pi / 2 + k * math.pi / 5
                    rr = r if k % 2 == 0 else r * 0.45
                    v += [cx + rr * math.cos(a), cy + rr * math.sin(a), 0, 0]
                Mesh(vertices=v, indices=list(range(12)), mode="triangle_fan")


class LivesRow(Widget):
    def __init__(self, n, total=3, **kw):
        super().__init__(size_hint=(None, None), size=(dp(26) * total, dp(26)), **kw)
        self.n, self.total = n, total
        self.bind(pos=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            for i in range(self.total):
                Color(*hexc(BAD if i < self.n else "#44527f"))
                Ellipse(pos=(self.x + i * dp(26), self.y), size=(dp(20), dp(20)))


class XpBar(Widget):
    def __init__(self, frac, **kw):
        super().__init__(size_hint_y=None, height=dp(12), **kw)
        self.frac = frac
        self.bind(pos=self.draw, size=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(*hexc(BG))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])
            Color(*hexc(ACC))
            RoundedRectangle(pos=self.pos, size=(max(dp(12), self.width * self.frac), self.height),
                             radius=[dp(6)])


# ------------------------------------------------------------ screens
class Page(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation="vertical", padding=dp(14), spacing=dp(10), **kw)
        self.app = app

    def after(self, delay, fn):
        Clock.schedule_once(lambda dt: fn() if self.parent else None, delay)


class Home(Page):
    def __init__(self, app):
        super().__init__(app)
        s = app.store
        sv = ScrollView(do_scroll_x=False)
        col = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, padding=[0, 0, 0, dp(10)])
        col.bind(minimum_height=col.setter("height"))
        sv.add_widget(col)
        self.add_widget(sv)

        col.add_widget(T(text="English Adventure", font_size=sp(30), color=hexc(ACC),
                         size_hint_y=None, height=dp(52)))
        col.add_widget(T(text="Grade 8  |  Prospect 2", font_size=sp(13), color=hexc(MUTED),
                         size_hint_y=None, height=dp(20)))

        card = Panel(orientation="vertical", size_hint_y=None, height=dp(120), padding=dp(14),
                     spacing=dp(8))
        row = BoxLayout(size_hint_y=None, height=dp(40))
        row.add_widget(T(text=f"Level {s.level}", font_size=sp(22), color=hexc(ACC)))
        row.add_widget(T(text=f"{s.xp} XP"))
        row.add_widget(T(text=f"Streak: {s.streak}"))
        card.add_widget(row)
        card.add_widget(XpBar((s.xp % 100) / 100))
        done = min(s.mission_count(), DAILY_GOAL)
        card.add_widget(T(text=f"Daily mission: {done}/{DAILY_GOAL} flashcards",
                          font_size=sp(14), color=hexc(GOOD if done >= DAILY_GOAL else TXT)))
        col.add_widget(card)

        col.add_widget(T(text="Choose a lesson", font_size=sp(13), color=hexc(MUTED),
                         size_hint_y=None, height=dp(22)))
        grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        self.lesson_btns = []
        for les in app.lessons:
            sel = les is app.lesson
            b = Btn(text=les["title"], bg=ACC if sel else CARD, fg=DARK if sel else TXT,
                    font_size=sp(13), height=dp(48))
            b.les = les
            b.bind(on_release=self.pick)
            grid.add_widget(b)
            self.lesson_btns.append(b)
        col.add_widget(grid)
        for name, cls, color, fg in (("Flashcards", Flashcards, "#4cc9f0", DARK),
                                     ("Match Game", Match, "#f72585", TXT),
                                     ("Sentence Builder", Sentence, "#b5179e", TXT),
                                     ("Listen & Choose", ListenGame, "#06d6a0", DARK),
                                     ("Boss Quiz", Quiz, "#fb8500", DARK)):
            col.add_widget(Btn(text=name, bg=color, fg=fg, height=dp(62), font_size=sp(20),
                               on_release=lambda *_, c=cls: app.show(c(app))))

        self.sfx_btn = Btn(text=self._sfx_text(), bg=CARD, fg=TXT, font_size=sp(14),
                           on_release=self.toggle_sfx)
        col.add_widget(self.sfx_btn)

        col.add_widget(T(text="Badges", color=hexc(MUTED), size_hint_y=None, height=dp(30)))
        for key, (name, desc) in BADGES.items():
            got = key in s.d["badges"]
            col.add_widget(T(text=name if got else "(locked) " + desc, font_size=sp(14),
                             color=hexc(ACC if got else MUTED), size_hint_y=None, height=dp(26)))

    def _sfx_text(self):
        return "Sound effects: " + ("ON" if self.app.store.d["sfx"] else "OFF")

    def toggle_sfx(self, *_):
        d = self.app.store.d
        d["sfx"] = not d["sfx"]
        self.app.store.save()
        self.sfx_btn.text = self._sfx_text()
        self.app.sfx.play("click")

    def pick(self, b):
        self.app.lesson = b.les
        for x in self.lesson_btns:
            sel = x.les is b.les
            x.set_bg(ACC if sel else CARD, DARK if sel else TXT)


class Game(Page):
    name = ""

    def __init__(self, app):
        super().__init__(app)
        self.lesson, self.store, self.sfx = app.lesson, app.store, app.sfx
        head = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        head.add_widget(Btn(text="< Menu", bg=CARD, fg=TXT, size_hint_x=None, width=dp(92),
                            height=dp(44), font_size=sp(14), on_release=lambda *_: app.home()))
        head.add_widget(T(text=self.name, font_size=sp(18), color=hexc(ACC)))
        self.info = T(text="", font_size=sp(14), color=hexc(MUTED), size_hint_x=None, width=dp(80))
        head.add_widget(self.info)
        self.add_widget(head)
        self.body = BoxLayout(orientation="vertical", spacing=dp(10))
        self.add_widget(self.body)


class Flashcards(Game):
    name = "Flashcards"

    def __init__(self, app):
        super().__init__(app)
        self.deck = sorted(self.lesson["words"],
                           key=lambda w: self.store.box(w["en"]) + random.random())[:10]
        self.i = self.known = self.bonus = 0
        self.show_card()

    def show_card(self):
        self.body.clear_widgets()
        w = self.deck[self.i]
        self.info.text = f"{self.i + 1}/{len(self.deck)}"
        card = Panel(orientation="vertical", padding=dp(16), spacing=dp(10))
        card.add_widget(T(text=f"Box {self.store.box(w['en'])}/5", font_size=sp(12),
                          color=hexc(MUTED), size_hint_y=None, height=dp(20)))
        card.add_widget(T(text=w["en"], font_size=sp(44)))
        card.add_widget(Btn(text="Listen", bg="#4cc9f0", height=dp(44),
                            on_release=lambda *_: speak(w["en"])))
        self.meaning = T(text="", font_size=sp(30), color=hexc(ACC))
        card.add_widget(self.meaning)
        self.body.add_widget(card)
        self.actions = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))
        self.actions.add_widget(Btn(text="Show meaning", height=dp(60), on_release=self.reveal))
        self.body.add_widget(self.actions)
        self.sfx.play("flip")
        self.after(0.25, lambda: speak(w["en"]))

    def reveal(self, *_):
        w = self.deck[self.i]
        self.meaning.text = fa(w["fa"])
        self.sfx.play("flip")
        self.actions.clear_widgets()
        self.actions.add_widget(Btn(text="Not yet", bg=BAD, fg=TXT, height=dp(60),
                                    on_release=lambda *_: self.rate(False)))
        self.actions.add_widget(Btn(text="I knew it!", bg=GOOD, fg=TXT, height=dp(60),
                                    on_release=lambda *_: self.rate(True)))

    def rate(self, knew):
        w = self.deck[self.i]
        box = self.store.box(w["en"])
        self.store.set_box(w["en"], min(5, box + 1) if knew else 1)
        self.known += knew
        self.bonus += self.store.add_mission()
        self.sfx.play("correct" if knew else "wrong")
        self.i += 1
        if self.i < len(self.deck):
            self.after(0.35, self.show_card)
        else:
            self.store.d["reviewed"] += len(self.deck)
            self.after(0.5, lambda: self.app.finish("Flashcards", self.known, len(self.deck),
                                                    self.bonus))


class Match(Game):
    name = "Match Game"

    def __init__(self, app):
        super().__init__(app)
        self.pairs = random.sample(self.lesson["words"], 6)
        self.mistakes = self.matched = 0
        self.sel = None
        self.info.text = "EN - FA"
        cols = BoxLayout(spacing=dp(12))
        en = [p["en"] for p in self.pairs]
        fas = [(p["fa"], p["en"]) for p in self.pairs]
        random.shuffle(en)
        random.shuffle(fas)
        left = BoxLayout(orientation="vertical", spacing=dp(8))
        right = BoxLayout(orientation="vertical", spacing=dp(8))
        for key in en:
            left.add_widget(self.mk(key, key, "en"))
        for text, key in fas:
            right.add_widget(self.mk(fa(text, 12), key, "fa"))
        cols.add_widget(left)
        cols.add_widget(right)
        self.body.add_widget(cols)

    def mk(self, text, key, side):
        b = Btn(text=text, bg=CARD, fg=TXT, size_hint_y=1, font_size=sp(18), silent=True)
        b.key, b.side = key, side
        b.bind(on_release=self.click)
        return b

    def click(self, b):
        if self.sel is None or self.sel is b:
            self._select(b)
            return
        p = self.sel
        if p.side == b.side:
            p.set_bg(CARD, TXT)
            self._select(b)
            return
        self.sel = None
        if p.key == b.key:
            for x in (p, b):
                x.set_bg(GOOD, TXT)
                x.disabled = True
            self.matched += 1
            self.sfx.play("match")
            if self.matched == 6:
                self.after(0.7, lambda: self.app.finish("Match Game",
                                                        max(0, 6 - self.mistakes), 6))
        else:
            self.mistakes += 1
            self.sfx.play("wrong")
            self.sfx.buzz()
            for x in (p, b):
                x.set_bg(BAD, TXT)
            self.after(0.45, lambda: [x.set_bg(CARD, TXT) for x in (p, b) if not x.disabled])

    def _select(self, b):
        self.sfx.play("click")
        self.sel = b
        b.set_bg(ACC, DARK)


class Sentence(Game):
    name = "Sentence Builder"

    def __init__(self, app):
        super().__init__(app)
        self.items = random.sample(self.lesson["sentences"], min(5, len(self.lesson["sentences"])))
        self.i = self.score = 0
        self.show()

    def show(self):
        self.body.clear_widgets()
        it = self.items[self.i]
        self.info.text = f"{self.i + 1}/{len(self.items)}"
        self.sentence = it["en"]
        self.target, self.built, self.failed = it["en"].split(), [], False
        self.body.add_widget(T(text=fa(it["fa"], 26), font_size=sp(20), color=hexc(ACC),
                               size_hint_y=None, height=dp(90)))
        panel = Panel(padding=dp(12), size_hint_y=None, height=dp(110))
        self.out = T(text="", font_size=sp(20))
        panel.add_widget(self.out)
        self.body.add_widget(panel)
        words = self.target[:]
        random.shuffle(words)
        grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None,
                          height=math.ceil(len(words) / 3) * dp(56))
        self.btns = []
        for w in words:
            b = Btn(text=w, bg="#4cc9f0", height=dp(48), font_size=sp(16), silent=True)
            b.bind(on_release=lambda btn: self.add(btn))
            grid.add_widget(b)
            self.btns.append(b)
        self.body.add_widget(grid)
        self.msg = T(text="", size_hint_y=None, height=dp(30))
        self.body.add_widget(self.msg)
        self.body.add_widget(Widget())
        row = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(10))
        row.add_widget(Btn(text="Clear", bg=CARD, fg=TXT, height=dp(56), on_release=self.reset))
        row.add_widget(Btn(text="Check", bg=GOOD, fg=TXT, height=dp(56), on_release=self.check))
        self.body.add_widget(row)

    def add(self, b):
        self.sfx.play("click")
        self.built.append(b.text)
        b.disabled = True
        b.set_bg("#44527f")
        self.out.text = " ".join(self.built)

    def reset(self, *_):
        self.built = []
        self.out.text = ""
        for b in self.btns:
            b.disabled = False
            b.set_bg("#4cc9f0")

    def check(self, *_):
        if self.built == self.target:
            self.score += 0 if self.failed else 1
            self.msg.text, self.msg.color = "Correct!", hexc(GOOD)
            self.sfx.play("correct")
            self.after(0.5, lambda: speak(self.sentence))
            self.after(2.8, self.next)
        else:
            self.failed = True
            self.msg.text, self.msg.color = "Not quite - try again", hexc(BAD)
            self.sfx.play("wrong")
            self.sfx.buzz()

    def next(self):
        self.i += 1
        if self.i < len(self.items):
            self.show()
        else:
            self.app.finish("Sentence Builder", self.score, len(self.items))


class ListenGame(Game):
    name = "Listen & Choose"

    def __init__(self, app):
        super().__init__(app)
        self.words = self.lesson["words"]
        self.qs = random.sample(self.words, min(8, len(self.words)))
        self.i = self.score = 0
        self.show()

    def show(self):
        self.body.clear_widgets()
        w = self.qs[self.i]
        self.info.text = f"{self.i + 1}/{len(self.qs)}"
        self.body.add_widget(T(text="What word do you hear?", font_size=sp(20),
                               size_hint_y=None, height=dp(50)))
        self.body.add_widget(Btn(text="Play sound", bg="#4cc9f0", height=dp(84), font_size=sp(24),
                                 on_release=lambda *_: speak(w["en"])))
        opts = random.sample([x["en"] for x in self.words if x is not w], 3) + [w["en"]]
        random.shuffle(opts)
        self.opts = []
        for o in opts:
            b = Btn(text=o, bg=CARD, fg=TXT, height=dp(60), font_size=sp(20), silent=True)
            b.value = o
            b.bind(on_release=self.answer)
            self.body.add_widget(b)
            self.opts.append(b)
        self.body.add_widget(Widget())
        self.after(0.3, lambda: speak(w["en"]))

    def answer(self, b):
        right = self.qs[self.i]["en"]
        for x in self.opts:
            x.disabled = True
            if x.value == right:
                x.set_bg(GOOD, TXT)
        if b.value == right:
            self.score += 1
            self.sfx.play("correct")
        else:
            b.set_bg(BAD, TXT)
            self.sfx.play("wrong")
            self.sfx.buzz()
        self.after(1.1, self.next)

    def next(self):
        self.i += 1
        if self.i < len(self.qs):
            self.show()
        else:
            self.app.finish("Listen & Choose", self.score, len(self.qs))


class Quiz(Game):
    name = "Boss Quiz"

    def __init__(self, app):
        super().__init__(app)
        words = self.lesson["words"]
        qs = []
        for w in random.sample(words, min(6, len(words))):
            opts = random.sample([x["fa"] for x in words if x is not w], 3) + [w["fa"]]
            random.shuffle(opts)
            qs.append({"q": f'Meaning of "{w["en"]}"?', "options": opts, "answer": w["fa"],
                       "persian": True})
        for g in random.sample(self.lesson["grammar"], min(4, len(self.lesson["grammar"]))):
            o = g["options"][:]
            random.shuffle(o)
            qs.append({"q": g["q"], "options": o, "answer": g["answer"], "persian": False})
        random.shuffle(qs)
        self.qs, self.i, self.score, self.hearts = qs, 0, 0, 3
        self.show()

    def show(self):
        self.body.clear_widgets()
        q = self.qs[self.i]
        self.info.text = f"{self.i + 1}/{len(self.qs)}"
        lives = AnchorLayout(size_hint_y=None, height=dp(30))
        lives.add_widget(LivesRow(self.hearts))
        self.body.add_widget(lives)
        self.body.add_widget(T(text=q["q"], font_size=sp(22), size_hint_y=None, height=dp(110)))
        self.opts = []
        for o in q["options"]:
            b = Btn(text=fa(o, 22) if q["persian"] else o, bg=CARD, fg=TXT, height=dp(62),
                    font_size=sp(19), silent=True)
            b.value = o
            b.bind(on_release=self.answer)
            self.body.add_widget(b)
            self.opts.append(b)
        self.body.add_widget(Widget())

    def answer(self, b):
        q = self.qs[self.i]
        for x in self.opts:
            x.disabled = True
            if x.value == q["answer"]:
                x.set_bg(GOOD, TXT)
        if b.value == q["answer"]:
            self.score += 1
            self.sfx.play("correct")
        else:
            b.set_bg(BAD, TXT)
            self.hearts -= 1
            self.sfx.play("wrong")
            self.sfx.buzz()
        self.after(1.0, self.next)

    def next(self):
        self.i += 1
        if self.hearts <= 0 or self.i >= len(self.qs):
            self.app.finish("Boss Quiz", self.score, len(self.qs))
        else:
            self.show()


class Result(Page):
    def __init__(self, app, title, correct, total, xp, new_badges, leveled):
        super().__init__(app)
        pct = correct / total if total else 0
        stars = 3 if pct >= 0.9 else 2 if pct >= 0.6 else 1
        self.add_widget(Widget())
        self.add_widget(T(text=title, color=hexc(MUTED), size_hint_y=None, height=dp(30)))
        wrap = AnchorLayout(size_hint_y=None, height=dp(64))
        wrap.add_widget(StarRow(stars))
        self.add_widget(wrap)
        self.add_widget(T(text=f"{correct} / {total} correct", font_size=sp(28),
                          size_hint_y=None, height=dp(50)))
        self.add_widget(T(text=f"+{xp} XP", font_size=sp(34), color=hexc(ACC),
                          size_hint_y=None, height=dp(56)))
        if leveled:
            self.add_widget(T(text=f"LEVEL UP!  Level {app.store.level}", font_size=sp(22),
                              color=hexc(GOOD), size_hint_y=None, height=dp(40)))
        for k in new_badges:
            self.add_widget(T(text=f"New badge: {BADGES[k][0]}", font_size=sp(18),
                              color=hexc(GOOD), size_hint_y=None, height=dp(34)))
        self.add_widget(Widget())
        self.add_widget(Btn(text="Menu", bg=CARD, fg=TXT, height=dp(58),
                            on_release=lambda *_: app.home()))


# ------------------------------------------------------------ app
class EnglishAdventure(App):
    title = "English Adventure"

    def build(self):
        Window.clearcolor = hexc(BG)
        if platform not in ("android", "ios"):
            Window.size = (400, 780)
        self.store = Store(os.path.join(self.user_data_dir, "progress.json"))
        self.sfx = Sfx(self.store)
        self.lessons = load_lessons()
        self.lesson = self.lessons[0]
        self.root_box = BoxLayout()
        Window.bind(on_keyboard=self.on_key)
        self.home()
        return self.root_box

    def show(self, widget):
        self.root_box.clear_widgets()
        self.root_box.add_widget(widget)

    def home(self):
        self.store.save()
        self.show(Home(self))

    def on_key(self, window, key, *args):
        if key == 27:  # Android back button
            if isinstance(self.root_box.children[0], Home):
                return False
            self.home()
            return True
        return False

    def finish(self, title, correct, total, extra=0):
        perfect = correct == total
        xp = correct * 5 + (10 if perfect else 0) + extra
        before = self.store.level
        new = self.store.add_xp(xp, perfect)
        leveled = self.store.level > before
        self.show(Result(self, title, correct, total, xp, new, leveled))
        self.sfx.play("win" if correct / max(1, total) >= 0.6 else "lose")
        if leveled:
            Clock.schedule_once(lambda dt: self.sfx.play("levelup"), 1.4)
        elif new:
            Clock.schedule_once(lambda dt: self.sfx.play("badge"), 1.4)

    def on_pause(self):
        self.store.save()
        return True


if __name__ == "__main__":
    EnglishAdventure().run()
