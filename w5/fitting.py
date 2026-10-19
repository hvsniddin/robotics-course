"""Reproduce Lab 5 fits, ODE comparison, and the Markdown report."""
from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.integrate import solve_ivp

BASE = Path(__file__).resolve().parent
BATTERY_VOLTAGE = 11.2  # Confirmed measured series voltage by the experimenter.


def theta_model(t, w_ss, T_m):
    return w_ss * (t + T_m * np.expm1(-t / T_m))


def main():
    raw = np.loadtxt(BASE / 'motor_data_240060.txt', delimiter=',')
    assert raw.shape[1] == 3 and np.isfinite(raw).all()
    assert set(raw[:, 0]) == set(range(-100, 101, 5))
    rows, traces = [], {}
    for pwm in range(-100, 101, 5):
        data = raw[raw[:, 0] == pwm, 1:]
        split = np.loadtxt(BASE / 'motor_data' / f'wheel_1_v_{pwm}.txt')
        np.testing.assert_array_equal(data, split)
        t, theta = data[:, 0] / 1000, np.deg2rad(data[:, 1])
        assert np.all(np.diff(t) > 0) and t[0] >= 0
        # Preserve time since step and angle since reset, including the first sample.
        stationary = np.ptp(data[:, 1]) <= 1
        if stationary:
            w, tau, status = 0., np.nan, 'no resolved motion'
            pred = np.zeros_like(theta)
        else:
            slope = np.polyfit(t[len(t)//2:], theta[len(t)//2:], 1)[0]
            (w, tau), _ = curve_fit(theta_model, t, theta,
                p0=[slope, .1], bounds=([-np.inf, .001], [np.inf, 2.]), maxfev=20000)
            status = 'bound reached' if tau <= .00101 or tau >= 1.999 else 'fit'
            pred = theta_model(t, w, tau)
        rows.append(dict(pwm=pwm, voltage=pwm / 100 * BATTERY_VOLTAGE,
            omega=w, tau=tau, rmse=float(np.sqrt(np.mean((theta-pred)**2))),
            samples=len(t), duration=t[-1], median_dt_ms=np.median(np.diff(t))*1000, status=status))
        traces[pwm] = (t, theta)
    with (BASE / 'fit_results.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)
    # Predeclared high-excitation range avoids fitting the stationary dead zone.
    moving = [r for r in rows if abs(r['pwm']) >= 20 and r['status'] == 'fit']
    u = np.array([r['voltage'] for r in moving]); w = np.array([r['omega'] for r in moving])
    gain = u @ w / (u @ u); ke = 1 / gain
    rms = np.sqrt(np.mean((w-gain*u)**2))
    directional = {}
    for sign, name in [(-1, 'reverse'), (1, 'forward')]:
        mask = u * sign > 0
        directional[name] = 1 / (u[mask] @ w[mask] / (u[mask] @ u[mask]))
    stopped = [r['pwm'] for r in rows if r['status'] == 'no resolved motion']
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter([r['voltage'] for r in rows], [r['omega'] for r in rows], label='Wheel 1: fitted steady-state speed')
    grid = np.linspace(-11.2, 11.2, 200)
    ax.plot(grid, gain*grid, '--', label=f'Origin fit, |PWM| ≥ 20%: kₑ = {ke:.4f} V·s/rad')
    ax.axvspan(-.56, .56, color='orange', alpha=.2, label='Dead-zone threshold unresolved between ±5% PWM')
    ax.axvline(0, color='orange', linewidth=1)
    ax.set(xlabel='Applied voltage U = PWM × 11.2 / 100 (V)', ylabel='Steady-state angular velocity (rad/s)', title='Default wheel • no external load • 11.2 V battery')
    ax.grid(alpha=.25); ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(BASE / 'omega_all_wheels.png', dpi=180); plt.close(fig)
    r = next(r for r in rows if r['pwm'] == 50)
    t, theta = traces[50]
    fine = np.linspace(0, t[-1], 500)
    sol = solve_ivp(lambda _, y: [y[1], (r['omega']-y[1])/r['tau']],
                    (0, fine[-1]), [0, 0], t_eval=fine, rtol=1e-9, atol=1e-11)
    assert sol.success
    np.testing.assert_allclose(sol.y[0], theta_model(fine, r['omega'], r['tau']), atol=1e-7)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(t, theta, s=12, label='Measured encoder angle')
    ax.plot(fine, sol.y[0], color='coral', label='Numerical first-order ODE simulation')
    ax.set(xlabel='Time since step (s)', ylabel='Angle θ (rad)', title=f'Wheel 1, +50% PWM: ωss={r["omega"]:.3f} rad/s, Tm={r["tau"]:.4f} s')
    ax.legend(); ax.grid(alpha=.25); fig.tight_layout()
    fig.savefig(BASE / 'step_responses_fit.png', dpi=180); plt.close(fig)
    table = '\n'.join(f'| {x["pwm"]} | {x["voltage"]:.2f} | {x["omega"]:.4f} | {x["tau"]:.4f} | {x["rmse"]:.4f} | {x["samples"]} | {x["status"]} |' .replace('nan', 'N/A') for x in rows)
    report = f'''# Lab 5 — DC motor parameter identification

## Aim and selected configuration

Identify the first-order motor dynamics of **one default wheel spinning freely without external load**, using a measured battery voltage of **11.2 V**. The current assignment allows one or both wheels, either size, with or without load; this report covers the selected single-wheel configuration. The two-wheel requirement in the archived `TASK.md` is outdated.

## Experiment and data provenance

The experimenter confirmed that the default wheel spun freely without an external load and that the battery reading was **11.2 V**. The existing dataset is labelled wheel 1; its left/right mounting is not recorded. The consolidated log `motor_data_240060.txt` contains {len(raw)} samples across all 41 PWM levels from −100% to +100%, including zero, in 5% steps. Times are recorded in milliseconds and encoder angles in degrees. The voltage used for each fit is U = 11.2 × PWM/100 V; battery variation during the series was not recorded.

The existing `motor_data/wheel_1_v_*.txt` files are derived splits of the consolidated log, not independently verified original robot files. Every numeric sample in those files was checked against the consolidated log and matches exactly; neither source was modified. The battery sidecar says `battery_voltage_mv: 11.2`, but the experimenter confirmed **volts**, so its unit label is erroneous and has been preserved as received.

Each run contains {min(x['samples'] for x in rows)}–{max(x['samples'] for x in rows)} samples, ending at {min(x['duration'] for x in rows):.3f}–{max(x['duration'] for x in rows):.3f} s. Median sample intervals per run range from {min(x['median_dt_ms'] for x in rows):.2f} to {max(x['median_dt_ms'] for x in rows):.2f} ms, slower than the requested 5 ms target. All timestamps are strictly increasing within each run. The original acquisition program/version that produced this log cannot be verified: the saved `collect_data.qrs` contains a loop condition that prevents acquisition.

## Identification method

Convert t from ms to s and θ from degrees to radians. Keep the recorded time relative to the step and the angle relative to encoder reset; subtracting the first measurement would discard the initial acceleration. This assumes the log uses that acquisition origin; the exact original collector is unavailable. Fit θ(t) = ωss [t − Tm + Tm exp(−t/Tm)] by nonlinear least squares with 0.001 ≤ Tm ≤ 2 s. Runs with an angle range of at most 1° are classified as no resolved motion: ωss is reported as zero and Tm is unidentifiable (N/A). RMSE is calculated in angle space. Parameters are descriptive fits to this series, without independent validation or repeated-trial uncertainty estimates.

Fit ωss = gU through the origin using moving, non-bound fits with |PWM| ≥ 20%, then kₑ = 1/g. This gives **kₑ = {ke:.5f} V·s/rad**, g = {gain:.5f} rad/(s·V), and speed-fit RMSE = {rms:.4f} rad/s. Separate origin fits give {directional['forward']:.5f} V·s/rad forward and {directional['reverse']:.5f} V·s/rad reverse. These effective constants include friction/load effects; the origin-constrained linear model does not represent the dead zone.

## Parameters at every PWM level — wheel 1

| PWM (%) | U (V) | ωss (rad/s) | Tm (s) | Angle RMSE (rad) | Samples | Status |
|---:|---:|---:|---:|---:|---:|---|
{table}

## Speed–voltage characteristic and dead zone

![Steady-state speed against applied voltage](omega_all_wheels.png)

No resolved motion was observed at PWM levels {', '.join(map(str, stopped))}%. Motion is already present at both −5% and +5% (±0.56 V), so a nonzero dead zone is not resolved by the 5% sampling grid. Shading marks the interval between those nearest moving levels as an upper bracket for any dead-zone thresholds, not a measured stationary interval; finer steps around zero would be needed. Wheel 1 denotes the selected default wheel throughout this report.

## Measured and simulated step response

![Measured angle and numerical simulation at +50% PWM](step_responses_fit.png)

At +50% PWM (U = 5.60 V), the fitted values are ωss = {r['omega']:.4f} rad/s and Tm = {r['tau']:.5f} s, with angle RMSE = {r['rmse']:.5f} rad. The simulation integrates dθ/dt = ω and dω/dt = (ωss − ω)/Tm from rest using `solve_ivp`. Its output agrees with the analytical response within 10⁻⁷ rad. This checks the fitted step dynamics on the same data; it is not an independent validation. Using the global kₑ would predict {gain*5.6:.4f} rad/s at this voltage, illustrating the distinction between the per-step fit and global linear approximation.

## Model limitations and odometry (5 sentences)

The measured speed–voltage curve departs from a single straight line, especially at intermediate PWM, while any friction dead zone is unresolved because motion is already present at ±5%. Forward and reverse effective kₑ differ ({directional['forward']:.5f} versus {directional['reverse']:.5f} V·s/rad), and coarse encoder/timing resolution limits the precision of fast transient fits. Battery sag was not tracked during the sweep, and these freely spinning wheel parameters need not describe a robot driving on the floor. The time constant varies with PWM, so one fixed first-order parameter pair cannot reproduce the whole operating range equally well. If the robot's drive-wheel speeds differ at equal PWM, the robot will turn unintentionally, and a pose predictor using identical motor parameters will accumulate heading and position error; encoder-based odometry avoids assuming equal speeds but still depends on correct wheel geometry and slip assumptions.

## Reproduction

Run `python w5/fitting.py` from the repository root (NumPy, SciPy, Matplotlib required). It verifies the split files, regenerates `fit_results.csv`, both report figures and this report, and checks the numerical simulation against the analytical model.

The selected single-wheel experiment is covered at every PWM level. See `README.md` for the file guide and execution checks.
'''
    (BASE / 'report.md').write_text(report)
    print(f'Generated report and plots; wheel 1 k_e={ke:.5f}; no-motion PWM={stopped}')

if __name__ == '__main__':
    main()
