import tkinter as tk
from tkinter import ttk
import threading
import time
import ctypes
import ctypes.wintypes
import keyboard

# === METHODE LA PLUS RAPIDE : SendInput Windows direct (bypass pyautogui) ===
MOUSEEVENTF_LEFTDOWN   = 0x0002
MOUSEEVENTF_LEFTUP     = 0x0004
MOUSEEVENTF_RIGHTDOWN  = 0x0008
MOUSEEVENTF_RIGHTUP    = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP   = 0x0040
INPUT_MOUSE = 0

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.wintypes.DWORD),
                ("dwFlags", ctypes.wintypes.DWORD),
                ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.wintypes.DWORD), ("union", INPUT_UNION)]

def _send_click(down_flag, up_flag):
    inputs = (INPUT * 2)(
        INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=MOUSEINPUT(dwFlags=down_flag))),
        INPUT(type=INPUT_MOUSE, union=INPUT_UNION(mi=MOUSEINPUT(dwFlags=up_flag))),
    )
    ctypes.windll.user32.SendInput(2, inputs, ctypes.sizeof(INPUT))

CLICK_MAP = {
    "Gauche":  (MOUSEEVENTF_LEFTDOWN,   MOUSEEVENTF_LEFTUP),
    "Droit":   (MOUSEEVENTF_RIGHTDOWN,  MOUSEEVENTF_RIGHTUP),
    "Milieu":  (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("AutoClicker Pro")
        self.root.geometry("420x560")
        self.root.resizable(False, False)
        self.root.configure(bg="#0D0D0F")

        self.clicking = False
        self.click_thread = None
        self.click_count = 0

        self._setup_styles()
        self._build_ui()
        self._bind_hotkey()

    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            "Custom.TCombobox",
            fieldbackground="#1A1A1F",
            background="#1A1A1F",
            foreground="#E8E8F0",
            bordercolor="#2A2A35",
            arrowcolor="#7C6FF0",
            selectbackground="#2A2A35",
            selectforeground="#E8E8F0",
        )
        self.style.map("Custom.TCombobox",
            fieldbackground=[("readonly", "#1A1A1F")],
            foreground=[("readonly", "#E8E8F0")],
        )

    def _build_ui(self):
        canvas = tk.Canvas(self.root, bg="#0D0D0F", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        canvas.create_text(210, 38, text="AUTO", font=("Segoe UI", 28, "bold"),
                           fill="#7C6FF0", anchor="center")
        canvas.create_text(210, 64, text="CLICKER", font=("Segoe UI", 10, "bold"),
                           fill="#4A4A5A", anchor="center")
        canvas.create_text(210, 82, text="▪  ▪  ▪", font=("Segoe UI", 8),
                           fill="#2A2A3A", anchor="center")

        self._section_label(canvas, 108, "INTERVALLE DE CLIC  (0 = TURBO MAX)")
        frame_interval = tk.Frame(self.root, bg="#1A1A1F", bd=0)
        canvas.create_window(210, 152, window=frame_interval, width=360, height=56)
        self._draw_panel(canvas, 210, 152, 360, 56)

        self.hours_var = tk.StringVar(value="0")
        self.mins_var  = tk.StringVar(value="0")
        self.secs_var  = tk.StringVar(value="0")
        self.ms_var    = tk.StringVar(value="0")

        time_frame = tk.Frame(frame_interval, bg="#1A1A1F")
        time_frame.pack(expand=True)
        for label, var in [("H", self.hours_var), ("M", self.mins_var),
                            ("S", self.secs_var), ("MS", self.ms_var)]:
            col = tk.Frame(time_frame, bg="#1A1A1F")
            col.pack(side="left", padx=8, pady=6)
            entry = tk.Entry(col, textvariable=var, width=4,
                             bg="#0D0D0F", fg="#E8E8F0", insertbackground="#7C6FF0",
                             font=("Consolas", 14, "bold"), bd=0,
                             highlightthickness=1, highlightcolor="#7C6FF0",
                             highlightbackground="#2A2A35", justify="center")
            entry.pack()
            tk.Label(col, text=label, bg="#1A1A1F", fg="#4A4A5A",
                     font=("Segoe UI", 8)).pack()

        self._section_label(canvas, 200, "BOUTON DE SOURIS")
        frame_btn = tk.Frame(self.root, bg="#1A1A1F", bd=0)
        canvas.create_window(210, 244, window=frame_btn, width=360, height=44)
        self._draw_panel(canvas, 210, 244, 360, 44)

        self.mouse_btn_var = tk.StringVar(value="Gauche")
        self.btn_combo = ttk.Combobox(frame_btn, textvariable=self.mouse_btn_var,
                                       values=["Gauche", "Droit", "Milieu"],
                                       state="readonly", width=18,
                                       style="Custom.TCombobox",
                                       font=("Segoe UI", 11))
        self.btn_combo.pack(expand=True, pady=9)

        self._section_label(canvas, 286, "TYPE DE CLIC")
        frame_click = tk.Frame(self.root, bg="#1A1A1F", bd=0)
        canvas.create_window(210, 330, window=frame_click, width=360, height=44)
        self._draw_panel(canvas, 210, 330, 360, 44)

        self.click_type_var = tk.StringVar(value="Simple")
        self.type_combo = ttk.Combobox(frame_click, textvariable=self.click_type_var,
                                        values=["Simple", "Double"],
                                        state="readonly", width=18,
                                        style="Custom.TCombobox",
                                        font=("Segoe UI", 11))
        self.type_combo.pack(expand=True, pady=9)

        self._section_label(canvas, 372, "RÉPÉTITIONS")
        frame_rep = tk.Frame(self.root, bg="#1A1A1F", bd=0)
        canvas.create_window(210, 416, window=frame_rep, width=360, height=44)
        self._draw_panel(canvas, 210, 416, 360, 44)

        self.repeat_var = tk.StringVar(value="∞  Infini")
        self.repeat_combo = ttk.Combobox(frame_rep, textvariable=self.repeat_var,
                                          values=["∞  Infini", "10", "50", "100", "500", "1000"],
                                          state="readonly", width=18,
                                          style="Custom.TCombobox",
                                          font=("Segoe UI", 11))
        self.repeat_combo.pack(expand=True, pady=9)

        self.status_dot  = canvas.create_oval(170, 464, 182, 476, fill="#2A2A3A", outline="")
        self.status_text = canvas.create_text(215, 470, text="EN ATTENTE",
                                               font=("Segoe UI", 9, "bold"),
                                               fill="#4A4A5A", anchor="center")
        self.count_text  = canvas.create_text(340, 470, text="0 clics",
                                               font=("Consolas", 9),
                                               fill="#2A2A3A", anchor="center")
        self.canvas = canvas

        self.start_btn = tk.Button(self.root, text="▶  DÉMARRER",
                                    bg="#7C6FF0", fg="white", activebackground="#9B90F5",
                                    activeforeground="white", bd=0, cursor="hand2",
                                    font=("Segoe UI", 12, "bold"),
                                    command=self.toggle_clicking)
        canvas.create_window(210, 518, window=self.start_btn, width=360, height=48)

        hotkey_frame = tk.Frame(self.root, bg="#0D0D0F")
        canvas.create_window(210, 548, window=hotkey_frame)
        tk.Label(hotkey_frame, text="Touche  ", bg="#0D0D0F",
                 fg="#2A2A3A", font=("Segoe UI", 8)).pack(side="left")
        tk.Label(hotkey_frame, text=" X ", bg="#1A1A1F",
                 fg="#7C6FF0", font=("Consolas", 8, "bold"),
                 padx=4, pady=1).pack(side="left")
        tk.Label(hotkey_frame, text="  pour démarrer / arrêter", bg="#0D0D0F",
                 fg="#2A2A3A", font=("Segoe UI", 8)).pack(side="left")

    def _draw_panel(self, canvas, cx, cy, w, h):
        r = 8
        x1, y1 = cx - w//2, cy - h//2
        x2, y2 = cx + w//2, cy + h//2
        canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90,
                          fill="#1A1A1F", outline="#2A2A35", style="pieslice", width=0.5)
        canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90,
                          fill="#1A1A1F", outline="#2A2A35", style="pieslice", width=0.5)
        canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90,
                          fill="#1A1A1F", outline="#2A2A35", style="pieslice", width=0.5)
        canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90,
                          fill="#1A1A1F", outline="#2A2A35", style="pieslice", width=0.5)
        canvas.create_rectangle(x1+r, y1, x2-r, y2, fill="#1A1A1F", outline="")
        canvas.create_rectangle(x1, y1+r, x2, y2-r, fill="#1A1A1F", outline="")
        canvas.create_line(x1+r, y1, x2-r, y1, fill="#2A2A35", width=0.5)
        canvas.create_line(x1+r, y2, x2-r, y2, fill="#2A2A35", width=0.5)
        canvas.create_line(x1, y1+r, x1, y2-r, fill="#2A2A35", width=0.5)
        canvas.create_line(x2, y1+r, x2, y2-r, fill="#2A2A35", width=0.5)

    def _section_label(self, canvas, y, text):
        canvas.create_text(38, y, text=text, font=("Segoe UI", 7, "bold"),
                           fill="#3A3A4A", anchor="w")
        canvas.create_line(200, y+4, 382, y+4, fill="#1A1A1F", width=0.5)

    def _bind_hotkey(self):
        keyboard.add_hotkey("x", self.toggle_clicking)

    def _get_interval(self):
        try:
            h  = int(self.hours_var.get() or 0)
            m  = int(self.mins_var.get()  or 0)
            s  = int(self.secs_var.get()  or 0)
            ms = int(self.ms_var.get()    or 0)
            return h * 3600 + m * 60 + s + ms / 1000.0
        except ValueError:
            return 0

    def _get_max_clicks(self):
        val = self.repeat_var.get()
        if "Infini" in val or "∞" in val:
            return None
        try:
            return int(val)
        except ValueError:
            return None

    def toggle_clicking(self):
        if self.clicking:
            self.stop_clicking()
        else:
            self.start_clicking()

    def start_clicking(self):
        self.clicking = True
        self.click_count = 0
        self.root.after(0, self._update_ui_running)
        self.click_thread = threading.Thread(target=self._click_loop, daemon=True)
        self.click_thread.start()

    def stop_clicking(self):
        self.clicking = False
        self.root.after(0, self._update_ui_stopped)

    def _click_loop(self):
        interval   = self._get_interval()
        btn_name   = self.mouse_btn_var.get()
        click_type = self.click_type_var.get()
        max_clicks = self._get_max_clicks()
        double     = click_type == "Double"
        down_flag, up_flag = CLICK_MAP.get(btn_name, CLICK_MAP["Gauche"])

        # Mise a jour UI toutes les 100 clics pour ne pas ralentir la boucle
        update_every = 100
        last_ui = 0

        while self.clicking:
            _send_click(down_flag, up_flag)
            if double:
                _send_click(down_flag, up_flag)

            self.click_count += 1

            if self.click_count - last_ui >= update_every:
                last_ui = self.click_count
                self.root.after(0, self._update_count)

            if max_clicks and self.click_count >= max_clicks:
                self.root.after(0, self.stop_clicking)
                break

            # Si intervalle = 0 : aucun sleep => vitesse maximale
            if interval > 0:
                time.sleep(interval)

    def _update_ui_running(self):
        self.canvas.itemconfig(self.status_dot,  fill="#7C6FF0")
        self.canvas.itemconfig(self.status_text, text="EN COURS", fill="#7C6FF0")
        self.start_btn.config(text="■  ARRÊTER", bg="#3A2A6A", activebackground="#4A3A7A")

    def _update_ui_stopped(self):
        self.root.after(0, self._update_count)
        self.canvas.itemconfig(self.status_dot,  fill="#2A4A2A")
        self.canvas.itemconfig(self.status_text, text="ARRÊTÉ", fill="#3A8A3A")
        self.start_btn.config(text="▶  DÉMARRER", bg="#7C6FF0", activebackground="#9B90F5")

    def _update_count(self):
        txt = f"{self.click_count:,} clics".replace(",", " ")
        self.canvas.itemconfig(self.count_text, text=txt, fill="#4A4A6A")

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClicker(root)
    root.mainloop()
