import tkinter as tk
from tkinter import ttk
import math
import numpy as np

class CannonGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Cannon Game")
        self.root.configure(bg='#1a1a2e')

        self.canvas_width = 700
        self.canvas_height = 400
        self.cannon_x = 60
        self.cannon_y = 340
        self.angle = 45.0
        self.power = 50.0
        self.attempts = 0
        self.max_attempts = 3
        
        
        
        self.game_over = False
        self.animating = False

        self.build_ui()
        self.new_game()

    def build_ui(self):
        title = tk.Label(self.root, text="🎯 Cannon Game",
                         bg='#1a1a2e', fg='#bb86fc',
                         font=('Arial', 18, 'bold'))
        title.pack(pady=8)

        self.canvas = tk.Canvas(self.root, width=self.canvas_width,
                                height=self.canvas_height,
                                bg='#0d0d1a', highlightthickness=2,
                                highlightbackground='#6200ee')
        self.canvas.pack(padx=15)

        controls = tk.Frame(self.root, bg='#1a1a2e')
        controls.pack(pady=10)

        # Angle slider
        tk.Label(controls, text="Angle:", bg='#1a1a2e', fg='#bb86fc',
                 font=('Arial', 11)).grid(row=0, column=0, padx=8)

        self.angle_var = tk.DoubleVar(value=45)
        angle_slider = ttk.Scale(controls, from_=0, to=90,
                                 variable=self.angle_var, orient='horizontal',
                                 length=180, command=self.update_angle)
        angle_slider.grid(row=0, column=1, padx=5)

        self.angle_label = tk.Label(controls, text="45.0°",
                                    bg='#1a1a2e', fg='#ffffff',
                                    font=('Arial', 11), width=6)
        self.angle_label.grid(row=0, column=2, padx=5)

        # Power slider
        tk.Label(controls, text="Power:", bg='#1a1a2e', fg='#bb86fc',
                 font=('Arial', 11)).grid(row=0, column=3, padx=8)

        self.power_var = tk.DoubleVar(value=50)
        power_slider = ttk.Scale(controls, from_=10, to=100,
                                 variable=self.power_var, orient='horizontal',
                                 length=180, command=self.update_power)
        power_slider.grid(row=0, column=4, padx=5)

        self.power_label = tk.Label(controls, text="50.0 m/s",
                                    bg='#1a1a2e', fg='#ffffff',
                                    font=('Arial', 11), width=9)
        self.power_label.grid(row=0, column=5, padx=5)

        # Buttons
        btn_frame = tk.Frame(self.root, bg='#1a1a2e')
        btn_frame.pack(pady=6)

        self.fire_btn = tk.Button(btn_frame, text="🔥 Fire!",
                                  bg='#6200ee', fg='white',
                                  font=('Arial', 12, 'bold'),
                                  relief='flat', padx=18, pady=5,
                                  command=self.fire,
                                  activebackground='#9c4dcc')
        self.fire_btn.pack(side='left', padx=10)

        tk.Button(btn_frame, text="🔄 New Game",
                  bg='#333366', fg='white',
                  font=('Arial', 12), relief='flat',
                  padx=14, pady=5, command=self.new_game,
                  activebackground='#555599').pack(side='left', padx=10)

        # Status bar
        bottom = tk.Frame(self.root, bg='#1a1a2e')
        bottom.pack(pady=4)

        self.attempts_label = tk.Label(bottom, text="Attempts: 0/3",
                                       bg='#1a1a2e', fg='#bb86fc',
                                       font=('Arial', 11))
        self.attempts_label.pack(side='left', padx=20)

        self.status_label = tk.Label(bottom, text="Adjust angle & power, then Fire!",
                                     bg='#1a1a2e', fg='#aaaaaa',
                                     font=('Arial', 11))
        self.status_label.pack(side='left', padx=20)

    def update_angle(self, value):
        self.angle = float(value)
        self.angle_label.config(text=f"{self.angle:.1f}°")
        self.redraw_cannon()

    def update_power(self, value):
        self.power = float(value)
        self.power_label.config(text=f"{self.power:.1f} m/s")

    def redraw_cannon(self):
        self.canvas.delete("cannon")
        self.draw_cannon()

    def new_game(self):
        self.attempts = 0
        self.game_over = False
        self.animating = False
        self.fire_btn.config(state='normal')
        self.attempts_label.config(text="Attempts: 0/3")
        self.status_label.config(text="Adjust angle & power, then Fire!",
                                 fg='#aaaaaa')

        # Random target position
        self.target_x = np.random.randint(400, 640)
        self.target_y = self.cannon_y
        self.target_radius = 18

        self.canvas.delete("all")
        self.draw_background()
        self.draw_target()
        self.draw_cannon()

    def draw_background(self):
        # Ground
        self.canvas.create_rectangle(0, self.cannon_y + 20,
                                     self.canvas_width, self.canvas_height,
                                     fill='#16213e', outline='')
        # Ground line
        self.canvas.create_line(0, self.cannon_y + 20,
                                self.canvas_width, self.cannon_y + 20,
                                fill='#6200ee', width=2)

    def draw_target(self):
        x, y = self.target_x, self.target_y
        r = self.target_radius
        self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                fill='#cf6679', outline='#ff4081', width=2,
                                tags="target")
        self.canvas.create_oval(x - r//2, y - r//2,
                                x + r//2, y + r//2,
                                fill='#ff4081', outline='',
                                tags="target")

    def draw_cannon(self):
        angle_rad = math.radians(self.angle)
        barrel_length = 35
        end_x = self.cannon_x + barrel_length * math.cos(angle_rad)
        end_y = self.cannon_y - barrel_length * math.sin(angle_rad)

        # Cannon body
        self.canvas.create_rectangle(self.cannon_x - 22, self.cannon_y,
                                     self.cannon_x + 22, self.cannon_y + 18,
                                     fill='#6200ee', outline='#bb86fc', width=2,
                                     tags="cannon")
        # Wheels
        self.canvas.create_oval(self.cannon_x - 20, self.cannon_y + 12,
                                self.cannon_x - 6, self.cannon_y + 22,
                                fill='#333366', outline='#bb86fc',
                                tags="cannon")
        self.canvas.create_oval(self.cannon_x + 6, self.cannon_y + 12,
                                self.cannon_x + 20, self.cannon_y + 22,
                                fill='#333366', outline='#bb86fc',
                                tags="cannon")
        # Barrel
        self.canvas.create_line(self.cannon_x, self.cannon_y,
                                end_x, end_y,
                                fill='#bb86fc', width=6,
                                tags="cannon")

    def fire(self):
        if self.game_over or self.animating:
            return

        self.animating = True
        self.fire_btn.config(state='disabled')
        self.attempts += 1
        self.attempts_label.config(text=f"Attempts: {self.attempts}/{self.max_attempts}")

        angle_rad = math.radians(self.angle)
        v0x = self.power * math.cos(angle_rad)
        v0y = self.power * math.sin(angle_rad)
        g = 9.8
        dt = 0.05
        scale = 4.5

        t = 0
        trajectory = []
        while True:
            x = self.cannon_x + v0x * t * scale
            y = self.cannon_y - (v0y * t - 0.5 * g * t ** 2) * scale
            trajectory.append((x, y))
            if y > self.cannon_y + 20 and t > 0.1:
                break
            if x > self.canvas_width + 50:
                break
            t += dt

        self.animate_projectile(trajectory, 0)

    def animate_projectile(self, trajectory, idx):
        if idx > 0:
            self.canvas.delete("projectile")

        if idx >= len(trajectory):
            self.animating = False
            self.check_miss()
            return

        x, y = trajectory[idx]

        # Draw trail
        if idx > 0:
            px, py = trajectory[idx - 1]
            self.canvas.create_line(px, py, x, y,
                                    fill='#6200ee', width=1,
                                    tags="trail")

        # Draw ball
        self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6,
                                fill='#ffcc00', outline='#ff9900',
                                tags="projectile")

        # Check hit
        dist = math.sqrt((x - self.target_x) ** 2 + (y - self.target_y) ** 2)
        if dist <= self.target_radius + 6:
            self.canvas.delete("projectile")
            self.on_hit()
            return

        self.root.after(20, lambda: self.animate_projectile(trajectory, idx + 1))

    def check_miss(self):
        if self.attempts >= self.max_attempts:
            self.game_over = True
            self.status_label.config(text="💀 Game Over! Press New Game.",
                                     fg='#cf6679')
        else:
            remaining = self.max_attempts - self.attempts
            self.status_label.config(
                text=f"Missed! {remaining} attempt(s) left.",
                fg='#ffcc00')
            self.fire_btn.config(state='normal')

    def on_hit(self):
        self.game_over = True
        self.animating = False
        self.canvas.delete("target")
        self.canvas.create_text(self.target_x, self.target_y,
                                text="💥", font=('Arial', 28))
        self.status_label.config(
            text=f"🎉 Hit! You got it in {self.attempts} attempt(s)!",
            fg='#00e676')
        self.fire_btn.config(state='disabled')


if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('Horizontal.TScale', background='#1a1a2e',
                    troughcolor='#333366', sliderlength=18)
    app = CannonGame(root)
    root.mainloop()
