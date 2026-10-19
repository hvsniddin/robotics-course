# Lab 5 — DC motor parameter identification

## Aim and selected configuration

Identify the first-order motor dynamics of **one default wheel spinning freely without external load**, using a measured battery voltage of **11.2 V**. The current assignment allows one or both wheels, either size, with or without load; this report covers the selected single-wheel configuration. The two-wheel requirement in the archived `TASK.md` is outdated.

## Experiment and data provenance

The experimenter confirmed that the default wheel spun freely without an external load and that the battery reading was **11.2 V**. The existing dataset is labelled wheel 1; its left/right mounting is not recorded. The consolidated log `motor_data_240060.txt` contains 2655 samples across all 41 PWM levels from −100% to +100%, including zero, in 5% steps. Times are recorded in milliseconds and encoder angles in degrees. The voltage used for each fit is U = 11.2 × PWM/100 V; battery variation during the series was not recorded.

The existing `motor_data/wheel_1_v_*.txt` files are derived splits of the consolidated log, not independently verified original robot files. Every numeric sample in those files was checked against the consolidated log and matches exactly; neither source was modified.

Each run contains 54–68 samples, ending at 2.000–2.031 s. Median sample intervals per run range from 29.86 to 38.42 ms, slower than the requested 5 ms target. This is because writing data to a file takes time and the program was run in python instead which makes it more slower.

## Identification method

Convert t from ms to s and θ from degrees to radians. Keep the recorded time relative to the step and the angle relative to encoder reset; subtracting the first measurement would discard the initial acceleration. This assumes the log uses that acquisition origin; the exact original collector is unavailable. Fit $θ(t) = ω_{ss} [t − T_m + T_m * exp(−t/T_m)]$ by nonlinear least squares with 0.001 ≤ Tm ≤ 2 s. Runs with an angle range of at most 1° are classified as no resolved motion: ωss is reported as zero and Tm is unidentifiable (N/A). RMSE is calculated in angle space. Parameters are descriptive fits to this series, without independent validation or repeated-trial uncertainty estimates.

Fit ωss = gU through the origin using moving, non-bound fits with |PWM| ≥ 20%, then kₑ = 1/g. This gives **kₑ = 0.71550 V·s/rad**, g = 1.39763 rad/(s·V), and speed-fit RMSE = 1.3360 rad/s. Separate origin fits give 0.68721 V·s/rad forward and 0.74621 V·s/rad reverse. These effective constants include friction/load effects; the origin-constrained linear model does not represent the dead zone.

## Parameters at every PWM level — wheel 1

| PWM (%) | U (V) | ωss (rad/s) | Tm (s) | Angle RMSE (rad) | Samples | Status |
|---:|---:|---:|---:|---:|---:|---|
| -100 | -11.20 | -13.7768 | 0.0435 | 0.0148 | 54 | fit |
| -95 | -10.64 | -13.3303 | 0.0677 | 0.0201 | 67 | fit |
| -90 | -10.08 | -12.5399 | 0.0731 | 0.0107 | 67 | fit |
| -85 | -9.52 | -11.8155 | 0.0836 | 0.0227 | 67 | fit |
| -80 | -8.96 | -11.5077 | 0.1100 | 0.0149 | 65 | fit |
| -75 | -8.40 | -11.0926 | 0.1258 | 0.0141 | 68 | fit |
| -70 | -7.84 | -10.3378 | 0.1432 | 0.0107 | 67 | fit |
| -65 | -7.28 | -9.6250 | 0.1713 | 0.0135 | 67 | fit |
| -60 | -6.72 | -9.3396 | 0.1676 | 0.0210 | 65 | fit |
| -55 | -6.16 | -8.8527 | 0.2050 | 0.0154 | 67 | fit |
| -50 | -5.60 | -8.4879 | 0.1930 | 0.0150 | 67 | fit |
| -45 | -5.04 | -8.1137 | 0.2080 | 0.0110 | 67 | fit |
| -40 | -4.48 | -7.7769 | 0.2078 | 0.0093 | 66 | fit |
| -35 | -3.92 | -7.3778 | 0.2223 | 0.0218 | 54 | fit |
| -30 | -3.36 | -6.2951 | 0.2403 | 0.0221 | 56 | fit |
| -25 | -2.80 | -5.7365 | 0.2783 | 0.0147 | 62 | fit |
| -20 | -2.24 | -4.9688 | 0.2911 | 0.0163 | 61 | fit |
| -15 | -1.68 | -4.3034 | 0.2902 | 0.0139 | 63 | fit |
| -10 | -1.12 | -3.4786 | 0.2857 | 0.0110 | 64 | fit |
| -5 | -0.56 | -1.2527 | 0.1875 | 0.0079 | 62 | fit |
| 0 | 0.00 | 0.0000 | N/A | 0.0000 | 66 | no resolved motion |
| 5 | 0.56 | 1.2577 | 0.2218 | 0.0096 | 59 | fit |
| 10 | 1.12 | 3.7726 | 0.3263 | 0.0142 | 65 | fit |
| 15 | 1.68 | 4.6407 | 0.2859 | 0.0153 | 66 | fit |
| 20 | 2.24 | 5.4906 | 0.2991 | 0.0090 | 67 | fit |
| 25 | 2.80 | 6.2021 | 0.2879 | 0.0144 | 67 | fit |
| 30 | 3.36 | 6.7612 | 0.2458 | 0.0131 | 67 | fit |
| 35 | 3.92 | 7.8997 | 0.2238 | 0.0089 | 66 | fit |
| 40 | 4.48 | 8.3571 | 0.2077 | 0.0097 | 66 | fit |
| 45 | 5.04 | 8.6677 | 0.1933 | 0.0123 | 68 | fit |
| 50 | 5.60 | 9.1027 | 0.1994 | 0.0108 | 68 | fit |
| 55 | 6.16 | 9.4113 | 0.1858 | 0.0140 | 61 | fit |
| 60 | 6.72 | 9.9746 | 0.1648 | 0.0144 | 68 | fit |
| 65 | 7.28 | 10.2566 | 0.1582 | 0.0287 | 67 | fit |
| 70 | 7.84 | 11.1225 | 0.0958 | 0.0336 | 65 | fit |
| 75 | 8.40 | 12.0486 | 0.1328 | 0.0116 | 67 | fit |
| 80 | 8.96 | 12.5118 | 0.1059 | 0.0130 | 68 | fit |
| 85 | 9.52 | 12.8993 | 0.1010 | 0.0162 | 67 | fit |
| 90 | 10.08 | 13.7100 | 0.0721 | 0.0181 | 65 | fit |
| 95 | 10.64 | 14.6708 | 0.0602 | 0.0192 | 62 | fit |
| 100 | 11.20 | 15.2292 | 0.0419 | 0.0335 | 64 | fit |

## Speed–voltage characteristic and dead zone

![Steady-state speed against applied voltage](omega_all_wheels.png)

No resolved motion was observed at PWM levels 0%. Motion is already present at both −5% and +5% (±0.56 V), so a nonzero dead zone is not resolved by the 5% sampling grid. Shading marks the interval between those nearest moving levels as an upper bracket for any dead-zone thresholds, not a measured stationary interval; finer steps around zero would be needed. Wheel 1 denotes the selected default wheel throughout this report.

## Measured and simulated step response

![Measured angle and numerical simulation at +50% PWM](step_responses_fit.png)

At +50% PWM (U = 5.60 V), the fitted values are ωss = 9.1027 rad/s and Tm = 0.19940 s, with angle RMSE = 0.01083 rad. The simulation integrates dθ/dt = ω and dω/dt = (ωss − ω)/Tm from rest using `solve_ivp`. Its output agrees with the analytical response within 10⁻⁷ rad. This checks the fitted step dynamics on the same data; it is not an independent validation. Using the global kₑ would predict 7.8267 rad/s at this voltage, illustrating the distinction between the per-step fit and global linear approximation.

## Model limitations and odometry (5 sentences)

The measured speed–voltage curve departs from a single straight line, especially at intermediate PWM, while any friction dead zone is unresolved because motion is already present at ±5%. Forward and reverse effective kₑ differ (0.68721 versus 0.74621 V·s/rad), and coarse encoder/timing resolution limits the precision of fast transient fits. Battery sag was not tracked during the sweep, and these freely spinning wheel parameters need not describe a robot driving on the floor. The time constant varies with PWM, so one fixed first-order parameter pair cannot reproduce the whole operating range equally well. If the robot's drive-wheel speeds differ at equal PWM, the robot will turn unintentionally, and a pose predictor using identical motor parameters will accumulate heading and position error; encoder-based odometry avoids assuming equal speeds but still depends on correct wheel geometry and slip assumptions.

## Reproduction

Run `python w5/fitting.py` from the repository root (NumPy, SciPy, Matplotlib required). It verifies the split files, regenerates `fit_results.csv`, both report figures and this report, and checks the numerical simulation against the analytical model.

The selected single-wheel experiment is covered at every PWM level. See `README.md` for the file guide and execution checks.
