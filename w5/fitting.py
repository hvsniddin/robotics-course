"""Find motor parameters from recorded encoder angles.

Run from the project folder: .venv/bin/python w5/fitting.py

Read main() at the bottom for the order of the steps.
The important quantities are:
    theta: angle turned by the wheel, in radians
    omega_ss: final speed after acceleration, in radians per second
    T_m: time constant; after this time, speed reaches 63% of its final value
    k_e: voltage divided by speed in our simplified motor model
"""

import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # Save graphs as files without opening a window.
import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import curve_fit

DATA_FOLDER = Path(__file__).resolve().parent
BATTERY_VOLTAGE = 11.2
PWM_LEVELS = range(-100, 101, 5)


def angle_model(time, steady_speed, time_constant):
    """Predicted angle when the wheel starts from rest at time zero."""
    # theta(t) = omega_ss * [t - T_m + T_m * exp(-t / T_m)]
    # expm1(x) means exp(x) - 1, calculated more accurately near zero.
    return steady_speed * (time + time_constant * np.expm1(-time / time_constant))


def load_measurements():
    """Read the three columns: PWM (%), time (ms), angle (degrees)."""
    measurements = np.loadtxt(DATA_FOLDER / 'motor_data_240060.txt', delimiter=',')
    if measurements.shape[1] != 3 or not np.isfinite(measurements).all():
        raise ValueError('Each measurement must contain three valid numbers.')
    if set(measurements[:, 0]) != set(PWM_LEVELS):
        raise ValueError('Expected PWM levels from -100 to +100 in steps of 5.')
    return measurements


def get_wheel_readings(measurements, pwm):
    """Select one PWM run and convert its time and angle to SI units."""
    # Column 0 contains PWM. Keep columns 1 and 2 from the matching rows.
    readings = measurements[measurements[:, 0] == pwm, 1:]

    # Check that the separate file contains the same recorded measurements.
    separate_file = DATA_FOLDER / 'motor_data' / f'wheel_1_v_{pwm}.txt'
    np.testing.assert_array_equal(readings, np.loadtxt(separate_file))

    time = readings[:, 0] / 1000
    angle = np.deg2rad(readings[:, 1])
    if time[0] < 0 or not np.all(np.diff(time) > 0):
        raise ValueError(f'Times must increase and start at or after zero: PWM {pwm}.')

    # Keep the recorded time since switch-on and angle since encoder reset.
    # Subtracting the first sample would remove part of the acceleration.
    return time, angle


def fit_one_run(pwm, time, angle):
    """Find the final speed and time constant that best match one run."""
    angle_change = np.max(angle) - np.min(angle)
    if angle_change <= np.deg2rad(1):
        # A change of at most one encoder degree is treated as no clear movement.
        steady_speed = 0.0
        time_constant = np.nan  # No movement means T_m cannot be determined.
        status = 'no resolved motion'
        fitted_angle = np.zeros_like(angle)
    else:
        # Near the end, angle is almost a straight line: its slope is speed.
        # Use this as a starting guess, then fit all the recorded samples.
        halfway = len(time) // 2
        initial_speed, unused_intercept = np.polyfit(time[halfway:], angle[halfway:], 1)
        initial_guess = [initial_speed, 0.1]

        # curve_fit tries different omega_ss and T_m values to minimize
        # the sum of squared differences between measured and predicted angles.
        # Speed can have either sign; T_m is restricted to 0.001–2 seconds.
        fitted_parameters, uncertainty = curve_fit(
            angle_model,
            time,
            angle,
            p0=initial_guess,
            bounds=([-np.inf, 0.001], [np.inf, 2.0]),
            maxfev=20000,
        )
        steady_speed, time_constant = fitted_parameters
        status = 'fit'
        if time_constant <= 0.00101 or time_constant >= 1.999:
            status = 'bound reached'  # The answer is at an allowed limit.
        fitted_angle = angle_model(time, steady_speed, time_constant)

    angle_errors = angle - fitted_angle
    typical_angle_error = np.sqrt(np.mean(angle_errors ** 2))

    # Keep the existing CSV column names: omega = omega_ss, tau = T_m,
    # and rmse = the root mean square angle error, in radians.
    return {
        'pwm': pwm,
        'voltage': pwm / 100 * BATTERY_VOLTAGE,
        'omega': steady_speed,
        'tau': time_constant,
        'rmse': float(typical_angle_error),
        'samples': len(time),
        'duration': time[-1],
        'median_dt_ms': np.median(np.diff(time)) * 1000,
        'status': status,
    }


def fit_voltage_constant(results):
    """Fit speed = slope x voltage, then calculate k_e = 1 / slope."""
    voltages = []
    speeds = []
    for result in results:
        # Use the chosen range |PWM| >= 20%, away from the low-voltage region.
        # Leave out runs with no movement or a fit at a parameter limit.
        if abs(result['pwm']) >= 20 and result['status'] == 'fit':
            voltages.append(result['voltage'])
            speeds.append(result['omega'])

    voltages = np.array(voltages)
    speeds = np.array(speeds)
    # This is the least-squares formula for a line forced through (0, 0).
    # It minimizes the squared speed errors across all the selected runs.
    slope = np.sum(voltages * speeds) / np.sum(voltages ** 2)
    return 1 / slope


def simulate_step(time, steady_speed, time_constant):
    """Calculate angle and speed from rest using the fitted motor equations."""
    def rates_of_change(current_time, state):
        angle, speed = state
        angle_change_per_second = speed
        speed_change_per_second = (steady_speed - speed) / time_constant
        return [angle_change_per_second, speed_change_per_second]

    # solve_ivp follows these rates of change from the initial [angle, speed].
    solution = solve_ivp(
        rates_of_change,
        (0, time[-1]),
        [0, 0],
        t_eval=time,
        rtol=1e-9,  # Small allowed numerical errors for the simulation.
        atol=1e-11,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    simulated_angle, simulated_speed = solution.y

    # Check the numerical calculation against the known formulas.
    expected_angle = angle_model(time, steady_speed, time_constant)
    expected_speed = -steady_speed * np.expm1(-time / time_constant)
    np.testing.assert_allclose(simulated_angle, expected_angle, rtol=0, atol=1e-7)
    np.testing.assert_allclose(simulated_speed, expected_speed, rtol=0, atol=1e-7)
    return simulated_angle, simulated_speed


def plot_speed_against_voltage(results, voltage_constant):
    """Show the fitted final speeds and the straight-line approximation."""
    voltages = [result['voltage'] for result in results]
    speeds = [result['omega'] for result in results]
    voltage_line = np.linspace(-BATTERY_VOLTAGE, BATTERY_VOLTAGE, 200)
    speed_line = voltage_line / voltage_constant

    figure, axes = plt.subplots(figsize=(9, 5))
    axes.scatter(voltages, speeds, label='Wheel 1: fitted steady-state speed')
    axes.plot(voltage_line, speed_line, '--',
              label=f'Line through zero, |PWM| ≥ 20%: kₑ = {voltage_constant:.4f} V·s/rad')
    # The wheel moved at +/-5% PWM, so the exact dead-zone limits are unknown.
    nearest_moving_voltage = BATTERY_VOLTAGE * 5 / 100
    axes.axvspan(-nearest_moving_voltage, nearest_moving_voltage,
                 color='orange', alpha=.2, label='Dead-zone limits unknown within ±5% PWM')
    axes.axvline(0, color='orange', linewidth=1)
    axes.set(xlabel='Applied voltage U = PWM × 11.2 / 100 (V)',
             ylabel='Steady-state angular velocity (rad/s)',
             title='Default wheel • no external load • 11.2 V battery')
    axes.grid(alpha=.25)
    axes.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(DATA_FOLDER / 'omega_all_wheels.png', dpi=180)
    plt.close(figure)


def plot_step_responses(results, measurements_by_pwm):
    """Draw angle above speed, with +100% on the left and -100% on the right."""
    figure, axes = plt.subplots(2, 2, figsize=(12, 8))
    results_by_pwm = {result['pwm']: result for result in results}

    for column, pwm in enumerate([100, -100]):
        result = results_by_pwm[pwm]
        time, angle = measurements_by_pwm[pwm]
        steady_speed = result['omega']
        time_constant = result['tau']
        smooth_time = np.linspace(0, time[-1], 1000)
        simulated_angle, simulated_speed = simulate_step(smooth_time, steady_speed, time_constant)

        angle_axes = axes[0, column]
        angle_axes.scatter(time, angle, s=12, label='Measured encoder angle')
        angle_axes.plot(smooth_time, simulated_angle, color='coral', label='Simulated motor model')
        angle_axes.set(ylabel='Angle θ (rad)',
                       title=f'{pwm:+d}% PWM: ωss={steady_speed:.3f} rad/s, Tm={time_constant:.4f} s')

        # Change in angle / elapsed time gives average speed between two readings.
        # Place each speed estimate halfway between those readings on the graph.
        measured_speed = np.diff(angle) / np.diff(time)
        midpoint_time = (time[1:] + time[:-1]) / 2
        speed_axes = axes[1, column]
        speed_axes.scatter(midpoint_time, measured_speed, s=16, label='Average speed between readings')
        speed_axes.plot(smooth_time, simulated_speed, color='coral', label='Simulated speed')
        speed_axes.axhline(steady_speed, color='gray', linestyle='--', label='Fitted steady-state speed')
        speed_axes.set(xlim=(0, .4), ylabel='Angular velocity ω (rad/s)')

    for panel in axes.flat:
        panel.set_xlabel('Time since step (s)')
        panel.legend(fontsize=8)
        panel.grid(alpha=.25)
    figure.suptitle('Wheel 1 • 100% PWM in both directions • no external load • 11.2 V')
    figure.tight_layout()
    figure.savefig(DATA_FOLDER / 'step_responses_fit.png', dpi=180)
    plt.close(figure)


def save_results(results):
    """Save every fitted parameter and error value in a CSV table."""
    with (DATA_FOLDER / 'fit_results.csv').open('w', newline='') as output_file:
        writer = csv.DictWriter(output_file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)


def write_report(results, voltage_constant):
    """Put the calculated values into the short lab report."""
    table_lines = []
    results_by_pwm = {result['pwm']: result for result in results}
    forward_time_constant = results_by_pwm[100]['tau']
    reverse_time_constant = results_by_pwm[-100]['tau']
    for result in results:
        if np.isnan(result['tau']):
            time_constant_text = 'N/A'
        else:
            time_constant_text = f"{result['tau']:.4f}"
        table_lines.append(
            f"| {result['pwm']} | **{time_constant_text}** | {result['omega']:.4f} |"
        )
    table = '\n'.join(table_lines)
    report = f'''# Lab 5 — DC motor identification

## Motor parameters

I tested one default wheel without load; no second-wheel measurements are available. At 0% PWM, T_m cannot be determined because the wheel did not move.

| PWM (%) | Wheel 1 T_m (s) | Wheel 1 ω_ss (rad/s) |
|---:|---:|---:|
{table}

## Speed against voltage

> **Identified k_e = {voltage_constant:.5f} V·s/rad** (fit across |PWM| ≥ 20%).

I calculated U = 11.2 × PWM/100 V from the measured battery voltage and fitted ω_ss = U/k_e. The shaded region (−0.56 to +0.56 V) brackets the unresolved dead zone: the wheel already moved at ±5% PWM.

![Wheel 1 speed against voltage, fitted k_e and dead-zone bracket](omega_all_wheels.png)

## Step responses at ±100% PWM

> **Identified T_m: {forward_time_constant:.5f} s at +100% PWM; {reverse_time_constant:.5f} s at −100% PWM.**

![Measured angle, encoder-derived speed and simulated model at ±100% PWM](step_responses_fit.png)

## Discussion

The linear speed–voltage model fits poorly at intermediate PWM, and T_m changes with PWM, so one fixed model does not describe the full range. Friction near zero and the extra load when driving on the floor also limit the model. I cannot quantify the difference between the two wheels because I only measured one. If their speeds differ at equal PWM, the robot will curve, and assuming equal speeds in next week's odometry will cause heading and position errors. Using each wheel's encoder readings accounts for this speed difference, although wheel-size errors and slip will still affect odometry.
'''
    (DATA_FOLDER / 'report.md').write_text(report)


def main():
    # 1. Read the recorded experiment.
    measurements = load_measurements()

    # 2. Find T_m and omega_ss for each PWM level.
    results = []
    measurements_by_pwm = {}
    for pwm in PWM_LEVELS:
        time, angle = get_wheel_readings(measurements, pwm)
        results.append(fit_one_run(pwm, time, angle))
        measurements_by_pwm[pwm] = (time, angle)

    # 3. Find k_e from the relationship between voltage and final speed.
    voltage_constant = fit_voltage_constant(results)

    # 4. Draw the two report figures, including the simulated step responses.
    plot_speed_against_voltage(results, voltage_constant)
    plot_step_responses(results, measurements_by_pwm)

    # 5. Save the parameter table and report.
    save_results(results)
    write_report(results, voltage_constant)
    print(f'Saved the report, parameter table and graphs. k_e = {voltage_constant:.5f} V·s/rad')


if __name__ == '__main__':
    main()
