WEBER DATA-INTEGRITY + ENGINEERING NOTEBOOK DROP

ADD:
  core/acquisition_integrity.py
  core/raw_packet_log.py
  core/engineering_notebook.py
  tools/inspect_acquisition.py

WHY THIS DROP IS CONTAINED
--------------------------
The immediate problem is a disagreement between the CHEF iQ phone history and
our recorded/decoded channels. We should instrument the data path without
risking the currently stable acquisition thread.

1. acquisition_integrity.py
   Detects long flat/unchanged runs per numeric channel and reports exactly
   where they begin/end in elapsed time. This distinguishes "sampling stopped"
   from "samples continued but decoded value froze."

2. raw_packet_log.py
   Provides a raw BLE advertisement logger: UTC timestamp, device identifier,
   manufacturer ID, RSSI, exact payload bytes and payload length.
   IMPORTANT: it is intentionally NOT wired into ble_scanner.py in this drop.
   I need the current scanner source before changing the stable acquisition
   callback. That next wiring change should be tiny and auditable.

3. engineering_notebook.py
   Structured editable notebook sidecar with:
     hardware configuration
     modifications
     test conditions
     acquisition summary
     analysis highlights
     observations
     conclusions
     next actions
     photo paths
   It does not touch raw CSV.

4. tools/inspect_acquisition.py
   Command-line integrity report for any recorder CSV.

NEXT SAFE WIRING STEP
---------------------
Provide the current:
  acquisition/ble_scanner.py
  acquisition/probe_service.py
  gui/sessions_tab.py

Then the next drop can:
- capture raw packets during acquisition,
- show packet-vs-decoded values in the GUI,
- make the structured notebook editable in Sessions,
- auto-fill acquisition/calibration highlights,
without guessing at the live acquisition callback.
