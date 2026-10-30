from __future__ import annotations

import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


LIVE_METRICS = (
    ("food_temperature_c", "food_temperature_f", "Food", "°F", "temperature"),
    ("ambient_temperature_c", "ambient_temperature_f", "Ambient", "°F", "temperature"),
    ("tip_1_temperature_c", "tip_1_temperature_f", "Tip 1", "°F", "temperature"),
    ("tip_2_temperature_c", "tip_2_temperature_f", "Tip 2", "°F", "temperature"),
    ("tip_3_temperature_c", "tip_3_temperature_f", "Tip 3", "°F", "temperature"),
    ("tip_4_temperature_c", "tip_4_temperature_f", "Tip 4", "°F", "temperature"),
    ("battery_percent", "battery_percent", "Battery", "%", "battery"),
    ("rssi", "rssi_dbm", "Signal", "dBm", "signal"),
)

REPLAY_METRICS = {
    "food_temperature_f": ("Food", "°F", "temperature"),
    "ambient_temperature_f": ("Ambient", "°F", "temperature"),
    "tip_1_temperature_f": ("Tip 1", "°F", "temperature"),
    "tip_2_temperature_f": ("Tip 2", "°F", "temperature"),
    "tip_3_temperature_f": ("Tip 3", "°F", "temperature"),
    "tip_4_temperature_f": ("Tip 4", "°F", "temperature"),
    "battery_percent": ("Battery", "%", "battery"),
    "rssi_dbm": ("Signal", "dBm", "signal"),
}

MAX_LIVE_POINTS = 1800


class SelectablePlot(QWidget):
    """Multi-select time series plot with separate axes for each unit."""

    cursor_changed = Signal(float)

    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self._title = title
        self._series: dict[str, dict] = {}
        self._selected: set[str] = set()
        self._user_changed_selection = False
        self._live_started_at: float | None = None
        self._replay_active = False
        self._replay_cursor = 0.0
        self._replay_start = 0.0
        self._replay_duration = 0.0

        self._channel_content = QWidget()
        self._channel_layout = QVBoxLayout(self._channel_content)
        self._channel_layout.setContentsMargins(4, 4, 4, 4)
        self._channel_checks: dict[str, QCheckBox] = {}
        self._channel_scroll = QScrollArea()
        self._channel_scroll.setWidgetResizable(True)
        self._channel_scroll.setMinimumWidth(230)
        self._channel_scroll.setWidget(self._channel_content)
        self._hint = QLabel("Each checkbox controls one plotted line.")
        self._figure = Figure(figsize=(8, 4))
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._canvas.mpl_connect("button_press_event", self._on_plot_click)

        self._side_layout = QVBoxLayout()
        self._side_layout.addWidget(QLabel("Channels"))
        self._side_layout.addWidget(self._channel_scroll, 1)
        self._side_layout.addWidget(self._hint)
        layout = QHBoxLayout(self)
        layout.addLayout(self._side_layout)
        layout.addWidget(self._canvas, 1)
        self._render()

    def add_side_widget(self, widget: QWidget, minimum_width: int | None = None) -> None:
        if minimum_width is not None:
            self._channel_scroll.setMinimumWidth(minimum_width)
        self._side_layout.addWidget(widget)

    @property
    def replay_duration(self) -> float:
        return self._replay_duration

    @property
    def replay_cursor(self) -> float:
        return self._replay_cursor

    @property
    def replay_start(self) -> float:
        return self._replay_start

    def reset_live(self) -> None:
        self._series.clear()
        self._selected.clear()
        self._user_changed_selection = False
        self._live_started_at = None
        self._replay_active = False
        self._replay_cursor = 0.0
        self._replay_start = 0.0
        self._replay_duration = 0.0
        self._sync_channels()
        self._render()

    def add_live_readings(self, readings) -> None:
        now = time.monotonic()
        if self._live_started_at is None:
            self._live_started_at = now
        elapsed = now - self._live_started_at
        new_channels = False

        for reading in readings:
            for source_field, key_field, label, unit, group in LIVE_METRICS:
                key = f"{reading.address}|{key_field}"
                if key not in self._series:
                    self._series[key] = {
                        "label": f"{reading.friendly_name} · {label}",
                        "unit": unit,
                        "group": group,
                        "x": [],
                        "y": [],
                    }
                    new_channels = True
                value = getattr(reading, source_field)
                if source_field.endswith("_temperature_c") and value is not None:
                    value = value * 9.0 / 5.0 + 32.0
                series = self._series[key]
                series["x"].append(elapsed)
                series["y"].append(value)
                excess = len(series["x"]) - MAX_LIVE_POINTS
                if excess > 0:
                    del series["x"][:excess]
                    del series["y"][:excess]

        if new_channels:
            self._sync_channels()
        self._render()

    def set_replay_series(self, entries) -> None:
        self._replay_active = True
        self._series = {
            entry["key"]: {
                "label": entry["label"],
                "unit": entry["unit"],
                "group": entry["group"],
                "x": list(entry["x"]),
                "y": list(entry["y"]),
            }
            for entry in entries
        }
        self._selected = {
            key for key, item in self._series.items()
            if item["group"] == "temperature"
        }
        self._user_changed_selection = False
        all_times = [
            x for item in self._series.values() for x in item["x"]
        ]
        self._replay_start = min(all_times, default=0.0)
        self._replay_cursor = self._replay_start
        self._replay_duration = max(all_times, default=0.0)
        self._sync_channels()
        self._render()
        self.cursor_changed.emit(self._replay_cursor)

    def set_replay_cursor(self, elapsed_seconds: float) -> None:
        if not self._replay_active:
            return
        self._replay_cursor = min(
            max(self._replay_start, float(elapsed_seconds)),
            self._replay_duration,
        )
        self._render()
        self.cursor_changed.emit(self._replay_cursor)

    def replay_readouts(self) -> tuple[tuple[str, float, float, str], ...]:
        if not self._replay_active:
            return ()
        rows = []
        for key, series in self._series.items():
            if key not in self._selected:
                continue
            for x, value in reversed(tuple(zip(series["x"], series["y"]))):
                if x <= self._replay_cursor and value is not None:
                    rows.append((series["label"], x, value, series["unit"]))
                    break
        return tuple(rows)

    def _sync_channels(self) -> None:
        while self._channel_layout.count():
            item = self._channel_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._channel_checks.clear()

        for key, series in self._series.items():
            checkbox = QCheckBox(f"{series['label']} ({series['unit']})")
            if not self._user_changed_selection and series["group"] == "temperature":
                self._selected.add(key)
            checkbox.setChecked(key in self._selected)
            checkbox.toggled.connect(
                lambda checked, channel_key=key: self._channel_toggled(
                    channel_key, checked
                )
            )
            self._channel_checks[key] = checkbox
            self._channel_layout.addWidget(checkbox)
        self._channel_layout.addStretch(1)

        if not self._series:
            self._hint.setText("No probe values available yet.")
        else:
            self._hint.setText("Choose channels; units use separate axes.")

    def _channel_toggled(self, key: str, checked: bool) -> None:
        self._user_changed_selection = True
        if checked:
            self._selected.add(key)
        else:
            self._selected.discard(key)
        self._render()
        if self._replay_active:
            self.cursor_changed.emit(self._replay_cursor)

    def _on_plot_click(self, event) -> None:
        if (
            self._replay_active
            and event.inaxes is not None
            and event.xdata is not None
        ):
            self.set_replay_cursor(event.xdata)

    def _render(self) -> None:
        self._figure.clear()
        temperature_axis = self._figure.add_subplot(111)
        selected_series = [
            (key, value) for key, value in self._series.items()
            if key in self._selected
        ]
        groups = {value["group"] for _, value in selected_series}
        axes = {"temperature": temperature_axis}
        if "battery" in groups:
            axes["battery"] = temperature_axis.twinx()
            axes["battery"].set_ylabel("Battery (%)")
        if "signal" in groups:
            signal_axis = temperature_axis.twinx()
            signal_axis.spines["right"].set_position(("outward", 55))
            axes["signal"] = signal_axis
            signal_axis.set_ylabel("Signal (dBm)")
        if "temperature" not in groups:
            temperature_axis.set_ylabel("")
            temperature_axis.set_yticks([])
        else:
            temperature_axis.set_ylabel("Temperature (°F)")

        plotted = 0
        for _, series in selected_series:
            values = [
                (x, y) for x, y in zip(series["x"], series["y"])
                if y is not None
            ]
            if not values:
                continue
            x_values, y_values = zip(*values)
            axis = axes[series["group"]]
            line, = axis.plot(
                x_values,
                y_values,
                label=series["label"] + " (" + series["unit"] + ")",
                linewidth=1.5,
            )
            if self._replay_active:
                cursor_points = [
                    (x, y) for x, y in values if x <= self._replay_cursor
                ]
                if cursor_points:
                    sample_time, sample_value = cursor_points[-1]
                    axis.plot(
                        [sample_time],
                        [sample_value],
                        marker="o",
                        color=line.get_color(),
                        linestyle="none",
                        label="_nolegend_",
                    )
            plotted += 1
        if self._replay_active:
            temperature_axis.axvline(
                self._replay_cursor,
                color="black",
                linestyle="--",
                linewidth=1,
                alpha=0.75,
            )
            if self._replay_duration > 0:
                temperature_axis.set_xlim(0.0, self._replay_duration)

        temperature_axis.set_title(self._title)
        temperature_axis.set_xlabel("Elapsed time (seconds)")
        temperature_axis.grid(True, alpha=0.25)
        handles, labels = [], []
        for axis in axes.values():
            axis_handles, axis_labels = axis.get_legend_handles_labels()
            handles.extend(axis_handles)
            labels.extend(axis_labels)
        if handles:
            temperature_axis.legend(handles, labels, loc="upper left", fontsize=8)
        if "signal" in axes:
            self._figure.subplots_adjust(right=0.84)
        else:
            self._figure.tight_layout()
        if not plotted and selected_series:
            self._hint.setText("Selected channels have no values at this cursor yet.")
        self._canvas.draw_idle()
