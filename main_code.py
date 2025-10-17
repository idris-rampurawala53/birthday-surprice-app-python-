
"""
Birthday Surprise App — single-file Tkinter app

Features
- Welcome screen with her name input and a secret start button
- Confetti + heart animation
- Typewriter birthday message
- Memories gallery (loads PNG/GIF images from ./assets/images)
- Cute quiz
- A heartfelt letter page
- Optional music (loads ./assets/music/song.mp3 if pygame is available)

How to use
1) Put your images (PNG or GIF) in ./assets/images next to this file.
2) (Optional) Put an MP3 at ./assets/music/song.mp3 for background music.
3) Run: python birthday_surprise.py

No external dependencies required. If Pillow is installed, JPG/JPEG images will also work.
Tested on Python 3.10+ with the standard library.
"""

import os
import sys
import math
import random
import time
import threading
import functools 
import tkinter as tk
import datetime as dt

from tkinter import ttk, messagebox

# Optional imports: Pillow for JPEG support; pygame for music
PIL_AVAILABLE = False
try:
    from PIL import Image, ImageTk  # type: ignore
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

PYGAME_AVAILABLE = False
try:
    import pygame  # type: ignore
    PYGAME_AVAILABLE = True
except Exception:
    PYGAME_AVAILABLE = False

APP_TITLE = "Happy Birthday 💖"
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
IMG_DIR = os.path.join(ASSETS_DIR, "images")
MUSIC_FILE = os.path.join(ASSETS_DIR, "music", "song.mp3")

# ----------------------------- Utility -----------------------------------

def resource_path(path: str) -> str:
    """Return absolute path, works with PyInstaller onefile bundles too."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, path)  # type: ignore[attr-defined]
    return path

# ----------------------------- Media Loader -------------------------------

class ImageLoader:
    def __init__(self, max_w=720, max_h=480):
        self.cache = {}
        self.max_w = max_w
        self.max_h = max_h

    def _load_with_pillow(self, path):
        img = Image.open(path)
        img.thumbnail((self.max_w, self.max_h), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)

    def _load_with_tk(self, path):
        # Tk's PhotoImage supports GIF/PNG. JPG will fail without Pillow.
        img = tk.PhotoImage(file=path)
        # Simple downscale via subsample if very large
        w, h = img.width(), img.height()
        scale = max(w / self.max_w, h / self.max_h, 1)
        if scale > 1:
            # subsample takes integers; round up
            k = int(math.ceil(scale))
            img = img.subsample(k, k)
        return img

    def load(self, path):
        path = os.path.abspath(path)
        if path in self.cache:
            return self.cache[path]
        try:
            if PIL_AVAILABLE:
                ph = self._load_with_pillow(path)
            else:
                ph = self._load_with_tk(path)
        except Exception as e:
            print(f"[ImageLoader] Failed to load {path}: {e}")
            return None
        self.cache[path] = ph
        return ph

    def list_images(self):
        if not os.path.isdir(IMG_DIR):
            return []
        exts = [".png", ".gif", ".jpg", ".jpeg"] if PIL_AVAILABLE else [".png", ".gif"]
        files = [os.path.join(IMG_DIR, f) for f in os.listdir(IMG_DIR)
                 if os.path.splitext(f.lower())[1] in exts]
        files.sort()
        return files

# ----------------------------- Music --------------------------------------

class MusicPlayer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.ready = False
        self.playing = False
        if PYGAME_AVAILABLE and os.path.isfile(self.file_path):
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(self.file_path)
                self.ready = True
            except Exception as e:
                print(f"[Music] Error initializing: {e}")
                self.ready = False

    def play_loop(self):
        if self.ready:
            try:
                pygame.mixer.music.stop()
                
                pygame.mixer.music.play(-1)
                self.playing = True
                print("[Music] started looping")
            except Exception as e:
                print(f"[Music] play error: {e}")

    def stop(self):
        if self.ready:
            try:
                pygame.mixer.music.stop()
                self.playing = False
            except Exception as e:
                print(f"[Music] stop error: {e}")

# ----------------------------- Confetti -----------------------------------

class Confetti:
    COLORS = [
        "#ff4d6d", "#fca311", "#48bfe3", "#64dfdf", "#80ed99",
        "#b5179e", "#ffd166", "#06d6a0", "#ef476f", "#118ab2"
    ]

    def __init__(self, canvas: tk.Canvas, width: int, height: int, count=120):
        self.canvas = canvas
        self.w = width
        self.h = height
        self.pieces = []
        for _ in range(count):
            x = random.randint(0, self.w)
            y = random.randint(-self.h, 0)
            r = random.randint(3, 7)
            color = random.choice(self.COLORS)
            shape = canvas.create_oval(x, y, x + r, y + r, fill=color, width=0 , tags="confetti")
            speed = random.uniform(1.5, 4.0)
            drift = random.uniform(-1.0, 1.0)
            self.pieces.append((shape, speed, drift))

    def step(self):
        for i, (shape, speed, drift) in enumerate(self.pieces):
            self.canvas.move(shape, drift, speed)
            x1, y1, x2, y2 = self.canvas.coords(shape)
            if y1 > self.h:
                # respawn at top
                dx = random.randint(0, self.w) - x1
                self.canvas.move(shape, dx, -self.h - (y2 - y1))

# ----------------------------- Heart --------------------------------------

def heart_points(cx, cy, size, steps=80):
    pts = []
    for t in [i * (2*math.pi/steps) for i in range(steps)]:
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t)
        x *= size / 32
        y *= size / 32
        pts.append((cx + x, cy - y))
    return pts

# ----------------------------- App ----------------------------------------

class BirthdayApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x650")
        self.minsize(820, 580)
        self.configure(bg="#fff7fb")
        self.iconify_if_windows()

        self.loader = ImageLoader()
        self.music = MusicPlayer(MUSIC_FILE)
        self.music_playing = False


        self._her_name = tk.StringVar(value="")

        self.dates_frame = None
        self.dates_labels = []


        # Build UI
        self._build_welcome()

    def toggle_music(self):
        if not hasattr(self, "music_playing"):
            self.music_playing = False  # initialize state on first call

        if self.music_playing:
            print("[Music] toggling OFF")
            self.music.stop()
            
        else:
            print("[Music] toggling ON")
            self.music.play_loop()
           


    def iconify_if_windows(self):
        try:
            if sys.platform.startswith("win"):
                # Keeps the default icon small and cute
                pass
        except Exception:
            pass

    

    # --------------------- Screens ---------------------
    def _build_welcome(self):
        self.welcome = tk.Frame(self, bg="#fff7fb")
        self.welcome.pack(fill=tk.BOTH, expand=True)

        title = tk.Label(self.welcome, text="A little surprise for you",
                         font=("Segoe UI", 28, "bold"), bg="#fff7fb")
        title.pack(pady=(40, 10))

        subtitle = tk.Label(self.welcome, text="(Hey, can you type your name?)",
                             font=("Segoe UI", 14), bg="#fff7fb")
        subtitle.pack(pady=(0, 20))

        # Left balloons
        left_canvas = tk.Canvas(self.welcome, width=120, height=500, bg="#fff7fb", highlightthickness=0)
        left_canvas.pack(side="left", fill="y")
        self.animate_balloons(left_canvas, ["red", "blue", "green", "yellow", "pink", "purple"])

        # Right balloons
        right_canvas = tk.Canvas(self.welcome, width=120, height=500, bg="#fff7fb", highlightthickness=0)
        right_canvas.pack(side="right", fill="y")
        self.animate_balloons(right_canvas, ["orange", "violet", "skyblue", "lime", "gold", "magenta"])


        entry = ttk.Entry(self.welcome, textvariable=self._her_name, width=30)
        entry.pack()
        entry.focus_set()

        self.error_lbl = tk.Label(self.welcome, text="", font=("Segoe UI", 11),
                          fg="red", bg="#fff7fb")
        self.error_lbl.pack(pady=(6, 0))


        start_btn = ttk.Button(self.welcome, text="Open Surprise 🎁", command=self._start)
        start_btn.pack(pady=24)
        # animated background for welcome screen
        colors = ["#fce1f5", "#d7c4f3", "#c4e3f3", "#c4f3e1", "#f3f3c4", "#f3c4c4"]
        self.animate_bg(self.welcome, colors, delay=5000)


        # Cute hint at bottom
        hint = tk.Label(self.welcome, text="Psst… increase volume if music starts 🎶",
                        font=("Segoe UI", 10), bg="#fff7fb", fg="#b5179e")
        hint.pack(side=tk.BOTTOM, pady=16)

    def animate_bg(self, widget, colors, delay=80):
        """Cycle background colors for a widget to create a gradient effect."""
        def loop(index=0):
            widget.configure(bg=colors[index])
            for child in widget.winfo_children():
                try:
                    child.configure(bg=colors[index])
                except:
                    pass
            self.after(delay, loop, (index + 1) % len(colors))
        loop()

    def animate_balloons(self, canvas, colors):
        """Animate balloons floating upwards."""
        balloons = []
        for i, color in enumerate(colors):
            x = 30 if i % 2 == 0 else 70
            y = 400 + i * 60
            b = canvas.create_oval(x, y, x+40, y+50, fill=color, outline=color)
            s = canvas.create_line(x+20, y+50, x+20, y+70, fill="black")
            balloons.append((b, s))

        def float_up():
            for b, s in balloons:
                canvas.move(b, 0, -1)
                canvas.move(s, 0, -1)
                y = canvas.coords(b)[1]
                if y < -60:  # reset if balloon goes off screen
                    dy = 500
                    canvas.move(b, 0, dy)
                    canvas.move(s, 0, dy)
            self.after(50, float_up)

        float_up()



    def _start(self):
        name = self._her_name.get().strip().lower()
        if not name:
            messagebox.showinfo("One small thing", "Please type your name ✨")
            return

        if name != "her_name":     #you can her name/nickname as password
            self.error_lbl.configure(text="try typing her_name hehe")   #cant login if name notmatch
            return

        # If correct → continue
        self.welcome.destroy()
        self._build_main("her_name")  # show Rasmalai as name
        threading.Thread(target=self.music.play_loop, daemon=True).start()


    def _build_main(self, name: str):
        topbar = tk.Frame(self, bg="#fff7fb")
        topbar.pack(fill=tk.X)
        greeting = tk.Label(topbar, text=f"Hellooo , {name}!",
                            font=("Segoe UI", 22, "bold"), bg="#fff7fb", fg="#b5179e")
        greeting.pack(pady=10)

        # Notebook
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill=tk.BOTH, expand=True)

        self._build_home_tab()
        self._build_memories_tab()
        self._build_quiz_tab(name)
        self._build_compliment_tab()
       

    # --------------------- Tabs ---------------------
    def _build_home_tab(self):
        self.home = tk.Frame(self.tabs, bg="#fff7fb")
        self.tabs.add(self.home, text="Home 💝")

        # Canvas animation area
        self.canvas = tk.Canvas(self.home, bg="#fff7fb", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Controls area
        ctrl = tk.Frame(self.home, bg="#fff7fb")
        ctrl.pack(fill=tk.X)

        self.msg_lbl = tk.Label(ctrl, text="Click the button to start the magic ✨",
                                font=("Segoe UI", 14), bg="#fff7fb")
        self.msg_lbl.pack(pady=8)

        btns = tk.Frame(ctrl, bg="#fff7fb")
        btns.pack(pady=(0, 10))

        ttk.Button(btns, text="Confetti! 🎉", command=self.start_confetti).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Draw Heart ❤️", command=self.draw_beating_heart).grid(row=0, column=1, padx=6)
        ttk.Button(btns, text="Show Dates 📅", command=self.toggle_dates_section).grid(row=0, column=2, padx=6)

        ttk.Button(btns, text="Toggle Music", command=self.music.stop).grid(row=0, column=3, padx=6)
        
        self.confetti = None
        self.animating = False
        self.heart_item = None

        # Resize handling
        self.home.bind("<Configure>", self._on_home_resize)

    def _on_home_resize(self, _evt=None):
        # Clear drawings on resize to keep it neat
        if hasattr(self, 'canvas'):
            self.canvas.delete("all")

    def start_confetti(self):
         # Toggle confetti
        if hasattr(self, "confetti_on") and self.confetti_on:
            # Turn off
            self.confetti_on = False
            self.animating = False
            self.canvas.delete("confetti")
            self.confetti = None
            return

    # Turn on
        self.confetti_on = True
        self.canvas.delete("confetti")
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 500
        self.confetti = Confetti(self.canvas, w, h, count=160)
        self.animating = True
        self._animate_confetti()

    def _animate_confetti(self):
        if not self.animating or not self.confetti_on or not self.confetti:
            return
        self.confetti.step()
        self.after(16, self._animate_confetti)  # ~60 FPS

    def draw_beating_heart(self):
        # if heart is already showing → stop and remove it
        if hasattr(self, "animating") and self.animating:
            self.animating = False
            self.canvas.delete("heart")  # remove drawn heart
            return
        # Create a separate canvas only for the heart
        
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 500
        cx, cy = w // 2, h // 2
        base = min(w, h) * 0.35

        self.animating = True

        def beat(scale=1.0, growing=True):
            if not self.animating:
                return
            # delete only heart items, leave confetti/messages intact
            self.canvas.delete("heart")

            pts = heart_points(cx, cy, base * scale, steps=160)
            for i in range(len(pts)):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % len(pts)]
                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill="#ff4d6d",
                    width=3,
                    smooth=True,
                    tags="heart"   # mark all heart parts with tag
                )

            next_scale = scale + (0.02 if growing else -0.02)
            if next_scale > 1.08:
                growing = False
            if next_scale < 0.92:
                growing = True

            self.after(50, lambda: beat(next_scale, growing))

        beat(1.0, True)



    
    def toggle_dates_section(self):
         # Create the attribute the first time
        if not hasattr(self, "dates_frame"):
            self.dates_frame = None

        if self.dates_frame and self.dates_frame.winfo_exists():
            # If it already exists → destroy it (hide)
            self.dates_frame.destroy()
            self.dates_frame = None
            self.dates_labels = []
        else:
            # Otherwise create it
            self.create_dates_section(self.home)

    def create_dates_section(self, parent):
        # Frame for dates
        self.dates_frame = tk.Frame(parent, bg="#fff7fb")
        dates_frame = self.dates_frame
        dates_frame.pack(pady=10)

        # Label header
        tk.Label(
            dates_frame,
            text="✨ Important Dates ✨",
            font=("Segoe UI", 14, "bold"),
            bg="#fff7fb"
        ).pack()

        self.dates_labels = []

        # List of important dates (month, day, label)
        self.important_dates = [     #add your own dates
            ((1, 20), "My Birthday 🎂"),    
            ((8, 23), "her Birthday 💖"),
            ((5, 22), "Anniversary 💍")
        ]

        # Create labels for each date
        for (_m, _d), title in self.important_dates:
            lbl = tk.Label(dates_frame, text="", font=("Segoe UI", 12), bg="#fff7fb")
            lbl.pack()
            self.dates_labels.append((lbl, _m, _d, title))

        # Start updating daily
        self.update_dates_countdown()

    def update_dates_countdown(self):
        today = dt.date.today()
        for lbl, m, d, title in self.dates_labels:
            event_date = dt.date(today.year, m, d)
            if event_date < today:  # if passed, use next year
                event_date = dt.date(today.year + 1, m, d)

            days_left = (event_date - today).days
            lbl.config(text=f"{title}: {days_left} days left")

        # Check again tomorrow
        self.after(24 * 60 * 60 * 1000, self.update_dates_countdown)


    def _build_memories_tab(self):
        self.mem = tk.Frame(self.tabs, bg="#fff7fb")
        self.tabs.add(self.mem, text="Memories 📸")

        self.gallery_img_label = tk.Label(self.mem, bg="#fff7fb")
        self.gallery_img_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        controls = tk.Frame(self.mem, bg="#fff7fb")
        controls.pack(pady=6)
        ttk.Button(controls, text="⟵ Previous", command=self.show_prev).grid(row=0, column=0, padx=6)
        ttk.Button(controls, text="Next ⟶", command=self.show_next).grid(row=0, column=1, padx=6)
        ttk.Button(controls, text="Shuffle 🔀", command=self.shuffle_gallery).grid(row=0, column=2, padx=6)

        self.images = self.loader.list_images()
        if not self.images:
            msg = tk.Label(self.gallery_img_label, text=(
                "Add your pictures in ./assets/images (PNG/GIF).\n"
                "If you have Pillow installed, JPG/JPEG will also work."
            ), font=("Segoe UI", 13), bg="#fff7fb")
            msg.pack(pady=40)
        self.cur_idx = 0
        self._show_current()

    def _show_current(self):
        if not self.images:
            return
        path = self.images[self.cur_idx]
        ph = self.loader.load(path)
        if ph is None:
            return
        self.gallery_img_label.configure(image=ph)
        self.gallery_img_label.image = ph  # keep reference

    def show_prev(self):
        if not self.images:
            return
        self.cur_idx = (self.cur_idx - 1) % len(self.images)
        self._show_current()

    def show_next(self):
        if not self.images:
            return
        self.cur_idx = (self.cur_idx + 1) % len(self.images)
        self._show_current()

    def shuffle_gallery(self):
        if not self.images:
            return
        random.shuffle(self.images)
        self.cur_idx = 0
        self._show_current()

    def _build_quiz_tab(self, name: str):
        self.quiz = tk.Frame(self.tabs, bg="#fff7fb")
        self.tabs.add(self.quiz, text="Cute game 🧠✨")

        # Container frame for centering
        game_frame = tk.Frame(self.quiz, bg="#fff7fb")
        game_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Words to use in the game
        words = ["nickname1", "nickname2", "nickname3", "nickname4", "nickname5", "nickname6"]  #add nickname for cute game
        self.game_words = words * 2
        random.shuffle(self.game_words)

        self.buttons = []
        self.flipped = []
        self.matched = []

        rows, cols = 3, 4
        for i in range(rows):
            for j in range(cols):
                index = i * cols + j
                btn = tk.Button(game_frame, text="❓", width=12, height=3,
                            font=("Segoe UI", 11, "bold"),
                            bg="#ffe6f2", fg="#ff4d6d", relief="raised",
                            command=lambda idx=index: self.flip_card(idx))
                btn.grid(row=i, column=j, padx=8, pady=8)
                self.buttons.append(btn)
    def flip_card(self, index):
        if index in self.matched or index in self.flipped:
            return

        btn = self.buttons[index]
        btn.config(text=self.game_words[index], state="disabled")
        self.flipped.append(index)

        if len(self.flipped) == 2:
            i1, i2 = self.flipped
            if self.game_words[i1] == self.game_words[i2]:
                self.matched.extend([i1, i2])
                self.flipped = []
                if len(self.matched) == len(self.game_words):
                    self.show_win_message()
            else:
                self.after(800, self.flip_back)

    def flip_back(self):
        for i in self.flipped:
            btn = self.buttons[i]
            btn.config(text="❓", state="normal")
        self.flipped = []

    def show_win_message(self):
        win_label = tk.Label(self.quiz, text="You found all my love words! 💕",
                            font=("Segoe UI", 14, "bold"),
                            bg="#fff7fb", fg="#ff4d6d")
        win_label.place(relx=0.5, rely=0.9, anchor="center")

    import random

    def _build_compliment_tab(self):
        self.compliment_tab = tk.Frame(self.tabs, bg="#fff7fb")
        self.tabs.add(self.compliment_tab, text="Compliment Generator 🌸")

        # Title
        tk.Label(
            self.compliment_tab,
            text="🌸 Compliment Generator For her 🌸",
            font=("Segoe UI", 14, "bold"),
            bg="#fff7fb",
            fg="#d63384"
        ).pack(pady=15)

        # Label for compliment display
        self.compliment_label = tk.Label(
            self.compliment_tab,
            text="Click the button for a surprise 💕",
            font=("Segoe UI", 12),
            bg="#fff7fb",
            fg="#444"
        )
        self.compliment_label.pack(pady=10)

        # Button to generate compliment
        tk.Button(
            self.compliment_tab,
            text="Give her a compliment 💝",
            command=self.generate_compliment,
            font=("Segoe UI", 11),
            bg="white",
            relief="solid",
            borderwidth=1
        ).pack(pady=10)

    def generate_compliment(self):
        compliments = [
            
            #here add compliment for her that gets generated randomly with double quote

            
        ]
        self.compliment_label.config(text=random.choice(compliments))


    # --------------------- App shutdown ---------------------
    def on_close(self):
        self.animating = False
        try:
            self.music.stop()
        except Exception:
            pass
        self.destroy()

# ----------------------------- Main ---------------------------------------

def main():
    app = BirthdayApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

if __name__ == "__main__":
    main()

