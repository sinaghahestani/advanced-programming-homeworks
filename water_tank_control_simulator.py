import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import math

class Tank:
    def __init__(self, capacity=50, height=100, diameter=30):
        self.capacity = capacity  # liters
        self.height = height  # cm
        self.diameter = diameter  # cm
        self.current_level = 0  # liters
        self.current_height = 0  # cm
        
    def add_water(self, amount):
        """Add water to tank (in liters)"""
        self.current_level = min(self.capacity, self.current_level + amount)
        self.update_height()
        
    def remove_water(self, amount):
        """Remove water from tank (in liters)"""
        self.current_level = max(0, self.current_level - amount)
        self.update_height()
        
    def update_height(self):
        """Calculate water height based on current level"""
        self.current_height = (self.current_level / self.capacity) * self.height
        
    def get_level(self):
        return self.current_level
    
    def get_height(self):
        return self.current_height
    
    def get_percentage(self):
        return (self.current_level / self.capacity) * 100

class Pump:
    def __init__(self, flow_rate=2.0):
        self.flow_rate = flow_rate  # liters per second
        self.is_on = False
        
    def turn_on(self):
        self.is_on = True
        
    def turn_off(self):
        self.is_on = False
        
    def get_flow(self, dt=0.1):
        """Get flow for time step dt"""
        if self.is_on:
            return self.flow_rate * dt
        return 0

class Sensor:
    def __init__(self, tank):
        self.tank = tank
        
    def read_level(self):
        """Read current water level"""
        return self.tank.get_level()
    
    def read_height(self):
        """Read current water height"""
        return self.tank.get_height()

class OnOffController:
    def __init__(self, setpoint, hysteresis=2.0):
        self.setpoint = setpoint
        self.hysteresis = hysteresis
        
    def compute(self, current_value):
        """Returns True if pump should be ON"""
        if current_value < self.setpoint - self.hysteresis:
            return True
        elif current_value > self.setpoint + self.hysteresis:
            return False
        return None  # Keep current state

class PIDController:
    def __init__(self, kp=1.0, ki=0.1, kd=0.05, setpoint=25):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        
        self.integral = 0
        self.prev_error = 0
        
    def compute(self, current_value, dt=0.1):
        """Compute PID output (0 to 1 range for pump intensity)"""
        error = self.setpoint - current_value
        
        self.integral += error * dt
        self.integral = max(-10, min(10, self.integral))  # Anti-windup
        
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        
        self.prev_error = error
        
        # Clamp output to 0-1 range
        return max(0, min(1, output))
    
    def reset(self):
        self.integral = 0
        self.prev_error = 0

class WaterTankSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("Water Tank Level Control Simulator")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a0033')
        
        # System components
        self.tank = Tank(capacity=50, height=100, diameter=30)
        self.pump = Pump(flow_rate=2.0)
        self.sensor = Sensor(self.tank)
        self.outlet_flow = 0.8  # liters per second (constant drain)
        
        # Controllers
        self.onoff_controller = OnOffController(setpoint=25, hysteresis=2)
        self.pid_controller = PIDController(kp=0.15, ki=0.02, kd=0.5, setpoint=25)
        
        # Simulation state
        self.running = False
        self.time = 0
        self.dt = 0.1  # seconds
        self.speed = 100  # ms per tick
        self.control_mode = 'manual'  # 'manual', 'onoff', 'pid'
        
        # Data history
        self.time_history = []
        self.level_history = []
        self.setpoint_history = []
        self.pump_state_history = []
        
        self.setup_ui()
        self.update_tank_visual()
        
    def setup_ui(self):
        # Main container
        main_frame = tk.Frame(self.root, bg='#1a0033')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Right panel - Control & Settings
        right_panel = tk.Frame(main_frame, bg='#2d1b4e', relief=tk.RIDGE, bd=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5,0))
        
        # Title
        title = tk.Label(right_panel, text="💧 Water Tank Control", 
                        font=('Arial', 16, 'bold'), bg='#2d1b4e', fg='#bb86fc')
        title.pack(pady=10)
        
        # Control Mode Selection
        mode_frame = tk.LabelFrame(right_panel, text="Control Mode", 
                                   font=('Arial', 11, 'bold'),
                                   bg='#2d1b4e', fg='#bb86fc', relief=tk.RIDGE, bd=2)
        mode_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.mode_var = tk.StringVar(value='manual')
        modes = [('Manual', 'manual'), ('On-Off', 'onoff'), ('PID', 'pid')]
        
        for text, mode in modes:
            tk.Radiobutton(mode_frame, text=text, variable=self.mode_var, 
                          value=mode, command=self.change_mode,
                          bg='#2d1b4e', fg='#bb86fc', selectcolor='#1a0033',
                          font=('Arial', 10), activebackground='#2d1b4e',
                          activeforeground='#03dac6').pack(anchor='w', padx=10, pady=2)
        
        # Setpoint Control
        setpoint_frame = tk.LabelFrame(right_panel, text="Setpoint (Liters)", 
                                       font=('Arial', 11, 'bold'),
                                       bg='#2d1b4e', fg='#bb86fc', relief=tk.RIDGE, bd=2)
        setpoint_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.setpoint_var = tk.DoubleVar(value=25)
        self.setpoint_scale = tk.Scale(setpoint_frame, from_=5, to=45, 
                                       orient=tk.HORIZONTAL, variable=self.setpoint_var,
                                       command=self.update_setpoint,
                                       bg='#2d1b4e', fg='#bb86fc', 
                                       highlightthickness=0, length=200,
                                       font=('Arial', 10))
        self.setpoint_scale.pack(padx=10, pady=5)
        
        self.setpoint_label = tk.Label(setpoint_frame, text="25.0 L", 
                                       bg='#2d1b4e', fg='#03dac6',
                                       font=('Arial', 12, 'bold'))
        self.setpoint_label.pack(pady=5)
        
        # Manual Pump Control
        self.manual_frame = tk.LabelFrame(right_panel, text="Manual Pump Control", 
                                         font=('Arial', 11, 'bold'),
                                         bg='#2d1b4e', fg='#bb86fc', relief=tk.RIDGE, bd=2)
        self.manual_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.pump_btn = tk.Button(self.manual_frame, text="Pump OFF", 
                                 command=self.toggle_pump,
                                 bg='#cf6679', fg='#fff', font=('Arial', 11, 'bold'),
                                 width=15, relief=tk.RAISED, bd=3)
        self.pump_btn.pack(pady=10)
        
        # PID Tuning
        self.pid_frame = tk.LabelFrame(right_panel, text="PID Tuning", 
                                       font=('Arial', 11, 'bold'),
                                       bg='#2d1b4e', fg='#bb86fc', relief=tk.RIDGE, bd=2)
        
        pid_params = [
            ('Kp (Proportional)', 'kp', 0, 1, 0.15),
            ('Ki (Integral)', 'ki', 0, 0.5, 0.02),
            ('Kd (Derivative)', 'kd', 0, 2, 0.5)
        ]
        
        self.pid_vars = {}
        for label, key, from_, to, default in pid_params:
            frame = tk.Frame(self.pid_frame, bg='#2d1b4e')
            frame.pack(fill=tk.X, padx=10, pady=3)
            
            tk.Label(frame, text=label, bg='#2d1b4e', fg='#bb86fc',
                    font=('Arial', 9)).pack(anchor='w')
            
            var = tk.DoubleVar(value=default)
            self.pid_vars[key] = var
            
            scale = tk.Scale(frame, from_=from_, to=to, resolution=0.01,
                           orient=tk.HORIZONTAL, variable=var,
                           command=lambda v, k=key: self.update_pid(k, v),
                           bg='#2d1b4e', fg='#bb86fc', 
                           highlightthickness=0, length=180,
                           font=('Arial', 8))
            scale.pack()
        
        # On-Off Tuning
        self.onoff_frame = tk.LabelFrame(right_panel, text="On-Off Settings", 
                                         font=('Arial', 11, 'bold'),
                                         bg='#2d1b4e', fg='#bb86fc', relief=tk.RIDGE, bd=2)
        
        hyst_frame = tk.Frame(self.onoff_frame, bg='#2d1b4e')
        hyst_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(hyst_frame, text="Hysteresis (L)", bg='#2d1b4e', fg='#bb86fc',
                font=('Arial', 9)).pack(anchor='w')
        
        self.hyst_var = tk.DoubleVar(value=2)
        hyst_scale = tk.Scale(hyst_frame, from_=0.5, to=5, resolution=0.5,
                             orient=tk.HORIZONTAL, variable=self.hyst_var,
                             command=self.update_hysteresis,
                             bg='#2d1b4e', fg='#bb86fc',
                             highlightthickness=0, length=180,
                             font=('Arial', 8))
        hyst_scale.pack()
        
        # Simulation Control
        sim_frame = tk.LabelFrame(right_panel, text="Simulation", 
                                 font=('Arial', 11, 'bold'),
                                 bg='#2d1b4e', fg='#bb86fc', relief=tk.RIDGE, bd=2)
        sim_frame.pack(padx=10, pady=5, fill=tk.X)
        
        self.start_btn = tk.Button(sim_frame, text="▶ Start", 
                                   command=self.start_simulation,
                                   bg='#03dac6', fg='#000', font=('Arial', 10, 'bold'),
                                   width=12, relief=tk.RAISED, bd=3)
        self.start_btn.pack(pady=5)
        
        self.stop_btn = tk.Button(sim_frame, text="⏸ Pause", 
                                  command=self.stop_simulation,
                                  bg='#cf6679', fg='#000', font=('Arial', 10, 'bold'),
                                  width=12, relief=tk.RAISED, bd=3, state=tk.DISABLED)
        self.stop_btn.pack(pady=5)
        
        tk.Button(sim_frame, text="🔄 Reset", command=self.reset_simulation,
                 bg='#9370db', fg='#fff', font=('Arial', 10, 'bold'),
                 width=12, relief=tk.RAISED, bd=3).pack(pady=5)
        
        # Speed control
        speed_frame = tk.Frame(sim_frame, bg='#2d1b4e')
        speed_frame.pack(pady=5)
        tk.Label(speed_frame, text="Speed:", bg='#2d1b4e', fg='#bb86fc',
                font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        self.speed_scale = tk.Scale(speed_frame, from_=50, to=300, orient=tk.HORIZONTAL,
                                   command=self.update_speed, bg='#2d1b4e', fg='#bb86fc',
                                   highlightthickness=0, length=130)
        self.speed_scale.set(100)
        self.speed_scale.pack(side=tk.LEFT)
        
        # Statistics
        stats_frame = tk.LabelFrame(right_panel, text="System Status", 
                                   font=('Arial', 11, 'bold'),
                                   bg='#2d1b4e', fg='#bb86fc', relief=tk.RIDGE, bd=2)
        stats_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        self.stats_labels = {}
        stats_info = [
            ("Time", "time", "0 s"),
            ("Water Level", "level", "0.0 L"),
            ("Level %", "percent", "0%"),
            ("Height", "height", "0 cm"),
            ("Pump Status", "pump", "OFF"),
            ("Error", "error", "0.0 L")
        ]
        
        for label, key, default in stats_info:
            frame = tk.Frame(stats_frame, bg='#2d1b4e')
            frame.pack(fill=tk.X, padx=10, pady=3)
            tk.Label(frame, text=f"{label}:", bg='#2d1b4e', fg='#bb86fc',
                    font=('Arial', 9, 'bold'), anchor='w', width=12).pack(side=tk.LEFT)
            self.stats_labels[key] = tk.Label(frame, text=default, bg='#2d1b4e',
                                             fg='#03dac6', font=('Arial', 9),
                                             anchor='e')
            self.stats_labels[key].pack(side=tk.RIGHT)
        
        # Left panel - Tank Visual & Charts
        left_panel = tk.Frame(main_frame, bg='#1a0033')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))
        
        # Tank visualization
        tank_frame = tk.LabelFrame(left_panel, text="Tank Visualization",
                                  font=('Arial', 12, 'bold'),
                                  bg='#2d1b4e', fg='#bb86fc', relief=tk.RIDGE, bd=2)
        tank_frame.pack(pady=(0,5), fill=tk.BOTH, expand=True)
        
        self.tank_canvas = tk.Canvas(tank_frame, width=500, height=350,
                                    bg='#0d0d0d', highlightthickness=0)
        self.tank_canvas.pack(padx=10, pady=10)
        
        # Charts
        chart_frame = tk.LabelFrame(left_panel, text="Level vs Time",
                                   font=('Arial', 12, 'bold'),
                                   bg='#2d1b4e', fg='#bb86fc', relief=tk.RIDGE, bd=2)
        chart_frame.pack(pady=(0,5), fill=tk.BOTH, expand=True)
        
        self.fig = Figure(figsize=(5, 3.5), facecolor='#2d1b4e')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1a0033')
        self.ax.set_xlabel('Time (s)', color='#bb86fc', fontsize=10)
        self.ax.set_ylabel('Water Level (L)', color='#bb86fc', fontsize=10)
        self.ax.tick_params(colors='#bb86fc', labelsize=8)
        self.ax.spines['bottom'].set_color('#bb86fc')
        self.ax.spines['left'].set_color('#bb86fc')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.grid(True, alpha=0.2, color='#bb86fc')
        
        self.chart_canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.chart_canvas.get_tk_widget().pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.change_mode()  # Initialize mode visibility
        
    def update_tank_visual(self):
        self.tank_canvas.delete('all')
        w, h = 500, 350
        
        # Tank dimensions
        tank_width = 150
        tank_height = 250
        tank_x = w // 2 - tank_width // 2
        tank_y = 50
        
        # Draw inlet pipe (from pump)
        pipe_x = tank_x + tank_width // 2
        self.tank_canvas.create_line(pipe_x, 10, pipe_x, tank_y,
                                     fill='#666', width=8)
        
        # Pump indicator
        pump_color = '#00ff00' if self.pump.is_on else '#666'
        self.tank_canvas.create_rectangle(pipe_x-15, 5, pipe_x+15, 25,
                                         fill=pump_color, outline='#fff', width=2)
        self.tank_canvas.create_text(pipe_x, 15, text='PUMP',
                                     fill='#000', font=('Arial', 8, 'bold'))
        
        # Flow indicator
        if self.pump.is_on:
            for i in range(3):
                y = 30 + i * 15
                self.tank_canvas.create_oval(pipe_x-3, y, pipe_x+3, y+6,
                                            fill='#03dac6', outline='')
        
        # Draw tank body
        self.tank_canvas.create_rectangle(tank_x, tank_y, 
                                         tank_x + tank_width, tank_y + tank_height,
                                         fill='', outline='#fff', width=3)
        
        # Water level
        water_height = (self.tank.get_level() / self.tank.capacity) * tank_height
        if water_height > 0:
            water_y = tank_y + tank_height - water_height
            self.tank_canvas.create_rectangle(tank_x+2, water_y,
                                             tank_x + tank_width-2, tank_y + tank_height-2,
                                             fill='#03dac6', outline='')
            
            # Water surface animation
            wave_points = []
            for x in range(0, tank_width, 5):
                wave_y = water_y + math.sin((x + self.time*10) * 0.2) * 2
                wave_points.extend([tank_x + x, wave_y])
            if len(wave_points) >= 4:
                self.tank_canvas.create_line(wave_points, fill='#fff', width=2, smooth=True)
        
        # Level markers
        for i in range(0, 6):
            level = i * 10
            y = tank_y + tank_height - (level / 50) * tank_height
            self.tank_canvas.create_line(tank_x - 10, y, tank_x, y,
                                         fill='#bb86fc', width=2)
            self.tank_canvas.create_text(tank_x - 20, y, text=f'{level}L',
                                         fill='#bb86fc', font=('Arial', 8))
        
        # Setpoint line
        if self.control_mode in ['onoff', 'pid']:
            setpoint = self.setpoint_var.get()
            setpoint_y = tank_y + tank_height - (setpoint / 50) * tank_height
            self.tank_canvas.create_line(tank_x, setpoint_y, 
                                         tank_x + tank_width, setpoint_y,
                                         fill='#ff6b6b', width=2, dash=(5, 5))
            self.tank_canvas.create_text(tank_x + tank_width + 30, setpoint_y,
                                         text='SP', fill='#ff6b6b',
                                         font=('Arial', 10, 'bold'))
        
        # Outlet pipe
        outlet_x = tank_x + tank_width + 10
        outlet_y = tank_y + tank_height - 20
        self.tank_canvas.create_line(tank_x + tank_width, outlet_y,
                                     outlet_x + 30, outlet_y,
                                     fill='#666', width=6)
        
        # Outlet flow indicator
        for i in range(3):
            x = outlet_x + i * 10
            self.tank_canvas.create_oval(x, outlet_y-2, x+4, outlet_y+2,
                                         fill='#9370db', outline='')
        
        # Labels
        self.tank_canvas.create_text(w//2, tank_y + tank_height + 30,
                                     text=f'{self.tank.get_level():.1f} L / {self.tank.capacity} L',
                                     fill='#03dac6', font=('Arial', 14, 'bold'))
        
        self.tank_canvas.create_text(w//2, tank_y - 20,
                                     text=f'Mode: {self.control_mode.upper()}',
                                     fill='#bb86fc', font=('Arial', 12, 'bold'))
        
    def update_chart(self):
        self.ax.clear()
        
        if len(self.time_history) > 0:
            # Plot water level
            self.ax.plot(self.time_history, self.level_history,
                        color='#03dac6', linewidth=2, label='Water Level')
            
            # Plot setpoint
            if len(self.setpoint_history) > 0:
                self.ax.plot(self.time_history, self.setpoint_history,
                            color='#ff6b6b', linewidth=2, linestyle='--', label='Setpoint')
            
            # Shade pump ON regions
            if self.control_mode != 'manual':
                pump_on_regions = []
                start_idx = None
                for i, state in enumerate(self.pump_state_history):
                    if state and start_idx is None:
                        start_idx = i
                    elif not state and start_idx is not None:
                        pump_on_regions.append((start_idx, i))
                        start_idx = None
                if start_idx is not None:
                    pump_on_regions.append((start_idx, len(self.pump_state_history)-1))
                
                for start, end in pump_on_regions:
                    self.ax.axvspan(self.time_history[start], self.time_history[end],
                                   alpha=0.2, color='#00ff00')
        
        self.ax.set_facecolor('#1a0033')
        self.ax.set_xlabel('Time (s)', color='#bb86fc', fontsize=10)
        self.ax.set_ylabel('Water Level (L)', color='#bb86fc', fontsize=10)
        self.ax.tick_params(colors='#bb86fc', labelsize=8)
        self.ax.spines['bottom'].set_color('#bb86fc')
        self.ax.spines['left'].set_color('#bb86fc')
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.grid(True, alpha=0.2, color='#bb86fc')
        self.ax.legend(loc='upper right', fontsize=8, facecolor='#2d1b4e', 
                      edgecolor='#bb86fc', labelcolor='#bb86fc')
        
        self.chart_canvas.draw()
        
    def change_mode(self):
        self.control_mode = self.mode_var.get()
        
        # Show/hide relevant panels
        if self.control_mode == 'manual':
            self.manual_frame.pack(padx=10, pady=5, fill=tk.X)
            self.pid_frame.pack_forget()
            self.onoff_frame.pack_forget()
        elif self.control_mode == 'onoff':
            self.manual_frame.pack_forget()
            self.pid_frame.pack_forget()
            self.onoff_frame.pack(padx=10, pady=5, fill=tk.X)
        else:  # pid
            self.manual_frame.pack_forget()
            self.onoff_frame.pack_forget()
            self.pid_frame.pack(padx=10, pady=5, fill=tk.X)
        
        # Reset controllers
        if self.control_mode == 'pid':
            self.pid_controller.reset()
    
    def toggle_pump(self):
        if self.pump.is_on:
            self.pump.turn_off()
            self.pump_btn.config(text="Pump OFF", bg='#cf6679')
        else:
            self.pump.turn_on()
            self.pump_btn.config(text="Pump ON", bg='#00ff00', fg='#000')
    
    def update_setpoint(self, value):
        sp = float(value)
        self.setpoint_label.config(text=f"{sp:.1f} L")
        self.onoff_controller.setpoint = sp
        self.pid_controller.setpoint = sp
    
    def update_pid(self, param, value):
        val = float(value)
        if param == 'kp':
            self.pid_controller.kp = val
        elif param == 'ki':
            self.pid_controller.ki = val
        elif param == 'kd':
            self.pid_controller.kd = val
    
    def update_hysteresis(self, value):
        self.onoff_controller.hysteresis = float(value)
    
    def update_speed(self, value):
        self.speed = int(value)
    
    def start_simulation(self):
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.simulation_loop()
    
    def stop_simulation(self):
        self.running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def reset_simulation(self):
        self.stop_simulation()
        self.tank.current_level = 0
        self.tank.update_height()
        self.pump.turn_off()
        self.time = 0
        self.time_history = []
        self.level_history = []
        self.setpoint_history = []
        self.pump_state_history = []
        self.pid_controller.reset()
        
        self.update_tank_visual()
        self.update_chart()
        self.update_statistics()
        
        if self.control_mode == 'manual':
            self.pump_btn.config(text="Pump OFF", bg='#cf6679', fg='#fff')
    
    def simulation_loop(self):
        if not self.running:
            return
        
        # Control logic
        current_level = self.sensor.read_level()
        
        if self.control_mode == 'onoff':
            action = self.onoff_controller.compute(current_level)
            if action is not None:
                if action:
                    self.pump.turn_on()
                else:
                    self.pump.turn_off()
        
        elif self.control_mode == 'pid':
            pump_intensity = self.pid_controller.compute(current_level, self.dt)
            
            # For simplicity, use threshold-based pump control
            if pump_intensity > 0.5:
                self.pump.turn_on()
            else:
                self.pump.turn_off()
        
        # System dynamics
        inflow = self.pump.get_flow(self.dt)
        outflow = self.outlet_flow * self.dt
        
        self.tank.add_water(inflow)
        self.tank.remove_water(outflow)
        
        # Record data
        self.time += self.dt
        self.time_history.append(self.time)
        self.level_history.append(self.tank.get_level())
        self.setpoint_history.append(self.setpoint_var.get())
        self.pump_state_history.append(self.pump.is_on)
        
        # Limit history length
        max_points = 500
        if len(self.time_history) > max_points:
            self.time_history = self.time_history[-max_points:]
            self.level_history = self.level_history[-max_points:]
            self.setpoint_history = self.setpoint_history[-max_points:]
            self.pump_state_history = self.pump_state_history[-max_points:]
        
        # Update visuals
        self.update_tank_visual()
        self.update_statistics()
        
        # Update chart every 10 ticks
        if len(self.time_history) % 10 == 0:
            self.update_chart()
        
        self.root.after(self.speed, self.simulation_loop)
    
    def update_statistics(self):
        self.stats_labels['time'].config(text=f"{self.time:.1f} s")
        self.stats_labels['level'].config(text=f"{self.tank.get_level():.1f} L")
        self.stats_labels['percent'].config(text=f"{self.tank.get_percentage():.1f}%")
        self.stats_labels['height'].config(text=f"{self.tank.get_height():.1f} cm")
        self.stats_labels['pump'].config(
            text="ON" if self.pump.is_on else "OFF",
            fg='#00ff00' if self.pump.is_on else '#cf6679'
        )
        
        error = self.setpoint_var.get() - self.tank.get_level()
        self.stats_labels['error'].config(text=f"{error:.1f} L")

def main():
    root = tk.Tk()
    app = WaterTankSimulator(root)
    root.mainloop()

if __name__ == "__main__":
    main()
