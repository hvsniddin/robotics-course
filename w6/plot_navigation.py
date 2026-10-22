from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_navigation(path):
    """Read comma-separated or whitespace-separated navigation data."""
    with path.open(encoding="utf-8") as source:
        lines = (line.replace(",", " ") for line in source)
        data = np.loadtxt(lines, ndmin=2)
    if data.size == 0 or data.shape[1] != 3:
        raise ValueError("Expected three columns: x (m), y (m), time (ms).")
    if not np.isfinite(data).all():
        raise ValueError("Navigation data contains non-finite values.")
    if np.any(np.diff(data[:, 2]) < 0):
        raise ValueError("Timestamps must be in chronological order.")
    x, y, time_ms = data.T
    return x, y, (time_ms - time_ms[0]) / 1000.0


def display_coordinates(x, y, digit):
    """Apply the same display orientation to real and simulated trajectories."""
    x, y = -x, -y
    if digit == 0:
        x, y = -y, x
    return x, y


def main():
    data_dir = Path(__file__).resolve().parent
    inputs = [data_dir / "nav_data_6.csv", data_dir / "nav_data_0.csv"]
    datasets = [load_navigation(path) for path in inputs]

    fig, axes = plt.subplots(
        1, len(datasets), figsize=(7 * len(datasets), 7),
        squeeze=False, sharex=True, sharey=True, layout="constrained"
    )
    fig.suptitle("Navigation trajectories")

    for trajectory, path, (x, y, elapsed) in zip(axes[0], inputs, datasets):
        digit = int(path.stem.rsplit("_", 1)[1])
        x, y = display_coordinates(x, y, digit)
        trajectory.plot(x, y, color="tab:blue", linewidth=1.5, label="Robot path")
        trajectory.scatter(
            x[0], y[0], color="tab:green", s=70, zorder=3, label="Start"
        )
        trajectory.scatter(
            x[-1], y[-1], color="tab:red", marker="X", s=80, zorder=3, label="End"
        )
        trajectory.set(title=path.name, xlabel="X (m)", ylabel="Y (m)")
        trajectory.set_aspect("equal", adjustable="box")
        trajectory.tick_params(labelleft=True)
        trajectory.grid(True, alpha=0.3)
        trajectory.legend()
        print(f"{path.name}: plotted {len(x)} samples spanning {elapsed[-1]:.2f} s.")

    output = data_dir / "navigation_plot.png"
    fig.savefig(output, dpi=180)
    print(f"Saved plot to: {output.resolve()}")
    plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
