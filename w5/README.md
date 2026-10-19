# Week 5 / Lab 5 — default wheel without load

[report.md](report.md) contains the completed analysis for the chosen configuration: **one default wheel, freely spinning without external load, battery 11.2 V**. The current assignment permits this configuration; a second wheel is not required. `TASK.md` preserves the original brief with the scope clarification at the top.

## Report contents

- All 41 PWM levels (−100% to +100%, in 5% steps), with T_m, steady-state speed, angle RMSE and sample counts.
- Speed versus applied voltage in SI units, fitted k_e and the unresolved dead-zone threshold bracket.
- Measured angle and numerical first-order ODE simulation at +50% PWM.
- Discussion of nonlinear behavior, direction asymmetry, sampling limitations and odometry.

## Reproduce

From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r w5/requirements.txt
.venv/bin/python w5/build_submission.py
```

`build_submission.py` runs the legacy plotting scripts in a temporary directory, checks the preserved split samples against the original log, then runs `fitting.py` to generate the authoritative report figures and table. It verifies source-data hashes, report image links and archive integrity, writes `verification.txt`, and builds `Lab5_submission.zip` with a `Lab5/` folder. No original measurements are overwritten. The standalone analysis command is `.venv/bin/python w5/fitting.py`.

## File guide

| File | Purpose |
|---|---|
| `report.md` | Main submission report |
| `fit_results.csv` | Parameters and diagnostics for every PWM |
| `omega_all_wheels.png` | Selected wheel's voltage characteristic; filename retained for compatibility |
| `step_responses_fit.png` | Measured and numerically simulated angle |
| `motor_data_240060.txt` | Preserved consolidated measurement log |
| `motor_data/` | Existing splits, checked sample-for-sample against the log |
| `fitting.py` | Authoritative analysis and report generator |
| `requirements.txt` | Analysis dependencies |
| `collect_data.qrs` | Original saved project, preserved unchanged |
| `plot.py`, `plot_omega.py`, `motor_graphs.png` | Earlier processing/degree-based exploratory plots |
