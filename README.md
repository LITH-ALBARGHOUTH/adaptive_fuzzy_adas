# Hierarchical Fuzzy Driving Simulation

This project provides a complete time-based driving simulation wrapped around an existing hierarchical fuzzy driver-assistance system.

The fuzzy hierarchy remains unchanged:

1. Collision Risk Engine
2. Lane Stability Engine
3. Comfort / Efficiency Engine
4. Meta Decision Engine

The work in this repository focuses on simulation, scenario management, CLI execution, logging, summaries, and matplotlib-based visualization.

## What The Simulation Does

At each time step the simulator:

1. Computes current sensor inputs from the ego vehicle, front vehicle, and environment
2. Calls the three lower-level fuzzy engines
3. Calls the meta fuzzy engine
4. Applies simple actuator arbitration to reduce unrealistic throttle/brake overlap
5. Updates ego vehicle motion using:
   - `acceleration = throttle_gain * throttle - brake_gain * brake`
   - `speed = max(0, speed + acceleration * dt)`
   - `x_position = x_position + speed * dt`
   - `y_position = y_position + steering * dt`
6. Updates front-vehicle motion
7. Logs all values for reporting and plotting

## State Model

Ego vehicle state:

- `x_position` in meters
- `y_position` in meters
- `speed` in meters per second

Front vehicle state:

- `x_front` in meters
- `speed_front` in meters per second

Environment:

- `road_condition` in `[0, 1]`
- `slope`
- `traffic_density` in `[0, 1]`

## Scenarios

The project includes seven predefined scenarios:

- `normal_driving`
- `high_speed_short_distance`
- `large_lane_deviation`
- `poor_road_condition`
- `conflicting_tradeoff`
- `boundary_stop_and_go`
- `boundary_open_road`

Each scenario defines:

- initial ego state
- initial front vehicle state
- initial environment state
- front-vehicle behavior over time
- environment changes over time
- lateral disturbance over time

## CLI Modes

Run all scenarios:

```bash
python3 main.py
```

The default run generates scenario plots under `outputs/generated_figures/`.

Run a single scenario:

```bash
python3 main.py --scenario conflicting_tradeoff
```

Run scenarios without saving plots:

```bash
python3 main.py --skip-plots
```

Run the required interactive one-shot evaluation mode:

```bash
python3 main.py --interactive
```

Interactive mode prompts for:

- speed
- distance
- lane deviation
- road condition

It then runs one full fuzzy evaluation and prints:

- subsystem outputs
- throttle
- brake
- steering

## Output

For each scenario the program prints:

- initial inputs
- subsystem outputs from the first time step
- final control outputs
- a short interpretation string
- summary metrics

Summary metrics include:

- final speed
- minimum distance
- maximum risk
- RMS lane deviation
- collision flag
- lane departure flag

## Plots

For every scenario the simulation saves:

1. speed vs time
2. distance vs time
3. risk vs time
4. lane deviation vs time
5. control signals vs time

When multiple scenarios are run together, the program also saves a comparison figure.

Plots are written to:

```text
outputs/generated_figures/
```

## Project Layout

```text
adaptive_fuzzy_adas/
├── main.py
├── requirements.txt
├── README.md
├── config.py
├── simulation.py
├── scenarios.py
├── utils.py
├── fuzzy_systems/
│   ├── __init__.py
│   ├── common.py
│   ├── risk_engine.py
│   ├── lane_engine.py
│   ├── comfort_engine.py
│   └── meta_engine.py
├── visualization/
│   ├── __init__.py
│   ├── scenario_plots.py
│   ├── membership_plots.py
│   ├── surface_plots.py
│   ├── rule_activation.py
│   └── defuzzification_plot.py
└── outputs/
    └── generated_figures/
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Notes

- The fuzzy engines are intentionally kept hierarchical and separate.
- The simulation layer converts ego speed from m/s to km/h before calling the existing fuzzy engines because their universes are defined in automotive km/h ranges.
- The project is written to stay simple, explainable, and runnable in a university-project setting.
