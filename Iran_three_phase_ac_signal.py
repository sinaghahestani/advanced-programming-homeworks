import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Arial'
plt.rcParams['axes.unicode_minus'] = False

V_rms = 220
V_line_rms = V_rms * np.sqrt(3)
frequency = 50
speed_of_light = 3e8

V_peak = V_rms * np.sqrt(2)
V_line_peak = V_line_rms * np.sqrt(2)
period = 1 / frequency
omega = 2 * np.pi * frequency
wavelength = speed_of_light / frequency

phase_shift = 2 * np.pi / 3

time_samples = np.linspace(0, 4 * period, 2000)
voltage_phase_A = V_peak * np.sin(omega * time_samples)
voltage_phase_B = V_peak * np.sin(omega * time_samples - phase_shift)
voltage_phase_C = V_peak * np.sin(omega * time_samples - 2 * phase_shift)

fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

ax1 = fig.add_subplot(gs[0, :])
ax1.plot(time_samples * 1000, voltage_phase_A, 'r-', linewidth=2, label='فاز A (0°)', alpha=0.8)
ax1.plot(time_samples * 1000, voltage_phase_B, 'g-', linewidth=2, label='فاز B (-120°)', alpha=0.8)
ax1.plot(time_samples * 1000, voltage_phase_C, 'b-', linewidth=2, label='فاز C (-240°)', alpha=0.8)
ax1.axhline(y=0, color='k', linestyle='--', linewidth=0.8, alpha=0.5)
ax1.axhline(y=V_peak, color='gray', linestyle=':', linewidth=1, alpha=0.4)
ax1.axhline(y=-V_peak, color='gray', linestyle=':', linewidth=1, alpha=0.4)
ax1.set_xlabel('زمان (میلی‌ثانیه)', fontsize=12)
ax1.set_ylabel('ولتاژ فاز (ولت)', fontsize=12)
ax1.set_title('سیگنال سه‌فاز برق شهری ایران - 220V Phase / 380V Line', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper right', fontsize=11)

ax2 = fig.add_subplot(gs[1, :])
time_single_cycle = np.linspace(0, period, 500)
voltage_A_cycle = V_peak * np.sin(omega * time_single_cycle)
voltage_B_cycle = V_peak * np.sin(omega * time_single_cycle - phase_shift)
voltage_C_cycle = V_peak * np.sin(omega * time_single_cycle - 2 * phase_shift)

ax2.plot(time_single_cycle * 1000, voltage_A_cycle, 'r-', linewidth=2.5, label='فاز A', alpha=0.9)
ax2.plot(time_single_cycle * 1000, voltage_B_cycle, 'g-', linewidth=2.5, label='فاز B', alpha=0.9)
ax2.plot(time_single_cycle * 1000, voltage_C_cycle, 'b-', linewidth=2.5, label='فاز C', alpha=0.9)
ax2.fill_between(time_single_cycle * 1000, voltage_A_cycle, alpha=0.15, color='r')
ax2.fill_between(time_single_cycle * 1000, voltage_B_cycle, alpha=0.15, color='g')
ax2.fill_between(time_single_cycle * 1000, voltage_C_cycle, alpha=0.15, color='b')
ax2.axhline(y=0, color='k', linestyle='--', linewidth=0.8)
ax2.set_xlabel('زمان (میلی‌ثانیه)', fontsize=12)
ax2.set_ylabel('ولتاژ فاز (ولت)', fontsize=12)
ax2.set_title(f'یک سیکل کامل - دوره تناوب = {period*1000:.1f} ms', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend(loc='upper right', fontsize=11)

ax3 = fig.add_subplot(gs[2, 0], projection='polar')
angles = np.linspace(0, 2 * np.pi, 100)
radius = np.ones_like(angles)

ax3.plot([0, 0], [0, 1], 'r-', linewidth=3, label='فاز A (0°)')
ax3.plot([0, -phase_shift], [0, 1], 'g-', linewidth=3, label='فاز B (-120°)')
ax3.plot([0, -2*phase_shift], [0, 1], 'b-', linewidth=3, label='فاز C (-240°)')
ax3.plot(angles, radius, 'k--', linewidth=0.8, alpha=0.3)
ax3.set_ylim(0, 1.2)
ax3.set_title('نمودار فازوری (Phasor)', fontsize=12, fontweight='bold', pad=20)
ax3.legend(loc='upper left', bbox_to_anchor=(1.1, 1.1), fontsize=9)

ax4 = fig.add_subplot(gs[2, 1])
voltage_AB = voltage_phase_A[:500] - voltage_phase_B[:500]
voltage_BC = voltage_phase_B[:500] - voltage_phase_C[:500]
voltage_CA = voltage_phase_C[:500] - voltage_phase_A[:500]

ax4.plot(time_single_cycle * 1000, voltage_AB, 'orange', linewidth=2, label='AB', alpha=0.8)
ax4.plot(time_single_cycle * 1000, voltage_BC, 'purple', linewidth=2, label='BC', alpha=0.8)
ax4.plot(time_single_cycle * 1000, voltage_CA, 'brown', linewidth=2, label='CA', alpha=0.8)
ax4.axhline(y=0, color='k', linestyle='--', linewidth=0.8)
ax4.axhline(y=V_line_peak, color='gray', linestyle=':', linewidth=1, alpha=0.4)
ax4.axhline(y=-V_line_peak, color='gray', linestyle=':', linewidth=1, alpha=0.4)
ax4.set_xlabel('زمان (میلی‌ثانیه)', fontsize=11)
ax4.set_ylabel('ولتاژ خط (ولت)', fontsize=11)
ax4.set_title(f'ولتاژ خط به خط (Line-to-Line)', fontsize=12, fontweight='bold')
ax4.grid(True, alpha=0.3)
ax4.legend(loc='upper right', fontsize=10)

fig.suptitle('سیستم برق سه‌فاز ایران - تحلیل کامل', fontsize=16, fontweight='bold', y=0.995)
plt.show()

print("=" * 70)
print("            مشخصات سیستم برق سه‌فاز ایران")
print("=" * 70)
print(f"{'ولتاژ فاز (Phase RMS)':<35}: {V_rms} V")
print(f"{'ولتاژ خط (Line RMS)':<35}: {V_line_rms:.2f} V")
print(f"{'ولتاژ پیک فاز':<35}: {V_peak:.2f} V")
print(f"{'ولتاژ پیک خط':<35}: {V_line_peak:.2f} V")
print(f"{'نسبت ولتاژ خط به فاز':<35}: √3 = {np.sqrt(3):.4f}")
print("-" * 70)
print(f"{'فرکانس':<35}: {frequency} Hz")
print(f"{'دوره تناوب':<35}: {period*1000:.1f} ms = {period:.4f} s")
print(f"{'فرکانس زاویه‌ای (ω)':<35}: {omega:.2f} rad/s")
print(f"{'اختلاف فاز بین فازها':<35}: 120° = {phase_shift:.4f} rad")
print("-" * 70)
print(f"{'طول موج':<35}: {wavelength/1000:.0f} km")
print(f"{'سرعت نور':<35}: {speed_of_light:.0e} m/s")
print("-" * 70)
print(f"{'نوع سیستم':<35}: Y (Star) متصل")
print(f"{'استاندارد':<35}: IEC 60038")
print("=" * 70)
