"""
Advanced Control Systems Analysis Tool
Author: [Your Name]
Date: 2026-07-04
Description: Interactive tool for analyzing first and second-order systems with
             comprehensive performance metrics and visualization capabilities.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk, messagebox
from scipy import signal
from typing import Tuple, Dict, List
import warnings
warnings.filterwarnings('ignore')


class TransferFunction:
    """Represents a transfer function and handles system type detection."""
    
    def __init__(self, K: float, zeta: float = None, omega_n: float = None, tau: float = None):
        """
        Initialize transfer function.
        
        Args:
            K: System gain
            zeta: Damping ratio (for second-order)
            omega_n: Natural frequency (for second-order)
            tau: Time constant (for first-order)
        """
        self.K = K
        self.zeta = zeta
        self.omega_n = omega_n
        self.tau = tau
        self.order = 1 if tau is not None else 2
        self.sys = self._create_system()
    
    def _create_system(self) -> signal.TransferFunction:
        """Create scipy transfer function object."""
        if self.order == 1:
            num = [self.K]
            den = [self.tau, 1]
        else:
            num = [self.K * self.omega_n**2]
            den = [1, 2 * self.zeta * self.omega_n, self.omega_n**2]
        
        return signal.TransferFunction(num, den)
    
    def get_damping_type(self) -> str:
        """Determine damping type for second-order systems."""
        if self.order == 1:
            return "First-Order"
        
        if self.zeta > 1:
            return "Overdamped"
        elif self.zeta == 1:
            return "Critically Damped"
        elif self.zeta > 0:
            return "Underdamped"
        else:
            return "Unstable"
    
    def get_formula(self) -> str:
        """Return LaTeX-style formula string."""
        if self.order == 1:
            return f"G(s) = {self.K:.2f} / ({self.tau:.2f}s + 1)"
        else:
            return f"G(s) = {self.K * self.omega_n**2:.2f} / (s² + {2*self.zeta*self.omega_n:.2f}s + {self.omega_n**2:.2f})"


class StepResponse:
    """Calculates and stores step response data."""
    
    def __init__(self, tf: TransferFunction, t_final: float = 10):
        """
        Initialize step response calculation.
        
        Args:
            tf: TransferFunction object
            t_final: Final simulation time
        """
        self.tf = tf
        self.t_final = t_final
        self.t, self.y = self._compute_response()
    
    def _compute_response(self) -> Tuple[np.ndarray, np.ndarray]:
        """Compute step response."""
        t = np.linspace(0, self.t_final, 2000)
        t, y = signal.step(self.tf.sys, T=t)
        return t, y


class ImpulseResponse:
    """Calculates and stores impulse response data."""
    
    def __init__(self, tf: TransferFunction, t_final: float = 10):
        self.tf = tf
        self.t_final = t_final
        self.t, self.y = self._compute_response()
    
    def _compute_response(self) -> Tuple[np.ndarray, np.ndarray]:
        """Compute impulse response."""
        t = np.linspace(0, self.t_final, 2000)
        t, y = signal.impulse(self.tf.sys, T=t)
        return t, y


class RampResponse:
    """Calculates and stores ramp response data."""
    
    def __init__(self, tf: TransferFunction, t_final: float = 10):
        self.tf = tf
        self.t_final = t_final
        self.t, self.y = self._compute_response()
    
    def _compute_response(self) -> Tuple[np.ndarray, np.ndarray]:
        """Compute ramp response (step of 1/s^2)."""
        # Ramp = integral of step = step response of G(s)/s
        num = np.polymul(self.tf.sys.num, [1])
        den = np.polymul(self.tf.sys.den, [1, 0])
        ramp_sys = signal.TransferFunction(num, den)
        
        t = np.linspace(0, self.t_final, 2000)
        t, y = signal.step(ramp_sys, T=t)
        return t, y


class PerformanceAnalyzer:
    """Analyzes system performance metrics."""
    
    def __init__(self, step_response: StepResponse):
        """
        Initialize analyzer.
        
        Args:
            step_response: StepResponse object
        """
        self.step = step_response
        self.tf = step_response.tf
        self.metrics = self._calculate_metrics()
    
    def _calculate_metrics(self) -> Dict[str, float]:
        """Calculate all performance metrics."""
        y = self.step.y
        t = self.step.t
        steady_state = y[-1]
        
        metrics = {
            'steady_state': steady_state,
            'rise_time': self._rise_time(t, y, steady_state),
            'settling_time_2': self._settling_time(t, y, steady_state, 0.02),
            'settling_time_5': self._settling_time(t, y, steady_state, 0.05),
            'overshoot': self._overshoot(y, steady_state),
            'peak_time': self._peak_time(t, y),
            'delay_time': self._delay_time(t, y, steady_state),
            'steady_state_error': self._steady_state_error(steady_state)
        }
        
        return metrics
    
    def _rise_time(self, t: np.ndarray, y: np.ndarray, ss: float) -> float:
        """Calculate rise time (10% to 90%)."""
        try:
            idx_10 = np.where(y >= 0.1 * ss)[0][0]
            idx_90 = np.where(y >= 0.9 * ss)[0][0]
            return t[idx_90] - t[idx_10]
        except:
            return np.nan
    
    def _settling_time(self, t: np.ndarray, y: np.ndarray, ss: float, tolerance: float) -> float:
        """Calculate settling time."""
        try:
            error = np.abs(y - ss) / ss
            settled_idx = np.where(error <= tolerance)[0]
            
            # Find last time it exceeds tolerance
            for i in range(len(settled_idx) - 1, 0, -1):
                if settled_idx[i] - settled_idx[i-1] > 50:  # Gap detection
                    return t[settled_idx[i]]
            
            return t[settled_idx[0]]
        except:
            return np.nan
    
    def _overshoot(self, y: np.ndarray, ss: float) -> float:
        """Calculate percent overshoot."""
        try:
            peak = np.max(y)
            if peak > ss:
                return ((peak - ss) / ss) * 100
            return 0.0
        except:
            return np.nan
    
    def _peak_time(self, t: np.ndarray, y: np.ndarray) -> float:
        """Calculate time to peak."""
        try:
            return t[np.argmax(y)]
        except:
            return np.nan
    
    def _delay_time(self, t: np.ndarray, y: np.ndarray, ss: float) -> float:
        """Calculate delay time (50% of steady state)."""
        try:
            idx = np.where(y >= 0.5 * ss)[0][0]
            return t[idx]
        except:
            return np.nan
    
    def _steady_state_error(self, ss: float) -> float:
        """Calculate steady state error for unit step."""
        return abs(1 - ss)
    
    def get_summary(self) -> str:
        """Return formatted summary of metrics."""
        m = self.metrics
        summary = f"""Performance Metrics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rise Time (tr):           {m['rise_time']:.3f} s
Settling Time (2%):       {m['settling_time_2']:.3f} s
Settling Time (5%):       {m['settling_time_5']:.3f} s
Overshoot (Mp):           {m['overshoot']:.2f} %
Peak Time (tp):           {m['peak_time']:.3f} s
Delay Time (td):          {m['delay_time']:.3f} s
Steady State Error:       {m['steady_state_error']:.4f}
Steady State Value:       {m['steady_state']:.4f}
"""
        return summary


class FrequencyAnalyzer:
    """Handles frequency domain analysis (Bode, Nyquist, Root Locus)."""
    
    def __init__(self, tf: TransferFunction):
        self.tf = tf
    
    def bode(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate Bode plot data."""
        w = np.logspace(-2, 2, 500)
        w, mag, phase = signal.bode(self.tf.sys, w)
        return w, mag, phase
    
    def nyquist(self) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate Nyquist plot data."""
        w = np.logspace(-2, 2, 500)
        w, H = signal.freqs(self.tf.sys.num, self.tf.sys.den, worN=w)
        return H.real, H.imag
    
    def root_locus_points(self, K_range: np.ndarray = None) -> List[np.ndarray]:
        """Calculate root locus points for varying gain."""
        if K_range is None:
            K_range = np.linspace(0.1, 10, 100)
        
        poles_list = []
        original_K = self.tf.K
        
        for K in K_range:
            self.tf.K = K
            temp_sys = self.tf._create_system()
            poles = temp_sys.poles
            poles_list.append(poles)
        
        self.tf.K = original_K  # Restore
        return poles_list


class Plotter:
    """Handles all plotting operations."""
    
    def __init__(self, figure: Figure):
        self.fig = figure
        self.systems = []  # Store multiple systems for comparison
    
    def add_system(self, name: str, tf: TransferFunction, color: str):
        """Add a system for comparison plotting."""
        step = StepResponse(tf)
        impulse = ImpulseResponse(tf)
        ramp = RampResponse(tf)
        self.systems.append({
            'name': name,
            'tf': tf,
            'step': step,
            'impulse': impulse,
            'ramp': ramp,
            'color': color
        })
    
    def clear_systems(self):
        """Clear all stored systems."""
        self.systems = []
    
    def plot_time_responses(self):
        """Plot step, impulse, and ramp responses."""
        self.fig.clear()
        
        if not self.systems:
            return
        
        # Create 3 subplots
        ax1 = self.fig.add_subplot(231)
        ax2 = self.fig.add_subplot(232)
        ax3 = self.fig.add_subplot(233)
        
        for sys in self.systems:
            # Step response
            ax1.plot(sys['step'].t, sys['step'].y, 
                    color=sys['color'], label=sys['name'], linewidth=2)
            ax1.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
            ax1.set_xlabel('Time (s)')
            ax1.set_ylabel('Amplitude')
            ax1.set_title('Step Response')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            
            # Impulse response
            ax2.plot(sys['impulse'].t, sys['impulse'].y,
                    color=sys['color'], label=sys['name'], linewidth=2)
            ax2.set_xlabel('Time (s)')
            ax2.set_ylabel('Amplitude')
            ax2.set_title('Impulse Response')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            
            # Ramp response
            ax3.plot(sys['ramp'].t, sys['ramp'].y,
                    color=sys['color'], label=sys['name'], linewidth=2)
            # Ideal ramp
            ax3.plot(sys['ramp'].t, sys['ramp'].t, 'k--', alpha=0.3, label='Ideal')
            ax3.set_xlabel('Time (s)')
            ax3.set_ylabel('Amplitude')
            ax3.set_title('Ramp Response')
            ax3.grid(True, alpha=0.3)
            ax3.legend()
        
        self.fig.tight_layout()
    
    def plot_frequency_responses(self):
        """Plot Bode, Nyquist, and Root Locus."""
        self.fig.clear()
        
        if not self.systems:
            return
        
        ax1 = self.fig.add_subplot(234)  # Bode Magnitude
        ax2 = self.fig.add_subplot(235)  # Bode Phase
        ax3 = self.fig.add_subplot(236)  # Nyquist
        
        for sys in self.systems:
            freq_analyzer = FrequencyAnalyzer(sys['tf'])
            
            # Bode
            w, mag, phase = freq_analyzer.bode()
            ax1.semilogx(w, mag, color=sys['color'], label=sys['name'], linewidth=2)
            ax2.semilogx(w, phase, color=sys['color'], label=sys['name'], linewidth=2)
            
            # Nyquist
            real, imag = freq_analyzer.nyquist()
            ax3.plot(real, imag, color=sys['color'], label=sys['name'], linewidth=2)
            ax3.plot(real, -imag, color=sys['color'], linestyle='--', alpha=0.5)
        
        ax1.set_xlabel('Frequency (rad/s)')
        ax1.set_ylabel('Magnitude (dB)')
        ax1.set_title('Bode - Magnitude')
        ax1.grid(True, which='both', alpha=0.3)
        ax1.legend()
        
        ax2.set_xlabel('Frequency (rad/s)')
        ax2.set_ylabel('Phase (deg)')
        ax2.set_title('Bode - Phase')
        ax2.grid(True, which='both', alpha=0.3)
        ax2.legend()
        
        ax3.axhline(y=0, color='k', linestyle='-', alpha=0.3)
        ax3.axvline(x=0, color='k', linestyle='-', alpha=0.3)
        ax3.plot([-1], [0], 'rx', markersize=10, label='Critical Point')
        ax3.set_xlabel('Real')
        ax3.set_ylabel('Imaginary')
        ax3.set_title('Nyquist Plot')
        ax3.grid(True, alpha=0.3)
        ax3.legend()
        ax3.axis('equal')
        
        self.fig.tight_layout()


class ControlSystemGUI:
    """Main GUI application."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Advanced Control Systems Analysis Tool")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a1a2e')
        
        # State
        self.current_system_order = tk.IntVar(value=2)
        self.comparison_systems = []
        
        # Matplotlib figure
        self.fig = Figure(figsize=(14, 8), facecolor='#16213e')
        
        # Plotter
        self.plotter = Plotter(self.fig)
        
        self._setup_ui()
        self._update_plot()
    
    def _setup_ui(self):
        """Setup user interface."""
        # Main container
        main_frame = tk.Frame(self.root, bg='#1a1a2e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls
        left_panel = tk.Frame(main_frame, bg='#0f3460', width=350)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Right panel - Plot
        right_panel = tk.Frame(main_frame, bg='#16213e')
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self._setup_control_panel(left_panel)
        self._setup_plot_panel(right_panel)
    
    def _setup_control_panel(self, parent):
        """Setup control panel with sliders."""
        # Title
        title = tk.Label(parent, text="System Parameters", 
                        font=('Arial', 16, 'bold'),
                        bg='#0f3460', fg='#e94560')
        title.pack(pady=15)
        
        # System order selection
        order_frame = tk.LabelFrame(parent, text="System Order", 
                                   bg='#0f3460', fg='white',
                                   font=('Arial', 10, 'bold'))
        order_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Radiobutton(order_frame, text="First-Order", variable=self.current_system_order,
                      value=1, command=self._on_order_change,
                      bg='#0f3460', fg='white', selectcolor='#1a1a2e',
                      activebackground='#0f3460', activeforeground='white',
                      font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=5)
        
        tk.Radiobutton(order_frame, text="Second-Order", variable=self.current_system_order,
                      value=2, command=self._on_order_change,
                      bg='#0f3460', fg='white', selectcolor='#1a1a2e',
                      activebackground='#0f3460', activeforeground='white',
                      font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=5)
        
        # Parameters frame
        self.params_frame = tk.Frame(parent, bg='#0f3460')
        self.params_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Create sliders (will be populated based on order)
        self.sliders = {}
        self._create_sliders()
        
        # Transfer function display
        tf_frame = tk.LabelFrame(parent, text="Transfer Function",
                                bg='#0f3460', fg='white',
                                font=('Arial', 10, 'bold'))
        tf_frame.pack(fill=tk.X, padx=15, pady=10)
        
        self.tf_label = tk.Label(tf_frame, text="", 
                                font=('Courier', 9),
                                bg='#1a1a2e', fg='#00ff9f',
                                justify=tk.LEFT, wraplength=300)
        self.tf_label.pack(padx=10, pady=10, fill=tk.X)
        
        # Damping type display
        self.damping_label = tk.Label(tf_frame, text="",
                                     font=('Arial', 10, 'bold'),
                                     bg='#1a1a2e', fg='#e94560')
        self.damping_label.pack(padx=10, pady=(0, 10))
        
        # Performance metrics
        metrics_frame = tk.LabelFrame(parent, text="Performance Metrics",
                                     bg='#0f3460', fg='white',
                                     font=('Arial', 10, 'bold'))
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        self.metrics_text = tk.Text(metrics_frame, height=12, width=35,
                                   bg='#1a1a2e', fg='#00ff9f',
                                   font=('Courier', 9), wrap=tk.WORD)
        self.metrics_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Buttons
        btn_frame = tk.Frame(parent, bg='#0f3460')
        btn_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Button(btn_frame, text="Add to Compare", command=self._add_comparison,
                 bg='#e94560', fg='white', font=('Arial', 10, 'bold'),
                 activebackground='#c23b4f', relief=tk.FLAT).pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="Clear Compare", command=self._clear_comparison,
                 bg='#533483', fg='white', font=('Arial', 10, 'bold'),
                 activebackground='#422866', relief=tk.FLAT).pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="Export Plot", command=self._export_plot,
                 bg='#16537e', fg='white', font=('Arial', 10, 'bold'),
                 activebackground='#114060', relief=tk.FLAT).pack(fill=tk.X, pady=5)
    
    def _create_sliders(self):
        """Create parameter sliders based on system order."""
        # Clear existing sliders
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.sliders.clear()
        
        if self.current_system_order.get() == 1:
            # First-order parameters
            self._create_slider('K', 0.1, 10.0, 1.0, 'Gain')
            self._create_slider('tau', 0.1, 10.0, 1.0, 'Time Constant (τ)')
        else:
            # Second-order parameters
            self._create_slider('K', 0.1, 10.0, 1.0, 'Gain')
            self._create_slider('zeta', 0.0, 2.0, 0.7, 'Damping Ratio (ζ)')
            self._create_slider('omega_n', 0.5, 10.0, 2.0, 'Natural Frequency (ωn)')
    
    def _create_slider(self, param: str, min_val: float, max_val: float, 
                      default: float, label: str):
        """Create a labeled slider."""
        frame = tk.Frame(self.params_frame, bg='#0f3460')
        frame.pack(fill=tk.X, pady=8)
        
        # Label with value
        label_frame = tk.Frame(frame, bg='#0f3460')
        label_frame.pack(fill=tk.X)
        
        tk.Label(label_frame, text=label, 
                bg='#0f3460', fg='white',
                font=('Arial', 9)).pack(side=tk.LEFT)
        
        value_label = tk.Label(label_frame, text=f"{default:.2f}",
                              bg='#0f3460', fg='#00ff9f',
                              font=('Arial', 9, 'bold'))
        value_label.pack(side=tk.RIGHT)
        
        # Slider
        slider = tk.Scale(frame, from_=min_val, to=max_val, resolution=0.01,
                         orient=tk.HORIZONTAL, bg='#1a1a2e', fg='white',
                         troughcolor='#533483', activebackground='#e94560',
                         highlightthickness=0, showvalue=False,
                         command=lambda v, p=param, l=value_label: self._on_slider_change(p, v, l))
        slider.set(default)
        slider.pack(fill=tk.X)
        
        self.sliders[param] = {'slider': slider, 'label': value_label}
    
    def _on_slider_change(self, param: str, value: str, label: tk.Label):
        """Handle slider value change."""
        label.config(text=f"{float(value):.2f}")
        self._update_plot()
    
    def _on_order_change(self):
        """Handle system order change."""
        self._create_sliders()
        self._update_plot()
    
    def _get_current_tf(self) -> TransferFunction:
        """Get transfer function from current slider values."""
        if self.current_system_order.get() == 1:
            K = self.sliders['K']['slider'].get()
            tau = self.sliders['tau']['slider'].get()
            return TransferFunction(K=K, tau=tau)
        else:
            K = self.sliders['K']['slider'].get()
            zeta = self.sliders['zeta']['slider'].get()
            omega_n = self.sliders['omega_n']['slider'].get()
            return TransferFunction(K=K, zeta=zeta, omega_n=omega_n)
    
    def _update_plot(self):
        """Update plot with current parameters."""
        tf = self._get_current_tf()
        
        # Update transfer function display
        self.tf_label.config(text=tf.get_formula())
        self.damping_label.config(text=f"Type: {tf.get_damping_type()}")
        
        # Update plotter
        self.plotter.clear_systems()
        self.plotter.add_system("Current", tf, '#e94560')
        
        # Add comparison systems
        colors = ['#00ff9f', '#f39c12', '#8e44ad', '#3498db']
        for i, comp_tf in enumerate(self.comparison_systems):
            self.plotter.add_system(f"Compare {i+1}", comp_tf, colors[i % len(colors)])
        
        # Update plots based on current view
        if hasattr(self, 'view_var'):
            if self.view_var.get() == 'time':
                self.plotter.plot_time_responses()
            else:
                self.plotter.plot_frequency_responses()
        else:
            self.plotter.plot_time_responses()
        
        self.canvas.draw()
        
        # Update metrics
        step = StepResponse(tf)
        analyzer = PerformanceAnalyzer(step)
        self.metrics_text.delete('1.0', tk.END)
        self.metrics_text.insert('1.0', analyzer.get_summary())
    
    def _setup_plot_panel(self, parent):
        """Setup matplotlib canvas."""
        # View selector
        view_frame = tk.Frame(parent, bg='#16213e')
        view_frame.pack(fill=tk.X, pady=5)
        
        self.view_var = tk.StringVar(value='time')
        
        tk.Radiobutton(view_frame, text="Time Domain", variable=self.view_var,
                      value='time', command=self._update_plot,
                      bg='#16213e', fg='white', selectcolor='#0f3460',
                      activebackground='#16213e', activeforeground='white',
                      font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=20)
        
        tk.Radiobutton(view_frame, text="Frequency Domain", variable=self.view_var,
                      value='freq', command=self._update_plot,
                      bg='#16213e', fg='white', selectcolor='#0f3460',
                      activebackground='#16213e', activeforeground='white',
                      font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=20)
        
        # Canvas
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _add_comparison(self):
        """Add current system to comparison list."""
        if len(self.comparison_systems) >= 4:
            messagebox.showwarning("Limit Reached", "Maximum 4 systems for comparison")
            return
        
        tf = self._get_current_tf()
        self.comparison_systems.append(tf)
        self._update_plot()
        messagebox.showinfo("Added", f"System added to comparison ({len(self.comparison_systems)}/4)")
    
    def _clear_comparison(self):
        """Clear all comparison systems."""
        self.comparison_systems.clear()
        self._update_plot()
        messagebox.showinfo("Cleared", "Comparison list cleared")
    
    def _export_plot(self):
        """Export current plot to PNG."""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if filename:
            self.fig.savefig(filename, dpi=300, facecolor='#16213e')
            messagebox.showinfo("Exported", f"Plot saved to {filename}")


def main():
    """Main entry point."""
    root = tk.Tk()
    app = ControlSystemGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
