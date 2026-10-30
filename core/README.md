# Weber smoker calibration drop

This drop creates the first experiment -> calibration -> simulator pipeline.

## Add / replace

core/thermal_analysis.py
core/calibration.py
core/calibration_store.py
core/calibration_workflow.py
core/calibrated_simulator.py
tools/calibration_demo.py

## Data boundaries

Raw measurement CSV
    -> RecordedExperiment
    -> thermal fit
    -> ThermalCalibration
    -> CalibratedChamberModel
    -> predictions

Raw measurements are never overwritten.

A saved calibration is written as:

    thermal_calibration.json

inside the experiment/session directory.

## Fitted physical parameters

Heat-loss coefficient K:

    P = K * (T_inf - T_out)

Effective thermal capacitance C:

    tau = C / K

The calibrated simulator then uses:

    C dT/dt = P - K(T - T_out)

This is intentionally a one-node model.  It gives us a measurable baseline
before we add chamber zones, water/food masses, lid losses, controller cycling,
or an LNN layer.
