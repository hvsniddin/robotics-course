"""Compare real-robot and simulator odometry for digits 6 and 0.

Run: python3 w6/analysis.py
Input columns: x (metres), y (metres), timestamp (milliseconds).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from plot_navigation import display_coordinates, load_navigation


def position_difference(real, simulated):
    """Compare at real sample times within the overlap, including its endpoint."""
    xr, yr, tr = real
    xs, ys, ts = simulated
    for times in (tr, ts):
        if len(times) < 2 or np.any(np.diff(times) <= 0):
            raise ValueError("Comparison requires at least two strictly increasing timestamps.")

    end = min(tr[-1], ts[-1])
    times = np.unique(np.append(tr[tr <= end], end))
    dx = np.interp(times, tr, xr) - np.interp(times, ts, xs)
    dy = np.interp(times, tr, yr) - np.interp(times, ts, ys)
    return times, np.hypot(dx, dy)


def path_length(data):
    x, y, _ = data
    return np.hypot(np.diff(x), np.diff(y)).sum()


def main():
    data_dir = Path(__file__).resolve().parent
    digits = (6, 0)
    trajectory_fig, trajectory_axes = plt.subplots(
        1, 2, figsize=(12, 7), layout="constrained"
    )
    error_fig, error_axes = plt.subplots(
        1, 2, figsize=(12, 4), layout="constrained"
    )
    trajectory_fig.suptitle("Real robot vs simulator — odometry trajectories")
    error_fig.suptitle("Position difference at matched elapsed times")
    summary = [
        "REAL ROBOT VS SIMULATOR — ODOMETRY COMPARISON",
        "",
        "Each clock is reset to its first logged sample; times are in seconds.",
        "Positions retain their recorded origins, scale and heading.",
        "Display rotations are applied equally to real and simulated data.",
        "Simulation is interpolated onto real timestamps within the shared duration.",
        "The exact overlap endpoint is included; no extrapolation is used.",
        "Mean and RMSE use these comparison samples (not time-weighted).",
        "Differences include timing/speed differences, not just path shape.",
        "Simulator odometry is a reference, not measured ground truth.",
    ]

    for digit, trajectory_ax, error_ax in zip(digits, trajectory_axes, error_axes):
        real = load_navigation(data_dir / f"data/nav_data_{digit}.csv")
        simulated = load_navigation(data_dir / f"data/nav_data_{digit}_sim.csv")
        times, error = position_difference(real, simulated)

        for data, label, color, style in (
            (real, "Real robot", "tab:blue", "-"),
            (simulated, "Simulator", "tab:orange", "--"),
        ):
            x, y = display_coordinates(data[0], data[1], digit)
            trajectory_ax.plot(x, y, style, color=color, label=label)
            trajectory_ax.scatter(
                x[0], y[0], color=color, marker="o", s=45, zorder=3,
                label=f"{label} start",
            )
            trajectory_ax.scatter(
                x[-1], y[-1], color=color, marker="X", s=65, zorder=3,
                label=f"{label} end",
            )
        trajectory_ax.set(title=f"Digit {digit}", xlabel="X (m)", ylabel="Y (m)")
        trajectory_ax.set_aspect("equal", adjustable="box")
        trajectory_ax.legend(fontsize=8)
        trajectory_ax.grid(True, alpha=0.3)

        error_ax.plot(times, error, color="tab:red")
        error_ax.set(
            title=f"Digit {digit}", xlabel="Elapsed time (s)",
            ylabel="Position difference (m)",
        )
        error_ax.grid(True, alpha=0.3)
        endpoint_gap = np.hypot(
            real[0][-1] - simulated[0][-1], real[1][-1] - simulated[1][-1]
        )
        summary.extend([
            "",
            f"Digit {digit}",
            f"  Samples: real {len(real[0])}, simulator {len(simulated[0])}",
            f"  Duration: real {real[2][-1]:.3f} s, simulator {simulated[2][-1]:.3f} s",
            f"  Path length: real {path_length(real):.3f} m, simulator {path_length(simulated):.3f} m",
            f"  Shared time interval: 0 to {times[-1]:.3f} s",
            f"  Mean position difference: {error.mean():.3f} m",
            f"  Position RMSE: {np.sqrt(np.mean(error ** 2)):.3f} m",
            f"  Maximum position difference: {error.max():.3f} m",
            f"  Position difference at overlap end: {error[-1]:.3f} m",
            f"  Endpoint separation (different finish times): {endpoint_gap:.3f} m",
        ])

    for fig, name in (
        (trajectory_fig, "plots/trajectory_comparison.png"),
        (error_fig, "plots/position_difference.png"),
    ):
        fig.savefig(data_dir / name, dpi=180)
    report = "\n".join(summary) + "\n"
    (data_dir / "comparison_summary.txt").write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved comparison plots and summary to {data_dir}")
    plt.show()
    plt.close(trajectory_fig)
    plt.close(error_fig)


if __name__ == "__main__":
    main()
