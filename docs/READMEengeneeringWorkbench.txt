WEBER ENGINEERING WORKBENCH DROP

ADD:
  core/digital_twin.py
  core/sensitivity_analysis.py
  core/engineering_journal.py

REPLACE:
  gui/simulator_tab.py

This drop combines the two directions we discussed:
1. Digital-twin manager + engineering dashboard.
2. Sensitivity analysis + engineering journal.

It builds on the existing saved thermal_calibration.json workflow.
It does not modify acquisition, recorder, raw CSV files, or Sessions.

Simulator tabs:
- Engineering Dashboard: what-if prediction, equilibrium, target power, margin,
  time-to-target, and calibration health.
- Sensitivity: ±50% heater-power sweep around the selected heater power.
- Engineering Journal: generates engineering_report.md inside the selected
  session using saved experiment notes + calibration.

The existing Sessions Compare / Validate drop remains complementary: use it
for A/B experiment comparison after today's improved-seal run.
