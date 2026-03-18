# Adaptive Fuzzy 3D Driving Demo

This project turns an existing hierarchical automotive fuzzy controller into a small 3D classroom-demo simulation.

The fuzzy architecture is preserved exactly as a hierarchy:

1. Collision Risk Engine
2. Lane Stability Engine
3. Comfort / Efficiency Engine
4. Meta Decision Engine

The new work in this demo is the interactive 3D simulation layer, the game-like scene, the HUD, the scenario UI, and the manual / assisted driving modes.

## Chosen Framework

This demo uses **Ursina Engine**.

Why Ursina:

- simplest stable Python path to a real 3D scene
- easy keyboard handling and in-game UI
- good fit for a lightweight academic demo
- avoids heavy engine architecture while still producing a convincing live simulation

## Features

- real-time 3D road scene
- ego vehicle and front vehicle
- chase camera and top-down camera
- scenario selector
- start / pause / reset controls
- three operating modes:
  - `DEMO`
  - `MANUAL`
  - `ASSISTED`
- live fuzzy telemetry on screen
- risk banner and color-coded risk bar
- brake-light feedback
- optional debug sensor guide
- lane centerline visualization toggle

## How The Fuzzy Controller Is Connected

Each frame the simulation:

1. reads scene state
2. computes:
   - ego speed
   - front distance
   - lane deviation
   - steering stability
   - road condition
   - slope
   - traffic density
3. runs the three lower-level fuzzy engines
4. runs the meta decision engine
5. applies throttle, brake, and steering to the vehicle model
6. updates the 3D scene and HUD

The fuzzy engines are kept modular and separate inside `fuzzy_systems/`.

## Project Structure

```text
adaptive_fuzzy_3d_sim/
├── main.py
├── requirements.txt
├── README.md
├── config.py
├── input_controller.py
├── scenario_manager.py
├── simulation_manager.py
├── vehicle.py
├── camera_controller.py
├── hud.py
├── world.py
├── fuzzy_systems/
│   ├── __init__.py
│   ├── common.py
│   ├── risk_engine.py
│   ├── lane_engine.py
│   ├── comfort_engine.py
│   └── meta_engine.py
├── scenarios/
│   ├── __init__.py
│   └── scenario_definitions.py
└── assets/
    └── README.md
```

## Installation

From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you are already using the parent repository virtual environment, you can reuse it.

## Run

```bash
cd adaptive_fuzzy_3d_sim
python3 main.py
```

## Keyboard Controls

- `W` / `Up`: throttle
- `S` / `Down`: brake
- `A` / `Left`: steer left
- `D` / `Right`: steer right
- `Space`: start / pause
- `R`: reset current scenario
- `Tab`: switch mode
- `C`: toggle camera
- `F1`: toggle debug overlays
- `L`: toggle lane center line
- `N`: next scenario
- `B`: previous scenario

## Modes

### DEMO

The fuzzy controller fully drives the ego vehicle.

### MANUAL

The user drives with the keyboard.
The fuzzy system still runs every frame and its outputs are shown live on the HUD.

### ASSISTED

The user drives manually, but the fuzzy system can warn and intervene when risk or lane error becomes too high.

## Scenario Selection

Use the on-screen `Prev` and `Next` buttons or the `B` / `N` keys.

Included scenarios:

- `normal_driving`
- `high_speed_short_distance`
- `large_lane_deviation`
- `poor_road_condition`
- `conflicting_tradeoff`
- `boundary_stop_and_go`
- `boundary_open_road`

## Recommended Demo Flow

1. Start with `normal_driving` in `DEMO` mode.
2. Switch camera once to show the top-down monitoring view.
3. Move to `high_speed_short_distance` and let the audience watch the fuzzy controller brake.
4. Switch to `MANUAL` mode and intentionally drift with `A` / `D`.
5. Switch to `ASSISTED` mode and show how intervention appears when risk rises.
6. Toggle debug overlays to show the front-distance guide.

## Limitations

- vehicle physics are intentionally arcade-style, not a full dynamics simulator
- the road is straight and simplified for demo stability
- traffic uses a lightweight scripted model
- primitive geometry is used instead of custom car assets

These tradeoffs are intentional so the demo remains easy to run, explain, and defend in a university project setting.
