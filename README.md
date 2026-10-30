# Weber Smoker Conversion with Thermal Simulator

A data-driven engineering project to convert a Weber smoker to electrically controlled operation, characterize its real thermal behavior, and develop an experimentally validated thermal simulator and temperature-control system.

The project combines:

- Chef iQ CQ60 Bluetooth temperature probes
- Bluetooth Low Energy (BLE) data acquisition
- Per-probe experimental data recording
- Session-based experiment management
- Real-world Weber thermal testing
- Physics-based thermal simulation
- Parameter calibration from measured data
- Heater-power and steady-state prediction
- Automated testing
- Future closed-loop temperature control

---

## Project Status

**Current development version: V3.1**

The project has progressed from basic BLE discovery into a data-driven thermal modeling system.

### Completed Milestones

- [x] Discover Chef iQ CQ60 BLE advertisements
- [x] Decode CQ60 manufacturer data
- [x] Identify individual physical probes
- [x] Capture raw probe temperature measurements
- [x] Associate physical probes with configurable friendly names
- [x] Design per-probe CSV recording
- [x] Introduce session-based experiment recording
- [x] Complete first controlled Weber heating experiment
- [x] Implement initial two-node thermal model
- [x] Implement model calibration framework
- [x] Implement heater-power prediction framework
- [x] Introduce automated simulator tests

### Current Objective

Calibrate and validate the thermal simulator against controlled physical experiments before implementing closed-loop smoker control.

---

# System Architecture

The project is divided into two major subsystems:

```text
Chef iQ CQ60 Probes
        │
        │ BLE
        ▼
┌───────────────────────┐
│   Data Acquisition    │
└───────────┬───────────┘
            │
            ▼
      Experiment Data
       CSV + Metadata
            │
            ▼
┌───────────────────────┐
│   Thermal Simulator   │
└───────────┬───────────┘
            │
            ▼
       Calibration
            │
            ▼
        Prediction
            │
            ▼
    Future Controller
            │
            ▼
      Electric Heater
```

This separation is intentional.

The BLE acquisition system does not need to understand thermal physics, and the simulator does not depend on Bluetooth hardware.

This allows each subsystem to evolve independently.

---

# Chef iQ CQ60 BLE Acquisition

The system currently recognizes three physical Chef iQ CQ60 probes.

On macOS, CoreBluetooth exposes device identifiers rather than conventional BLE MAC addresses. These identifiers are mapped to configurable friendly names.

Example:

```python
ProbeDefinition(
    match_fragment="902B6F7B-D0F4-EC70-1C01-8D7DE6A68397",
    friendly_name="Brisket Flat",
)
```

Friendly names describe the **role of a probe during an experiment** rather than forcing the software to permanently identify devices as Probe 1, Probe 2, and Probe 3.

Possible roles include:

- `Brisket Flat`
- `Brisket Point`
- `Upper Cooking Grate`
- `Lower Cooking Grate`
- `Weber Chamber`
- `Weber Exterior`
- `Ambient Air`

This allows the same physical probe to serve different experimental roles without modifying the BLE acquisition logic.

---

# CQ60 Measurements

The acquisition model supports several measurements from each CQ60 probe:

- Food temperature
- Ambient temperature
- Tip sensor 1
- Tip sensor 2
- Tip sensor 3
- Tip sensor 4
- Battery level
- BLE RSSI
- Raw BLE manufacturer packet

One research objective is determining exactly how Chef iQ derives its reported food temperature from the multiple temperature sensors located along the probe.

For this reason, the individual sensor measurements and raw BLE data should be preserved whenever possible.

---

# Data Recording

Each execution of the acquisition program represents a new experimental session.

A new timestamped directory is created automatically.

Existing experimental data is never intentionally overwritten.

Example:

```text
data/
└── sessions/
    ├── 20260824_190512/
    │   ├── session.json
    │   ├── brisket_flat.csv
    │   └── chamber.csv
    │
    └── 20260825_101405/
        ├── session.json
        ├── chamber.csv
        └── weber_exterior.csv
```

Each probe receives its own CSV file.

All probe files belonging to the same experiment share the same session directory and session start time.

This architecture simplifies:

- Time synchronization
- Experimental analysis
- Simulator ingestion
- Experiment replay
- Data visualization
- Model validation

---

# Experiment Metadata

Every controlled experiment should contain machine-readable metadata.

Example:

```json
{
  "name": "Baseline Weber electric heater test - 1100 W",
  "heater_power_w": 1100,
  "internal_file": "internal.csv",
  "external_file": "external.csv",
  "ambient_temperature_f": null,
  "internal_temperature_column": "Food Temperature",
  "external_temperature_column": "Food Temperature",
  "notes": "1100 W electric heating element operated continuously at 100 percent power."
}
```

This ensures that experimental datasets remain understandable long after they are recorded.

Future metadata may include:

- Heater wattage
- Heater duty cycle
- Outside temperature
- Wind conditions
- Weber configuration
- Vent position
- Insulation configuration
- Food type
- Food mass
- Food starting temperature
- Probe placement
- Controller configuration
- Experiment notes

---

# Baseline Thermal Experiment

The first controlled thermal experiment established a baseline for the unmodified electric-heater configuration.

## Experimental Configuration

| Parameter | Value |
|---|---|
| Heater | Electric resistance heating element |
| Rated power | 1100 W |
| Heater command | 100% |
| Duty cycle | Continuous |
| Smoker | Weber |
| Internal measurement | Chef iQ CQ60 |
| External measurement | Chef iQ CQ60 |

The 1100 W heater remained continuously energized during the heating experiment.

---

## Experimental Observation

The Weber did **not** reach the desired 225°F internal operating temperature under the tested conditions.

The internal probe temperature approached approximately:

```text
180°F
```

The CQ60 local ambient measurement inside the Weber exceeded approximately:

```text
220°F
```

The external probe remained approximately:

```text
105–110°F
```

These measurements demonstrate substantial thermal gradients across the system.

Rather than treating the inability to reach 225°F as a failed test, the experiment is being used as the project's first thermal calibration dataset.

It is designated:

> **Calibration Experiment #1 — 1100 W Baseline**

---

# Thermal Model

V3.1 currently uses a **two-node lumped-parameter thermal model**.

```text
                         Chamber heat loss
                                │
                                ▼
1100 W Heater ───────► [ CHAMBER ]
                           │
                           │ thermal conduction
                           ▼
                      [ WEBER BODY ]
                           │
                           │ convection
                           │ radiation
                           ▼
                        AMBIENT
```

A second heat-loss path represents direct chamber-to-ambient losses such as:

- Air leakage
- Vent losses
- Openings
- Imperfect seals
- Other unmodeled heat-transfer mechanisms

---

# Chamber Energy Balance

The chamber is modeled approximately by:

```text
C_chamber × dT_chamber/dt
    =
Q_heater
    - Q_chamber_to_body
    - Q_chamber_to_ambient
```

where:

- `C_chamber` is the effective chamber heat capacity
- `Q_heater` is useful heater power
- `Q_chamber_to_body` is heat transferred into the Weber structure
- `Q_chamber_to_ambient` represents direct heat loss

---

# Weber Body Energy Balance

The Weber structure is modeled approximately by:

```text
C_body × dT_body/dt
    =
Q_chamber_to_body
    - Q_body_to_ambient
```

where:

- `C_body` is the effective thermal capacity of the Weber structure
- `Q_body_to_ambient` represents convection and radiation from the Weber to the surrounding environment

---

# Model Parameters

The calibration system currently estimates:

| Parameter | Meaning |
|---|---|
| `C_chamber` | Effective chamber heat capacity |
| `C_body` | Effective Weber body heat capacity |
| `UA_chamber_body` | Chamber-to-body thermal conductance |
| `UA_chamber_ambient` | Direct chamber-to-ambient conductance |
| `UA_body_ambient` | Weber-body-to-ambient conductance |
| `heater_efficiency` | Fraction of electrical heater power entering the modeled thermal system |

These parameters are inferred from experimental measurements rather than chosen solely from theoretical assumptions.

The objective is not merely to create a simulation that looks plausible.

The objective is to create a model capable of predicting the behavior of the **actual physical Weber smoker**.

---

# Why the Current Model Has Two Thermal Nodes

A more complicated model is not automatically a better model.

The baseline experiment directly observes approximately two useful thermal states:

1. Internal Weber thermal response
2. External Weber thermal response

Electrical heater power is a known input.

Adding additional unmeasured thermal states too early could create an under-constrained model.

An optimizer might then produce an excellent-looking curve while estimating physically meaningless parameters.

Additional thermal nodes will therefore be introduced only when experimental evidence demonstrates that they are necessary.

Possible future thermal nodes include:

- Heating element
- Internal air
- Cooking grate
- Weber lid
- Lower kettle
- Food surface
- Food core
- External environment

---

# Calibration

The calibration system compares simulated temperatures against measured experimental temperatures.

The optimizer searches for thermal parameters that minimize prediction error.

The current error metric is combined **root-mean-square error (RMSE)** between:

- Measured internal temperature
- Simulated internal temperature
- Measured external temperature
- Simulated Weber-body temperature

Conceptually:

```text
Measured Data
      │
      ▼
┌────────────────┐
│ Thermal Model  │
└───────┬────────┘
        │
        ▼
Simulated Temperatures
        │
        ▼
Compare with Measurements
        │
        ▼
Calculate RMSE
        │
        ▼
Adjust Parameters
        │
        └──────────────► Repeat
```

The optimization mechanism is deliberately separated from the physics model.

This allows the optimizer to be replaced later without rewriting the thermal equations.

---

# Prediction

After calibration, the simulator can evaluate heater powers that have not yet been physically tested.

The current prediction sweep includes:

| Heater Power |
|---:|
| 800 W |
| 900 W |
| 1000 W |
| 1100 W |
| 1200 W |
| 1300 W |
| 1400 W |
| 1500 W |
| 1600 W |

For each heater power, the simulator predicts:

- Temperature after a specified heating period
- Approximate steady-state chamber temperature

The simulator also estimates the heater power required to reach a specified steady-state target.

The current design target is:

> **225°F**

---

# Primary Engineering Question

The central hardware question at this stage is:

> **What combination of heater power and thermal-loss reduction is required for the Weber to reliably maintain 225°F under realistic environmental conditions?**

The calibrated simulator should eventually allow us to evaluate configurations such as:

```text
1100 W + existing Weber
1500 W + existing Weber

1100 W + insulation
1500 W + insulation

Cold ambient conditions
Warm ambient conditions

Low wind
High wind
```

This allows hardware changes to be evaluated computationally before modifying the physical smoker.

---

# Calibration Is Not Validation

Calibration and validation are deliberately treated as separate engineering activities.

A model that reproduces the experiment used to fit it is **not necessarily predictive**.

The intended workflow is:

```text
Experiment A
      │
      ▼
Calibrate Model
      │
      ▼
Estimated Physical Parameters
      │
      ▼
Predict Experiment B
      │
      ▼
Run Experiment B
      │
      ▼
Compare Prediction
Against Measurement
```

Only after successful validation against independent experiments should the model be trusted for hardware design decisions.

---

# Recommended Next Experiments

Several experiments would provide especially valuable validation data.

## Different Heater Power

Run the Weber at a different known heater power.

For example:

```text
1500 W at 100% duty cycle
```

This is one of the strongest tests of whether the calibrated heat-loss parameters are genuinely predictive.

---

## Heater Cool-Down Experiment

Heat the Weber to equilibrium and then switch the heater completely off.

Record the complete cooling curve.

This experiment is especially useful for identifying:

- Thermal capacitance
- Heat-loss coefficients
- Slow structural thermal behavior

Because heater input becomes exactly:

```text
0 W
```

the parameter-identification problem becomes considerably cleaner.

---

## Insulation Experiment

Repeat the same heater test after adding a known insulation configuration.

The difference between the baseline and insulated runs can quantify the improvement in thermal resistance.

---

# Automated Tests

V3.1 includes automated unit tests.

Current tests cover:

- Fahrenheit-to-Celsius conversion
- Celsius-to-Fahrenheit conversion
- Thermal heating behavior
- Zero-power equilibrium behavior
- Increased heater power producing increased equilibrium temperature
- Numerical interpolation
- Required heater-power calculations

Run the test suite from the project root:

```bash
python -m unittest discover -s simulator/tests -v
```

Expected completion:

```text
----------------------------------------------------------------------
Ran 8 tests

OK
```

Every significant software bug discovered during development should ideally result in a new regression test.

As the project matures, physical experiments can also become simulator regression tests.

---

# Running the Simulator

From the project root:

```bash
python -m simulator.main
```

V3.1 intentionally prints startup diagnostics immediately.

Example:

```text
Starting Weber simulator V3.1...

Experiment directory: experiments/baseline_1100w
Loading experiment.json...
Loading experiment.json... OK
Loading internal.csv... OK
Loading external.csv... OK

WEBER SMOKER THERMAL SIMULATOR V3.1
========================================================================
Experiment: Baseline Weber electric heater test - 1100 W
Heater power: 1100 W
Internal samples: ...
External samples: ...

Running calibration...
```

This behavior is intentional.

Missing files, malformed CSV files, invalid metadata, or other startup problems should produce explicit errors rather than making the program appear to do nothing.

---

# Experiment Directory

The baseline experiment should be organized as:

```text
simulator/
└── experiments/
    └── baseline_1100w/
        ├── experiment.json
        ├── internal.csv
        └── external.csv
```

Example `experiment.json`:

```json
{
  "name": "Baseline Weber electric heater test - 1100 W",
  "heater_power_w": 1100,
  "internal_file": "internal.csv",
  "external_file": "external.csv",
  "ambient_temperature_f": null,
  "internal_temperature_column": "Food Temperature",
  "external_temperature_column": "Food Temperature",
  "notes": "1100 W electric heating element operated continuously at 100 percent power."
}
```

---

# Python Environment

A virtual environment is recommended.

On macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

The BLE acquisition subsystem currently uses packages including:

```text
bleak
chefiq-ble
home-assistant-bluetooth
```

The simulator currently uses:

```text
matplotlib
```

Additional scientific Python dependencies may be introduced as the calibration system matures.

---

# macOS BLE Notes

Initial development and testing are being performed on macOS.

CoreBluetooth behaves somewhat differently from BLE implementations on other platforms.

In particular, macOS exposes CoreBluetooth device UUIDs rather than conventional BLE MAC addresses.

Values originating from PyObjC/CoreBluetooth should also be explicitly converted into native Python strings before being passed to libraries expecting `str`.

For example:

```python
address = str(device.address)

bluetooth_name = str(
    advertisement.local_name
    or device.name
    or "CQ60"
)
```

This avoids errors such as:

```text
TypeError: Expected str, got objc.pyobjc_unicode
```

---

# Repository Hygiene

IDE configuration, Python caches, virtual environments, and automatically generated experimental data should generally not be committed.

Recommended `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]

# Virtual environments
.venv/
venv/

# PyCharm
.idea/

# macOS
.DS_Store

# Automatically recorded cook sessions
data/sessions/
```

Controlled experiments intentionally retained as calibration or validation datasets may eventually be versioned separately from routine data collection.

---

# Development Roadmap

## Phase 1 — BLE Acquisition

**Status: Substantially complete**

- [x] Discover CQ60 probes
- [x] Decode manufacturer data
- [x] Identify individual physical probes
- [x] Capture temperature information
- [x] Handle macOS/CoreBluetooth behavior

---

## Phase 2 — Experimental Recorder

**Status: Functional and being refined**

- [x] Friendly probe names
- [x] Per-probe CSV architecture
- [x] Session-based recording
- [x] Experiment metadata architecture
- [x] Preserve raw measurements
- [x] Prevent accidental session overwrite

---

## Phase 3 — Thermal Simulator

**Status: Active development**

- [x] Load real experimental data
- [x] Implement two-node thermal physics
- [x] Implement parameter calibration
- [x] Implement heater-power prediction
- [x] Generate calibration plots
- [x] Introduce automated tests

---

## Phase 4 — Model Validation

**Status: Next major experimental phase**

Run additional controlled experiments under different operating conditions and compare simulator predictions against measurements not used during calibration.

High-value experiments include:

- Different heater wattage
- Added insulation
- Different ambient temperature
- Heater shutoff and cool-down
- Repeatability testing

---

## Phase 5 — Cooking Model

Introduce food as an additional thermal system.

Potential states include:

```text
Food surface temperature
Food core temperature
Evaporative cooling
Food thermal mass
Moisture loss
```

The CQ60's multiple internal sensors may provide particularly valuable information for this stage.

---

## Phase 6 — Closed-Loop Controller

After validating the physical model, introduce automatic heater control.

A possible controller-development sequence is:

```text
Hysteresis Control
        │
        ▼
PID Control
        │
        ▼
Feed-Forward + PID
        │
        ▼
Model-Based Control
        │
        ▼
Model Predictive Control
        │
        ▼
Learning-Assisted Control
```

The simulator should be used to evaluate controller behavior before a new control algorithm operates the physical heating system.

---

## Phase 7 — Hardware Optimization

Use the experimentally validated simulator to evaluate:

- Heater wattage
- Insulation
- Vent configuration
- Heat distribution
- Recovery after opening the lid
- Environmental sensitivity
- Energy consumption
- Warm-up time
- Steady-state efficiency

---

# Experimental Method

The project follows a simple engineering principle:

> **Measure first. Model second. Predict third. Validate fourth.**

Every controlled experiment should improve our understanding of the physical system.

Every important model parameter should ultimately be supported by experimental evidence.

Every important simulator prediction should eventually be tested against the physical Weber.

---

# Immediate Next Steps

1. Verify the complete V3.1 unit-test suite.
2. Successfully import Calibration Experiment #1.
3. Calibrate the two-node thermal model.
4. Examine the fitted parameters for physical plausibility.
5. Compare modeled and measured temperature curves.
6. Quantify calibration residuals.
7. Estimate the heater power required to maintain 225°F.
8. Design Calibration/Validation Experiment #2.
9. Predict Experiment #2 **before running it**.
10. Run the physical experiment.
11. Compare prediction against measurement.
12. Add model complexity only if the residuals demonstrate that additional physics are necessary.

---

# Long-Term Goal

The long-term objective is an experimentally validated Weber smoker platform capable of:

```text
Measurement
     │
     ▼
Modeling
     │
     ▼
Prediction
     │
     ▼
Control
     │
     ▼
Validation
     │
     └──────────► Improved Model
```

The objective is not simply to switch an electric heating element based on a temperature threshold.

The goal is to develop a system that understands enough of the Weber's thermal behavior to **measure, predict, and intelligently control the cooking environment**.# Webber-Smoker-conversion-with-LNN-and-simulator
# Webber-Smoker-conversion-with-LNN-and-simulator
