import os
import re
import glob
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

DATA_DIR = Path("motor_data")


def read_data_file(filepath):
    times, positions = [], []
    battery_v = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith("#"):
                if "battery" in line.lower():
                    match = re.search(r"[\d.]+", line)
                    if match:
                        battery_v = float(match.group())
                continue

            parts = line.replace(",", " ").split()
            if len(parts) >= 2:
                try:
                    times.append(float(parts[0]))
                    positions.append(float(parts[1]))
                except ValueError:
                    continue

    return np.array(positions), np.array(times), battery_v


def read_battery(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
    match = re.search(r"[\d.]+", content)
    return float(match.group()) if match else None


def compute_omega(positions, times):
    n = len(positions)
    if n < 4:
        return 0.0

    start = int(n * 0.4)
    dp = positions[-1] - positions[start]
    dt = (times[-1] - times[start]) / 1000.0  # ms to seconds

    return dp / dt if dt > 0 else 0.0


def load_wheel_data(wheel_id):
    battery_file = DATA_DIR / f"wheel_{wheel_id}_battery.txt"
    battery_v = None

    if battery_file.exists():
        battery_v = read_battery(battery_file)

    files = list(DATA_DIR.glob(f"wheel_{wheel_id}_v_*.txt"))
    if not files:
        print(f"No data files found for wheel {wheel_id}")
        return None

    results = []
    for fp in files:
        # Extract PWM percentage from filename
        v_match = re.search(r"_v_(-?\d+)\.txt$", fp.name)
        if not v_match:
            continue
        voltage_pct = int(v_match.group(1))

        positions, times, header_batt = read_data_file(fp)
        if len(positions) < 4:
            continue

        # Fallback to header battery voltage if dedicated file was missing
        effective_battery = battery_v or header_batt or 11.2

        omega = compute_omega(positions, times)
        U_actual = (voltage_pct / 100.0) * effective_battery
        coeff = (U_actual / omega) if omega != 0 else None

        results.append(
            {
                "voltage_pct": voltage_pct,
                "U_actual": U_actual,
                "omega": omega,
                "coeff": coeff,
                "battery_v": effective_battery,
                "positions": positions,
                "times": times,
            }
        )

    results.sort(key=lambda x: x["voltage_pct"])
    return results if results else None


def plot_wheel(wheel_id, results, axs):
    """Plots omega vs PWM % and U/omega coefficients for a given wheel."""
    battery_v = results[0]["battery_v"]
    voltages = [r["voltage_pct"] for r in results]
    omegas = [r["omega"] for r in results]

    # Subplot 1: Omega vs PWM %
    ax1 = axs[0]
    ax1.scatter(voltages, omegas, color="#378ADD", s=40, zorder=3, label="data")

    if len(voltages) > 2:
        coeffs_fit = np.polyfit(voltages, omegas, 1)
        x_fit = np.linspace(min(voltages), max(voltages), 200)
        y_fit = np.polyval(coeffs_fit, x_fit)
        ax1.plot(
            x_fit,
            y_fit,
            color="#E24B4A",
            linewidth=1.5,
            linestyle="--",
            label=f"fit: k={coeffs_fit[0]:.2f}",
        )

    ax1.axhline(0, color="gray", linewidth=0.8, linestyle=":")
    ax1.axvline(0, color="gray", linewidth=0.8, linestyle=":")
    ax1.set_xlabel("PWM Voltage (%)", fontsize=10)
    ax1.set_ylabel("ω (°/s)", fontsize=10)
    ax1.set_title(
        f"Wheel {wheel_id} — ω vs PWM% (Batt: {battery_v:.2f} V)",
        fontsize=11,
    )
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Subplot 2: U/omega Coefficient Bar Chart
    ax2 = axs[1]
    cv = [r["voltage_pct"] for r in results if r["coeff"] is not None]
    cc = [r["coeff"] for r in results if r["coeff"] is not None]

    ax2.bar(cv, cc, color="#1D9E75", width=3.5, zorder=3)
    if cc:
        avg = np.mean(cc)
        ax2.axhline(
            avg,
            color="#E24B4A",
            linewidth=1.5,
            linestyle="--",
            label=f"mean={avg:.5f}",
        )
        ax2.legend(fontsize=9)

    ax2.set_xlabel("PWM Voltage (%)", fontsize=10)
    ax2.set_ylabel("U/ω (V·s/°)", fontsize=10)
    ax2.set_title(f"Wheel {wheel_id} — Coefficient U/ω", fontsize=11)
    ax2.grid(True, alpha=0.3)


def main():
    if not DATA_DIR.exists():
        print(f"Directory '{DATA_DIR}' not found.")
        return

    all_files = list(DATA_DIR.glob("wheel_*_v_*.txt")) + list(
        DATA_DIR.glob("wheel_*_battery.txt")
    )
    wheel_ids = sorted(
        {
            int(f.name.split("_")[1])
            for f in all_files
            if f.name.startswith("wheel_")
        }
    )

    if not wheel_ids:
        print(f"No valid wheel data found in '{DATA_DIR}'")
        return

    print(f"Found wheels: {wheel_ids}")

    n = len(wheel_ids)
    fig, all_axs = plt.subplots(
        n, 2, figsize=(14, 5 * n), squeeze=False
    )
    fig.suptitle(
        "Motor Characteristics — U/ω", fontsize=14, fontweight="bold", y=1.01
    )

    wheel_data_cache = {}

    for i, wid in enumerate(wheel_ids):
        results = load_wheel_data(wid)
        if results is None:
            continue
        wheel_data_cache[wid] = results
        plot_wheel(wid, results, all_axs[i])

    plt.tight_layout()
    out_path = "motor_graphs.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Graph saved to: {out_path}")
    plt.show()

    print("\n=== Mean Coefficients U/ω (V·s/°) ===")
    for wid, results in wheel_data_cache.items():
        coeffs = [r["coeff"] for r in results if r["coeff"] is not None]
        if coeffs:
            print(f"  Wheel {wid}: {np.mean(coeffs):.5f} V·s/°")


if __name__ == "__main__":
    main()