import tkinter as tk
import numpy as np
import json
import os

# ── Constants ──────────────────────────────────
G = 9.81
DT = 0.02

# ── Colors ─────────────────────────────────────
BG = "#0d0d1a"
PANEL = "#1a1a2e"
ACCENT = "#7b2fff"
ACCENT2 = "#a855f7"
TEXT = "#e2d9f3"
WARN = "#ff4c4c"
GREEN = "#4ade80"
GRID = "#2a2a3e"
TRACK = "#3a3a5c"
CART_C = "#7b2fff"
POLE_OK = "#a855f7"
POLE_WARN = "#facc15"
POLE_FALL = "#ff4c4c"
WHEEL = "#555577"

# ──────────────────────────────────────────────
# PHYSICS CLASSES
# ──────────────────────────────────────────────

class Pendulum:
    def __init__(self, mass=0.1, length=1.0, noise_std=0.0):
        self.mass = mass
        self.length = length
        self.noise_std = noise_std
        self.theta = 0.0
        self.theta_dot = 0.0
        
    def reset(self, noise_std=None):
        if noise_std is not None:
            self.noise_std = noise_std
        self.theta = np.random.uniform(-0.05, 0.05)
        self.theta_dot = 0.0
    
    @property
    def measured_theta(self):
        return self.theta + np.random.normal(0, self.noise_std)
    
    @property
    def measured_theta_dot(self):
        return self.theta_dot + np.random.normal(0, self.noise_std * 5)


class Cart:
    def __init__(self, mass=1.0, track_limit=3.0):
        self.mass = mass
        self.track_limit = track_limit
        self.x = 0.0
        self.x_dot = 0.0
        
    def reset(self):
        self.x = 0.0
        self.x_dot = 0.0


class Controller:
    def __init__(self):
        self.mode = "PID"
        self.Kp = 50.0
        self.Ki = 1.0
        self.Kd = 10.0
        self.integral = 0.0
        self.prev_error = 0.0
        self.LQR_K = np.array([[-1.0, -1.732, 18.68, 3.467]])
        
    def compute(self, state, dt):
        """state = [x, x_dot, theta, theta_dot]"""
        x, x_dot, theta, theta_dot = state
        
        if self.mode == "P":
            return self.Kp * theta
        
        elif self.mode == "PD":
            return self.Kp * theta + self.Kd * theta_dot
        
        elif self.mode == "PID":
            error = theta
            self.integral += error * dt
            derivative = (error - self.prev_error) / dt if dt > 0 else 0
            self.prev_error = error
            return self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        
        elif self.mode == "LQR":
            state_vec = np.array([[x], [x_dot], [theta], [theta_dot]])
            return float(-self.LQR_K @ state_vec)
        
        return 0.0
    
    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0


class Simulation:
    def __init__(self):
        self.cart = Cart()
        self.pendulum = Pendulum()
        self.controller = Controller()
        
        self.dt = DT
        self.manual_force = 0.0
        self.auto_mode = False  # شروع با حالت دستی
        self.running = False
        self.paused = False
        
        self.time_elapsed = 0.0
        self.score = 0.0
        self.best_score = 0.0
        
        self.log = {"t": [], "theta": [], "force": [], "x": []}
        self.theta_history = []
        
        self.difficulty = "Medium"
        self.difficulties = {
            "Easy": {"noise": 0.0, "mass_pole": 0.05, "length": 1.2, "cart_mass": 1.5},
            "Medium": {"noise": 0.01, "mass_pole": 0.1, "length": 1.0, "cart_mass": 1.0},
            "Hard": {"noise": 0.03, "mass_pole": 0.15, "length": 0.8, "cart_mass": 0.8},
            "Expert": {"noise": 0.05, "mass_pole": 0.2, "length": 0.6, "cart_mass": 0.6}
        }
        
        self._load_best()
        
    def _load_best(self):
        if os.path.exists("best_score.json"):
            try:
                with open("best_score.json", "r") as f:
                    data = json.load(f)
                    self.best_score = data.get("best", 0.0)
            except:
                pass
    
    def save_best(self):
        with open("best_score.json", "w") as f:
            json.dump({"best": self.best_score}, f)
    
    def reset(self):
        diff = self.difficulties[self.difficulty]
        
        self.cart.mass = diff["cart_mass"]
        self.cart.reset()
        
        self.pendulum.mass = diff["mass_pole"]
        self.pendulum.length = diff["length"]
        self.pendulum.reset(noise_std=diff["noise"])
        
        self.controller.reset()
        
        self.time_elapsed = 0.0
        self.score = 0.0
        self.log = {"t": [], "theta": [], "force": [], "x": []}
        self.theta_history = []
        self.running = True
        self.paused = False
        self.manual_force = 0.0
    
    def _derivatives(self, state, F):
        """state = [x, x_dot, theta, theta_dot]"""
        x, x_dot, theta, theta_dot = state
        
        mc = self.cart.mass
        mp = self.pendulum.mass
        L = self.pendulum.length
        
        sin_t = np.sin(theta)
        cos_t = np.cos(theta)
        
        total = mc + mp
        denom = total - mp * cos_t**2
        
        x_ddot = (F + mp * sin_t * (L * theta_dot**2 + G * cos_t)) / denom
        theta_ddot = (-F * cos_t - mp * L * theta_dot**2 * sin_t * cos_t - total * G * sin_t) / (L * denom)
        
        return np.array([x_dot, x_ddot, theta_dot, theta_ddot])
    
    def _rk4(self, state, F):
        k1 = self._derivatives(state, F)
        k2 = self._derivatives(state + k1 * self.dt / 2, F)
        k3 = self._derivatives(state + k2 * self.dt / 2, F)
        k4 = self._derivatives(state + k3 * self.dt, F)
        return state + (k1 + 2*k2 + 2*k3 + k4) * self.dt / 6
    
    def step(self):
        if not self.running or self.paused:
            return
        
        # Get state (with noise for controller if auto)
        if self.auto_mode:
            state = np.array([
                self.cart.x,
                self.cart.x_dot,
                self.pendulum.measured_theta,
                self.pendulum.measured_theta_dot
            ])
            force = self.controller.compute(state, self.dt)
        else:
            force = self.manual_force
        
        force = np.clip(force, -50, 50)
        
        # Update physics
        true_state = np.array([
            self.cart.x,
            self.cart.x_dot,
            self.pendulum.theta,
            self.pendulum.theta_dot
        ])
        
        new_state = self._rk4(true_state, force)
        
        self.cart.x = np.clip(new_state[0], -self.cart.track_limit, self.cart.track_limit)
        self.cart.x_dot = new_state[1]
        self.pendulum.theta = new_state[2]
        self.pendulum.theta_dot = new_state[3]
        
        # Update time and score
        self.time_elapsed += self.dt
        if abs(self.pendulum.theta) < np.radians(20):
            self.score += self.dt
        
        if self.score > self.best_score:
            self.best_score = self.score
            self.save_best()
        
        # Log data
        self.log["t"].append(self.time_elapsed)
        self.log["theta"].append(np.degrees(self.pendulum.theta))
        self.log["force"].append(force)
        self.log["x"].append(self.cart.x)
        
        # History for plot
        self.theta_history.append(np.degrees(self.pendulum.theta))
        if len(self.theta_history) > 200:
            self.theta_history.pop(0)
    
    @property
    def fallen(self):
        return abs(self.pendulum.theta) > np.radians(45)
    
    @property
    def near_fall(self):
        return abs(self.pendulum.theta) > np.radians(25)


# ──────────────────────────────────────────────
# GUI
# ──────────────────────────────────────────────

class GUI:
    def __init__(self):
        self.sim = Simulation()
        
        self.root = tk.Tk()
        self.root.title("Inverted Pendulum — Control Lab")
        self.root.configure(bg=BG)
        
        # پنجره قابل تغییر اندازه
        self.root.state('zoomed')  # برای ویندوز
        # برای لینوکس/مک می‌توانید از این استفاده کنید:
        # self.root.attributes('-zoomed', True)
        
        self._build_ui()
        self._bind_keys()
        
        self.sim.reset()
        self.sim.running = True
        self.root.after(int(DT * 1000), self._loop)
        self.root.mainloop()
    
    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=10, pady=(10, 5))
        tk.Label(header, text="⚖  Inverted Pendulum — Control Engineering Lab",
                 font=("Consolas", 16, "bold"), bg=BG, fg=ACCENT2).pack()
        
        # Main area
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Left side: Canvas + Plot
        left = tk.Frame(main, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.canvas = tk.Canvas(left, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.plot_canvas = tk.Canvas(left, height=140, bg=PANEL, highlightthickness=0)
        self.plot_canvas.pack(fill="x", pady=(5, 0))
        
        # Right side: Control panels
        right = tk.Frame(main, bg=BG, width=280)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        
        # Telemetry panel
        self._build_telemetry(right)
        
        # Controller panel
        self._build_controller(right)
        
        # PID Tuning panel
        self._build_pid_tuning(right)
        
        # Difficulty panel
        self._build_difficulty(right)
        
        # Control buttons
        self._build_buttons(right)
    
    def _build_telemetry(self, parent):
        panel = tk.Frame(parent, bg=PANEL, padx=12, pady=10)
        panel.pack(fill="x", pady=(0, 8))
        
        tk.Label(panel, text="TELEMETRY", font=("Consolas", 11, "bold"),
                 bg=PANEL, fg=ACCENT2).pack(anchor="w", pady=(0, 8))
        
        def add_row(label, attr):
            tk.Label(panel, text=label, font=("Consolas", 9),
                     bg=PANEL, fg=TEXT, anchor="w").pack(anchor="w")
            lbl = tk.Label(panel, text="—", font=("Consolas", 11, "bold"),
                           bg=PANEL, fg=GREEN, anchor="w")
            lbl.pack(anchor="w", pady=(0, 6))
            setattr(self, attr, lbl)
        
        add_row("Angle (°)", "lbl_theta")
        add_row("Ang. vel (°/s)", "lbl_thetadot")
        add_row("Cart pos (m)", "lbl_x")
        add_row("Force (N)", "lbl_force")
        add_row("Time (s)", "lbl_time")
        add_row("Score", "lbl_score")
        add_row("Best", "lbl_best")
    
    def _build_controller(self, parent):
        panel = tk.Frame(parent, bg=PANEL, padx=12, pady=10)
        panel.pack(fill="x", pady=(0, 8))
        
        tk.Label(panel, text="CONTROLLER", font=("Consolas", 11, "bold"),
                 bg=PANEL, fg=ACCENT2).pack(anchor="w", pady=(0, 8))
        
        self.ctrl_var = tk.StringVar(value="Manual")
        
        for mode in ["Manual", "P", "PD", "PID", "LQR"]:
            tk.Radiobutton(panel, text=mode, variable=self.ctrl_var, value=mode,
                           font=("Consolas", 10), bg=PANEL, fg=TEXT, selectcolor=ACCENT,
                           activebackground=PANEL, activeforeground=ACCENT2,
                           command=self._on_ctrl_change).pack(anchor="w", pady=2)
    
    def _build_pid_tuning(self, parent):
        panel = tk.Frame(parent, bg=PANEL, padx=12, pady=10)
        panel.pack(fill="x", pady=(0, 8))
        
        tk.Label(panel, text="PID TUNING", font=("Consolas", 11, "bold"),
                 bg=PANEL, fg=ACCENT2).pack(anchor="w", pady=(0, 8))
        
        def add_slider(label, from_, to, default, attr):
            tk.Label(panel, text=label, font=("Consolas", 9),
                     bg=PANEL, fg=TEXT).pack(anchor="w", pady=(4, 0))
            slider = tk.Scale(panel, from_=from_, to=to, resolution=0.1,
                              orient="horizontal", bg=PANEL, fg=TEXT,
                              highlightthickness=0, troughcolor=ACCENT,
                              command=lambda v: self._update_pid())
            slider.set(default)
            slider.pack(fill="x", pady=(0, 4))
            setattr(self, attr, slider)
        
        add_slider("Kp", 0, 150, 50, "slider_kp")
        add_slider("Ki", 0, 10, 1, "slider_ki")
        add_slider("Kd", 0, 50, 10, "slider_kd")
    
    def _build_difficulty(self, parent):
        panel = tk.Frame(parent, bg=PANEL, padx=12, pady=10)
        panel.pack(fill="x", pady=(0, 8))
        
        tk.Label(panel, text="DIFFICULTY", font=("Consolas", 11, "bold"),
                 bg=PANEL, fg=ACCENT2).pack(anchor="w", pady=(0, 8))
        
        self.diff_var = tk.StringVar(value="Medium")
        
        for level in ["Easy", "Medium", "Hard", "Expert"]:
            tk.Radiobutton(panel, text=level, variable=self.diff_var, value=level,
                           font=("Consolas", 10), bg=PANEL, fg=TEXT, selectcolor=ACCENT,
                           activebackground=PANEL, activeforeground=ACCENT2,
                           command=self._on_diff_change).pack(anchor="w", pady=2)
    
    def _build_buttons(self, parent):
        panel = tk.Frame(parent, bg=BG)
        panel.pack(fill="x", pady=(0, 0))
        
        btn_cfg = dict(font=("Consolas", 10, "bold"), bg=ACCENT, fg="white",
                       relief="flat", cursor="hand2", padx=8, pady=6)
        
        tk.Button(panel, text="⏸  Pause", command=self._toggle_pause, **btn_cfg).pack(fill="x", pady=(0, 4))
        tk.Button(panel, text="↺  Reset", command=self._do_reset, **btn_cfg).pack(fill="x", pady=(0, 4))
        tk.Button(panel, text="💾  Save Log", command=self._save_log, **btn_cfg).pack(fill="x")
    
    def _on_ctrl_change(self):
        mode = self.ctrl_var.get()
        if mode == "Manual":
            self.sim.auto_mode = False
        else:
            self.sim.auto_mode = True
            self.sim.controller.mode = mode
            self.sim.controller.reset()
    
    def _update_pid(self):
        self.sim.controller.Kp = self.slider_kp.get()
        self.sim.controller.Ki = self.slider_ki.get()
        self.sim.controller.Kd = self.slider_kd.get()
    
    def _on_diff_change(self):
        self.sim.difficulty = self.diff_var.get()
        self._do_reset()
    
    def _toggle_pause(self):
        self.sim.paused = not self.sim.paused
    
    def _do_reset(self):
        self.sim.reset()
    
    def _set_force(self, f):
        if not self.sim.auto_mode:  # فقط در حالت دستی
            self.sim.manual_force = f
    
    def _save_log(self):
        with open("pendulum_log.csv", "w") as f:
            f.write("time,theta_deg,force,x\n")
            for i in range(len(self.sim.log["t"])):
                f.write(f"{self.sim.log['t'][i]:.3f},{self.sim.log['theta'][i]:.3f},"
                        f"{self.sim.log['force'][i]:.3f},{self.sim.log['x'][i]:.3f}\n")
        self.lbl_score.config(text="Saved!")
        self.root.after(1500, lambda: self._update_labels())
    
    def _bind_keys(self):
        # کنترل با کیبورد - فقط کلیدهای چپ و راست
        self.root.bind("<Left>", lambda e: self._set_force(-25))
        self.root.bind("<Right>", lambda e: self._set_force(25))
        self.root.bind("<KeyRelease-Left>", lambda e: self._set_force(0))
        self.root.bind("<KeyRelease-Right>", lambda e: self._set_force(0))
        
        # کلیدهای دیگر
        self.root.bind("<space>", lambda e: self._toggle_pause())
        self.root.bind("<r>", lambda e: self._do_reset())
        self.root.bind("<R>", lambda e: self._do_reset())
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self._exit_fullscreen())
        
    def _toggle_fullscreen(self):
        current = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not current)
        
    def _exit_fullscreen(self):
        self.root.attributes('-fullscreen', False)
    
    def _draw(self):
        cv = self.canvas
        cv.delete("all")
        W = cv.winfo_width()
        H = cv.winfo_height()
        
        if W <= 1 or H <= 1:
            return
        
        SCALE = min(W, H) // 8
        
        # Grid
        for x in range(0, W, 50):
            cv.create_line(x, 0, x, H, fill=GRID, width=1)
        for y in range(0, H, 50):
            cv.create_line(0, y, W, y, fill=GRID, width=1)
        
        # Track
        cy = int(H * 0.7)
        cv.create_rectangle(0, cy+15, W, cy+20, fill=TRACK, outline="")
        
        # Track limits
        for sign in [-1, 1]:
            lx = W//2 + sign * self.sim.cart.track_limit * SCALE
            cv.create_line(lx, cy-40, lx, cy+40, fill=WARN, width=2, dash=(5, 3))
        
        # Cart position
        cx = W//2 + self.sim.cart.x * SCALE
        cart_w, cart_h = 55, 30
        cv.create_rectangle(cx-cart_w, cy-cart_h, cx+cart_w, cy,
                            fill=CART_C, outline=ACCENT2, width=2)
        
        # Wheels
        for wx in [cx-35, cx+35]:
            cv.create_oval(wx-8, cy-6, wx+8, cy+10, fill=WHEEL, outline=ACCENT2, width=2)
        
        # Pole
        theta = self.sim.pendulum.theta
        L = self.sim.pendulum.length
        px = cx + L * SCALE * np.sin(theta)
        py = cy - cart_h - L * SCALE * np.cos(theta)
        
        adeg = abs(np.degrees(theta))
        if adeg < 10:
            pole_color = POLE_OK
        elif adeg < 25:
            pole_color = POLE_WARN
        else:
            pole_color = POLE_FALL
        
        cv.create_line(cx, cy-cart_h, px, py, fill=pole_color, width=7, capstyle="round")
        cv.create_oval(px-12, py-12, px+12, py+12, fill=pole_color, outline="white", width=2)
        
        # Angle arc
        arc_r = 50
        start_angle = 90
        extent = -np.degrees(theta)
        cv.create_arc(cx-arc_r, cy-cart_h-arc_r, cx+arc_r, cy-cart_h+arc_r,
                      start=start_angle, extent=extent, outline=pole_color,
                      width=2, style="arc")
        
        # Status text
        if self.sim.fallen:
            cv.create_text(W//2, H//2, text="FALLEN — Press R to reset",
                           font=("Consolas", 20, "bold"), fill=WARN)
            self.sim.running = False
        elif self.sim.paused:
            cv.create_text(W//2, 30, text="PAUSED", font=("Consolas", 16, "bold"), fill=POLE_WARN)
        
        if not self.sim.auto_mode:
            cv.create_text(W//2, H-80, text="MANUAL MODE — Use ← → keys",
                           font=("Consolas", 14, "bold"), fill=GREEN)
        
        # Force arrow
        current_force = self.sim.manual_force if not self.sim.auto_mode else 0
        if abs(current_force) > 0.5:
            arrow_len = int(abs(current_force) * 3)
            arrow_x = cx + np.sign(current_force) * arrow_len
            cv.create_line(cx, cy-cart_h//2, arrow_x, cy-cart_h//2,
                           fill=POLE_WARN, width=5, arrow=tk.LAST, arrowshape=(15, 18, 6))
        
        # Key hints
        cv.create_text(W//2, H-30, 
                       text="← → : control   |   Space: pause   |   R: reset   |   F11: fullscreen",
                       font=("Consolas", 10), fill=TEXT)
    
    def _draw_plot(self):
        pc = self.plot_canvas
        pc.delete("all")
        W = pc.winfo_width()
        H = 140
        
        if W <= 1:
            return
        
        pc.create_rectangle(0, 0, W, H, fill=PANEL, outline="")
        
        # Danger zones
        mid = H // 2
        zone_45 = mid
        zone_25 = int(25 / 45 * mid)
        
        pc.create_rectangle(0, 0, W, mid-zone_25, fill="#2a1515", outline="")
        pc.create_rectangle(0, mid+zone_25, W, H, fill="#2a1515", outline="")
        
        # Grid lines
        pc.create_line(0, mid, W, mid, fill=GRID, width=1, dash=(4, 2))
        pc.create_line(0, mid-zone_25, W, mid-zone_25, fill=WARN, width=1, dash=(2, 2))
        pc.create_line(0, mid+zone_25, W, mid+zone_25, fill=WARN, width=1, dash=(2, 2))
        
        # Labels
        pc.create_text(8, mid-zone_25, text="+25°", font=("Consolas", 8), fill=WARN, anchor="w")
        pc.create_text(8, mid+zone_25, text="-25°", font=("Consolas", 8), fill=WARN, anchor="w")
        pc.create_text(8, mid, text="0°", font=("Consolas", 8), fill=TEXT, anchor="w")
        pc.create_text(W-8, 10, text="θ(t)", font=("Consolas", 9, "bold"), fill=ACCENT2, anchor="ne")
        
        # Plot history
        hist = self.sim.theta_history
        if len(hist) < 2:
            return
        
        points = []
        n = len(hist)
        for i, val in enumerate(hist):
            x = int(i / (n - 1) * W)
            y = int(mid - (val / 45) * mid)
            y = max(2, min(H-2, y))
            points.append((x, y))
        
        for i in range(len(points) - 1):
            pc.create_line(*points[i], *points[i+1], fill=ACCENT2, width=2)
    
    def _update_labels(self):
        theta_d = np.degrees(self.sim.pendulum.theta)
        color = WARN if abs(theta_d) > 25 else GREEN
        
        self.lbl_theta.config(text=f"{theta_d:.2f}", fg=color)
        self.lbl_thetadot.config(text=f"{np.degrees(self.sim.pendulum.theta_dot):.2f}", fg=TEXT)
        self.lbl_x.config(text=f"{self.sim.cart.x:.2f}", fg=TEXT)
        
        if self.sim.auto_mode:
            state = np.array([self.sim.cart.x, self.sim.cart.x_dot,
                              self.sim.pendulum.measured_theta, self.sim.pendulum.measured_theta_dot])
            force = self.sim.controller.compute(state, self.sim.dt)
        else:
            force = self.sim.manual_force
        
        self.lbl_force.config(text=f"{force:.1f}", fg=TEXT)
        self.lbl_time.config(text=f"{self.sim.time_elapsed:.2f}", fg=TEXT)
        self.lbl_score.config(text=f"{self.sim.score:.2f}", fg=GREEN)
        self.lbl_best.config(text=f"{self.sim.best_score:.2f}", fg=ACCENT2)
    
    def _loop(self):
        self.sim.step()
        self._draw()
        self._draw_plot()
        self._update_labels()
        self.root.after(int(DT * 1000), self._loop)


# ──────────────────────────────────────────────
# RUN
# ──────────────────────────────────────────────

if __name__ == "__main__":
    GUI()
