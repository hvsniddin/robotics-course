import re
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

DATA_DIR = Path("motor_data")
COLORS = ["#378ADD", "#1D9E75", "#E24B4A", "#D85A30", "#7F77DD"]


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
    battery_v = read_battery(battery_file) if battery_file.exists() else None

    files = list(DATA_DIR.glob(f"wheel_{wheel_id}_v_*.txt"))
    if not files:
        print(f"No data files found for wheel {wheel_id}")
        return None

    points = []
    effective_battery = battery_v

    for fp in files:
        match = re.search(r"_v_(-?\d+)\.txt$", fp.name)
        if not match:
            continue
        voltage_pct = int(match.group(1))

        positions, times, header_batt = read_data_file(fp)
        if len(positions) < 4:
            continue

        if effective_battery is None and header_batt is not None:
            effective_battery = header_batt

        batt = effective_battery if effective_battery is not None else 11.2

        omega = compute_omega(positions, times)
        U_actual = (voltage_pct / 100.0) * batt
        points.append((U_actual, omega, voltage_pct))

    if not points:
        return None

    points.sort(key=lambda x: x[0])

    return {
        "U": [p[0] for p in points],
        "omega": [p[1] for p in points],
        "voltage_pct": [p[2] for p in points],
        "battery_v": effective_battery or 11.2,
    }


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

    all_wheel_data = {}
    for wid in wheel_ids:
        data = load_wheel_data(wid)
        if data is not None:
            all_wheel_data[wid] = data

    if not all_wheel_data:
        print("No valid data points processed.")
        return

    plt.figure(figsize=(10, 6))

    for i, (wid, d) in enumerate(all_wheel_data.items()):
        color = COLORS[i % len(COLORS)]
        plt.scatter(d["U"], d["omega"], color=color, s=35, zorder=3)
        plt.plot(
            d["U"],
            d["omega"],
            color=color,
            linewidth=1.5,
            alpha=0.85,
            label=f'Wheel {wid} (Batt: {d["battery_v"]:.2f} V)',
        )

    plt.axhline(0, color="gray", linewidth=0.8, linestyle=":")
    plt.axvline(0, color="gray", linewidth=0.8, linestyle=":")
    plt.xlabel("Motor Voltage U (V)", fontsize=11)
    plt.ylabel("Angular Velocity ω (°/s)", fontsize=11)
    plt.title(
        "All Wheels — Angular Velocity ω vs Voltage U",
        fontsize=13,
        fontweight="bold",
    )
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    out_path = "omega_all_wheels.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Saved plot to: {out_path}")
    plt.show()


if __name__ == "__main__":
    main()