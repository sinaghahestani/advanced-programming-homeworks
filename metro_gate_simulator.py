import tkinter as tk
import random
import time
import threading
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum, auto


# ── Enums & Data Structures ────────────────────────────────

class GateState(Enum):
    IDLE = auto()
    SCANNING = auto()
    OPENING = auto()
    OPEN = auto()
    CLOSING = auto()
    ALARM = auto()
    EMERGENCY = auto()
    FAULT = auto()


class CardType(Enum):
    REGULAR = "عادی"
    STUDENT = "دانشجویی"
    SENIOR = "سالمند"
    BLOCKED = "مسدود"


@dataclass
class MetroCard:
    card_id: str
    holder_name: str
    card_type: CardType
    balance: float
    entry_log: list = field(default_factory=list)
    is_blocked: bool = False

    def charge(self, amount: float) -> bool:
        if self.balance >= amount and not self.is_blocked:
            self.balance -= amount
            return True
        return False


# ── PID Controller ────────────────────────────────

class PIDController:
    def __init__(self, kp=2.0, ki=0.1, kd=0.5):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.prev_error = 0.0
        self.integral = 0.0

    def compute(self, setpoint: float, measured: float, dt: float = 0.05) -> float:
        error = setpoint - measured
        self.integral += error * dt
        self.integral = max(-20.0, min(20.0, self.integral))
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        self.prev_error = error
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        return max(-100.0, min(100.0, output))

    def reset(self):
        self.prev_error = 0.0
        self.integral = 0.0


# ── Gate Motor ────────────────────────────────

class GateMotor:
    def __init__(self):
        self.position = 0.0
        self.velocity = 0.0
        self.target = 0.0
        self.pid = PIDController()
        self.fault = False

    def update(self, dt: float = 0.05):
        if self.fault:
            return
        control = self.pid.compute(self.target, self.position, dt)
        noise = random.gauss(0, 0.3)
        self.velocity = control * 0.4 + noise
        self.position += self.velocity * dt
        self.position = max(0.0, min(100.0, self.position))

    def open(self):
        self.target = 100.0
        self.pid.reset()

    def close(self):
        self.target = 0.0
        self.pid.reset()

    @property
    def is_open(self) -> bool:
        return self.position >= 95.0

    @property
    def is_closed(self) -> bool:
        return self.position <= 5.0


# ── IR Sensor ────────────────────────────────

class IRSensor:
    def __init__(self):
        self.blocked = False
        self._noise_prob = 0.02

    def update(self, person_passing: bool):
        noise = random.random() < self._noise_prob
        self.blocked = person_passing ^ noise

    @property
    def signal(self) -> float:
        base = 0.2 if self.blocked else 3.3
        return base + random.gauss(0, 0.05)


# ── Sample Cards ────────────────────────────────

SAMPLE_CARDS = {
    "1234567890": MetroCard("1234567890", "علی رضایی", CardType.REGULAR, 5000.0),
    "9876543210": MetroCard("9876543210", "مریم احمدی", CardType.STUDENT, 3000.0),
    "1111111111": MetroCard("1111111111", "حسین موسوی", CardType.SENIOR, 8000.0),
    "0000000000": MetroCard("0000000000", "کارت تست", CardType.BLOCKED, 0.0, is_blocked=True),
}

FARE = {"REGULAR": 5000, "STUDENT": 2500, "SENIOR": 2000}


# ── Main App ────────────────────────────────

class MetroGateSimulator:
    BG = "#0d0d1a"
    PANEL = "#1a1a2e"
    ACCENT = "#7c3aed"
    ACCENT2 = "#a855f7"
    GREEN = "#22c55e"
    RED = "#ef4444"
    YELLOW = "#eab308"
    TEXT = "#e2e8f0"
    SUBTEXT = "#94a3b8"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Metro Gate Simulator — Control Engineering")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)

        self.motor = GateMotor()
        self.ir = IRSensor()
        self.state = GateState.IDLE
        self.person_passing = False
        self.open_timer = 0.0
        self.total_entries = 0
        self.total_revenue = 0
        self.current_card: Optional[MetroCard] = None
        self.running = True
        self.emergency = False
        self.log_lines = []

        self._build_ui()
        self._start_simulation_loop()

    def _panel(self, parent, title: str) -> tk.Frame:
        tk.Label(parent, text=title, font=("Arial", 9, "bold"),
                 bg=self.BG, fg=self.ACCENT2).pack(anchor="w", pady=(8, 2))
        f = tk.Frame(parent, bg=self.PANEL, bd=0, relief="flat",
                     highlightbackground=self.ACCENT, highlightthickness=1)
        f.pack(fill="x", pady=(0, 4))
        return f

    def _build_ui(self):
        self.root.geometry("900x660")

        tk.Label(self.root, text="🚇 Metro Gate Simulator",
                 font=("Arial", 16, "bold"),
                 bg=self.BG, fg=self.ACCENT2).pack(pady=(12, 0))
        tk.Label(self.root, text="Control Engineering — PID Motor Control",
                 font=("Arial", 9), bg=self.BG, fg=self.SUBTEXT).pack()

        main = tk.Frame(self.root, bg=self.BG)
        main.pack(fill="both", expand=True, padx=14, pady=8)

        left = tk.Frame(main, bg=self.BG)
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(main, bg=self.BG, width=280)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        self._build_gate_canvas(left)
        self._build_motor_panel(left)
        self._build_controls(left)
        self._build_card_panel(right)
        self._build_dashboard(right)
        self._build_log(right)

    def _build_gate_canvas(self, parent):
        f = self._panel(parent, "🚪  Gate Visualization")
        self.canvas = tk.Canvas(f, width=380, height=185,
                                bg=self.BG, highlightthickness=0)
        self.canvas.pack(padx=8, pady=8)
        self._draw_gate()

    def _draw_gate(self):
        c = self.canvas
        c.delete("all")
        w, h = 380, 185

        c.create_rectangle(0, h - 30, w, h, fill="#1e1e3a", outline="")

        fc = self.ACCENT
        c.create_rectangle(60, 40, 90, h - 30, fill=fc, outline="")
        c.create_rectangle(290, 40, 320, h - 30, fill=fc, outline="")
        c.create_rectangle(60, 40, 320, 60, fill=fc, outline="")

        pos = self.motor.position / 100.0
        bar_right = int(90 + (290 - 90) * pos)
        bar_color = (self.GREEN if self.motor.is_open else
                     (self.YELLOW if pos > 0.1 else self.RED))
        c.create_rectangle(90, 90, bar_right, 110, fill=bar_color, outline="")

        beam_color = self.RED if self.ir.blocked else "#00ff94"
        c.create_line(90, 135, 290, 135, fill=beam_color, width=2, dash=(4, 3))
        c.create_oval(82, 131, 94, 143, fill=beam_color, outline="")
        c.create_oval(286, 131, 298, 143, fill=beam_color, outline="")

        state_colors = {
            GateState.IDLE: self.SUBTEXT,
            GateState.SCANNING: self.YELLOW,
            GateState.OPENING: self.GREEN,
            GateState.OPEN: self.GREEN,
            GateState.CLOSING: self.YELLOW,
            GateState.ALARM: self.RED,
            GateState.EMERGENCY: self.GREEN,
            GateState.FAULT: self.RED,
        }
        c.create_text(w // 2, 22,
                      text=f"State: {self.state.name}",
                      fill=state_colors.get(self.state, self.TEXT),
                      font=("Arial", 10, "bold"))

        led = (self.GREEN if self.motor.is_open else
               (self.YELLOW if self.motor.position > 5 else self.RED))
        c.create_oval(340, 12, 360, 32, fill=led, outline="")

    def _build_motor_panel(self, parent):
        f = self._panel(parent, "⚙️  Motor & Sensor Signals")
        inner = tk.Frame(f, bg=self.PANEL)
        inner.pack(fill="x", padx=8, pady=6)

        self._bars = {}
        for label, key, color in [
            ("Motor Position", "pos", self.ACCENT2),
            ("Motor Velocity", "vel", self.GREEN),
            ("IR Signal (V)", "ir", self.YELLOW),
        ]:
            row = tk.Frame(inner, bg=self.PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, width=16, anchor="w",
                     bg=self.PANEL, fg=self.TEXT,
                     font=("Arial", 8)).pack(side="left")
            bg_frame = tk.Frame(row, bg="#2d2d4e", height=14, width=180)
            bg_frame.pack(side="left", padx=4)
            bg_frame.pack_propagate(False)
            bar = tk.Frame(bg_frame, bg=color, height=14)
            bar.place(x=0, y=0, height=14, width=0)
            val_lbl = tk.Label(row, text="0.00", width=7, bg=self.PANEL, fg=color,
                               font=("Courier", 8))
            val_lbl.pack(side="left")
            self._bars[key] = (bar, val_lbl)

    def _build_card_panel(self, parent):
        f = self._panel(parent, "💳  Card Scanner")
        inner = tk.Frame(f, bg=self.PANEL)
        inner.pack(fill="x", padx=8, pady=6)

        tk.Label(inner, text="Card ID:", bg=self.PANEL,
                 fg=self.TEXT, font=("Arial", 8)).pack(anchor="w")
        self.card_entry = tk.Entry(inner, font=("Courier", 11),
                                   bg="#2d2d4e", fg=self.ACCENT2,
                                   insertbackground=self.ACCENT2,
                                   relief="flat", bd=4)
        self.card_entry.pack(fill="x", pady=(2, 6))
        self.card_entry.insert(0, "1234567890")

        btn_row = tk.Frame(inner, bg=self.PANEL)
        btn_row.pack(fill="x")
        for txt, cmd in [("Scan Card", self._scan_card),
                         ("Random", self._random_card)]:
            tk.Button(btn_row, text=txt, command=cmd,
                      bg=self.ACCENT, fg="white",
                      font=("Arial", 8, "bold"),
                      relief="flat", bd=0, cursor="hand2",
                      activebackground=self.ACCENT2,
                      padx=8, pady=4).pack(side="left", padx=(0, 4))

        self.card_info = tk.Label(inner, text="—",
                                  bg=self.PANEL, fg=self.SUBTEXT,
                                  font=("Arial", 8),
                                  wraplength=240, justify="left")
        self.card_info.pack(anchor="w", pady=(6, 0))

    def _build_dashboard(self, parent):
        f = self._panel(parent, "📊  Dashboard")
        inner = tk.Frame(f, bg=self.PANEL)
        inner.pack(fill="x", padx=8, pady=6)

        self.dash_entries = tk.Label(inner, text="Entries: 0",
                                      bg=self.PANEL, fg=self.GREEN,
                                      font=("Arial", 9, "bold"))
        self.dash_revenue = tk.Label(inner, text="Revenue: 0 ﷼",
                                      bg=self.PANEL, fg=self.ACCENT2,
                                      font=("Arial", 9, "bold"))
        self.dash_state = tk.Label(inner, text="State: IDLE",
                                    bg=self.PANEL, fg=self.TEXT,
                                    font=("Arial", 9))
        for w in (self.dash_entries, self.dash_revenue, self.dash_state):
            w.pack(anchor="w", pady=1)

    def _build_log(self, parent):
        tk.Label(parent, text="📋  Event Log",
                 font=("Arial", 9, "bold"),
                 bg=self.BG, fg=self.ACCENT2).pack(anchor="w", pady=(8, 2))
        log_frame = tk.Frame(parent, bg=self.PANEL,
                             highlightbackground=self.ACCENT,
                             highlightthickness=1)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, bg=self.BG, fg=self.SUBTEXT,
                                font=("Courier", 7), relief="flat",
                                state="disabled", wrap="word", height=12)
        sb = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_controls(self, parent):
        f = self._panel(parent, "🎛️  Manual Controls")
        inner = tk.Frame(f, bg=self.PANEL)
        inner.pack(fill="x", padx=8, pady=6)

        buttons = [
            ("Open Gate", self.ACCENT, self._manual_open),
            ("Close Gate", "#dc2626", self._manual_close),
            ("🚨 Emergency", self.YELLOW, self._toggle_emergency),
            ("Simulate Person", self.GREEN, self._sim_person),
            ("Inject Fault", "#6b7280", self._inject_fault),
            ("Clear Fault", "#0891b2", self._clear_fault),
        ]
        for i, (txt, color, cmd) in enumerate(buttons):
            tk.Button(inner, text=txt, command=cmd,
                      bg=color, fg="white",
                      font=("Arial", 8, "bold"),
                      relief="flat", bd=0, cursor="hand2",
                      activebackground=self.ACCENT2,
                      padx=6, pady=4).grid(row=i // 3, column=i % 3,
                                           padx=3, pady=3, sticky="ew")
        inner.columnconfigure((0, 1, 2), weight=1)

    def _log(self, msg: str, color: str = None):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.log_lines.append(line)
        self.log_text.configure(state="normal")
        tag = f"c{len(self.log_lines)}"
        self.log_text.insert("end", line, tag)
        if color:
            self.log_text.tag_configure(tag, foreground=color)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _scan_card(self):
        self._process_card(self.card_entry.get().strip())

    def _random_card(self):
        card_id = random.choice(list(SAMPLE_CARDS.keys()))
        self.card_entry.delete(0, "end")
        self.card_entry.insert(0, card_id)
        self._process_card(card_id)

    def _process_card(self, card_id: str):
        if self.state == GateState.FAULT:
            self._log("⚠️ System fault — cannot scan", self.RED)
            return
        if self.emergency:
            self._log("🚨 Emergency mode active", self.YELLOW)
            return
        if self.state in (GateState.SCANNING, GateState.OPENING, GateState.OPEN):
            self._log("⏳ Gate busy", self.YELLOW)
            return

        self.state = GateState.SCANNING
        self._log(f"📡 Scanning: {card_id}", self.ACCENT2)

        def delayed_check():
            time.sleep(0.6)
            card = SAMPLE_CARDS.get(card_id)
            if not card:
                self.root.after(0, lambda: self._deny("❌ Card not found"))
                return
            if card.is_blocked:
                self.root.after(0, lambda: self._deny(f"🚫 Card blocked: {card.holder_name}"))
                return
            fare = FARE.get(card.card_type.name, 5000)
            if not card.charge(fare):
                self.root.after(0, lambda: self._deny(f"💸 Insufficient balance ({card.holder_name})"))
                return
            card.entry_log.append(datetime.now().isoformat())
            self.total_entries += 1
            self.total_revenue += fare
            self.root.after(0, lambda: self._allow(card, fare))

        threading.Thread(target=delayed_check, daemon=True).start()

    def _allow(self, card: MetroCard, fare: int):
        info = (f"✅ {card.holder_name} | {card.card_type.value}\n"
                f"   کسر: {fare:,} ﷼ | موجودی: {card.balance:,.0f} ﷼")
        self.card_info.configure(text=info, fg=self.GREEN)
        self._log(f"✅ {card.holder_name} (-{fare:,} ﷼)", self.GREEN)
        self.state = GateState.OPENING
        self.motor.open()
        self.open_timer = 4.0

    def _deny(self, reason: str):
        self.card_info.configure(text=reason, fg=self.RED)
        self._log(reason, self.RED)
        self.state = GateState.ALARM
        self.root.after(1500, self._reset_to_idle)

    def _reset_to_idle(self):
        if self.state == GateState.ALARM:
            self.state = GateState.IDLE

    def _manual_open(self):
        self.state = GateState.OPENING
        self.motor.open()
        self.open_timer = 5.0
        self._log("🔓 Manual open", self.YELLOW)

    def _manual_close(self):
        self.state = GateState.CLOSING
        self.motor.close()
        self._log("🔒 Manual close", self.RED)

    def _toggle_emergency(self):
        self.emergency = not self.emergency
        if self.emergency:
            self.state = GateState.EMERGENCY
            self.motor.open()
            self._log("🚨 EMERGENCY — all gates open!", self.YELLOW)
        else:
            self.state = GateState.IDLE
            self.motor.close()
            self._log("✅ Emergency cleared", self.GREEN)

    def _sim_person(self):
        self.person_passing = True
        self._log("🚶 Person passing…", self.SUBTEXT)
        self.root.after(2000, self._person_done)

    def _person_done(self):
        self.person_passing = False

    def _inject_fault(self):
        self.motor.fault = True
        self.state = GateState.FAULT
        self._log("⚡ Motor fault injected!", self.RED)

    def _clear_fault(self):
        self.motor.fault = False
        self.state = GateState.IDLE
        self._log("🔧 Fault cleared", self.GREEN)

    def _start_simulation_loop(self):
        self._sim_step()

    def _sim_step(self):
        if not self.running:
            return

        dt = 0.05
        self.motor.update(dt)
        self.ir.update(self.person_passing)

        if self.state == GateState.OPENING and self.motor.is_open:
            self.state = GateState.OPEN

        if self.state == GateState.OPEN:
            self.open_timer -= dt
            if self.open_timer <= 0 and not self.ir.blocked:
                self.state = GateState.CLOSING
                self.motor.close()

        if self.state == GateState.CLOSING and self.motor.is_closed:
            self.state = GateState.IDLE

        self._draw_gate()
        self._update_motor_bars()
        self._update_dashboard()

        self.root.after(50, self._sim_step)

    def _update_motor_bars(self):
        pos = self.motor.position
        vel = max(0.0, self.motor.velocity * 5)
        ir_v = min(self.ir.signal, 3.5)

        data = [
            ("pos", pos, 100.0, f"{pos:.1f}%"),
            ("vel", vel, 100.0, f"{self.motor.velocity:+.2f}"),
            ("ir", ir_v / 3.5 * 100, 100.0, f"{ir_v:.2f}V"),
        ]
        for key, val, mx, txt in data:
            bar, lbl = self._bars[key]
            bar.place(x=0, y=0, height=14,
                      width=int(180 * min(val, mx) / mx))
            lbl.configure(text=txt)

    def _update_dashboard(self):
        self.dash_entries.configure(text=f"Entries: {self.total_entries}")
        self.dash_revenue.configure(text=f"Revenue: {self.total_revenue:,} ﷼")
        self.dash_state.configure(text=f"State: {self.state.name}")

    def on_close(self):
        self.running = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = MetroGateSimulator(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
