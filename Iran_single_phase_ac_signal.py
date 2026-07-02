import numpy as np
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Arial'
plt.rcParams['axes.unicode_minus'] = False

V_rms = 220
frequency = 50
speed_of_light = 3e8

V_peak = V_rms * np.sqrt(2)
V_peak_to_peak = 2 * V_peak
period = 1 / frequency
omega = 2 * np.pi * frequency
wavelength = speed_of_light / frequency

time_samples = np.linspace(0, 4 * period, 2000)
voltage_signal = V_peak * np.sin(omega * time_samples)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
fig.suptitle('سیگنال برق شهری ایران - AC 220V, 50Hz', fontsize=16, fontweight='bold')

ax1.plot(time_samples * 1000, voltage_signal, 'b-', linewidth=2, label='سیگنال ولتاژ')
ax1.axhline(y=0, color='k', linestyle='--', linewidth=0.8, alpha=0.5)
ax1.axhline(y=V_peak, color='r', linestyle=':', linewidth=1, alpha=0.7, label=f'پیک: {V_peak:.2f} V')
ax1.axhline(y=-V_peak, color='r', linestyle=':', linewidth=1, alpha=0.7)
ax1.axhline(y=V_rms, color='g', linestyle='-.', linewidth=1, alpha=0.7, label=f'RMS: {V_rms} V')
ax1.axhline(y=-V_rms, color='g', linestyle='-.', linewidth=1, alpha=0.7)
ax1.set_xlabel('زمان (میلی‌ثانیه)', fontsize=12)
ax1.set_ylabel('ولتاژ (ولت)', fontsize=12)
ax1.set_title('سیگنال کامل', fontsize=13, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper right')

time_single_cycle = np.linspace(0, period, 500)
voltage_single_cycle = V_peak * np.sin(omega * time_single_cycle)

ax2.plot(time_single_cycle * 1000, voltage_single_cycle, 'b-', linewidth=2.5)
ax2.fill_between(time_single_cycle * 1000, voltage_single_cycle, alpha=0.3)
ax2.axhline(y=0, color='k', linestyle='--', linewidth=0.8)
ax2.set_xlabel('زمان (میلی‌ثانیه)', fontsize=12)
ax2.set_ylabel('ولتاژ (ولت)', fontsize=12)
ax2.set_title(f'یک سیکل کامل - دوره ثابت = {period*1000:.1f} ms', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

print("=" * 60)
print("             مشخصات سیگنال برق شهری ایران")
print("=" * 60)
print(f"{'ولتاژ اثر (RMS)':<30}: {V_rms:.2f} V")
print(f"{'ولتاژ پیک':<30}: {V_peak:.2f} V")
print(f"{'دامنه (peak-to-peak)':<30}: {V_peak_to_peak:.2f} V")
print(f"{'فرکانس':<30}: {frequency} Hz")
print(f"{'دوره لرزش (Period)':<30}: {period*1000:.1f} ms = {period:.3f} s")
print(f"{'فرکانس زاویه‌ای (ω)':<30}: {omega:.2f} rad/s")
print(f"{'طول موج':<30}: {wavelength/1000:.0f} km")
print("=" * 60)
