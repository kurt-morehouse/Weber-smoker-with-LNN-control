from PySide6.QtCore import QSize

from PySide6.QtWidgets import (
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)

from matplotlib.figure import Figure

from core.experiment_reader import RecordedExperiment


class ExperimentPlot(QWidget):

    # Display-only smoothing. Raw RecordedExperiment data is never modified.
    DISPLAY_FILTER_TIME_CONSTANT_SECONDS = 15.0


    def __init__(
        self,
        parent=None,
    ) -> None:

        super().__init__(parent)

        self._figure = Figure()

        self._canvas = FigureCanvasQTAgg(
            self._figure
        )

        self._canvas.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        self._toolbar = NavigationToolbar2QT(
            self._canvas,
            self,
        )

        self._toolbar.setIconSize(
            QSize(16, 16)
        )

        self._toolbar.setMaximumHeight(
            26
        )

        self._toolbar.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout = QVBoxLayout()

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(2)

        layout.addWidget(
            self._toolbar
        )

        layout.addWidget(
            self._canvas,
            stretch=1,
        )

        self.setLayout(layout)

        self.clear()

    def clear(self) -> None:

        self._figure.clear()

        axis = self._figure.add_subplot(
            111
        )

        axis.set_title(
            "Select an Experiment"
        )

        axis.set_xlabel(
            "Elapsed Time (seconds)"
        )

        axis.set_ylabel(
            "Temperature (°F)"
        )

        axis.grid(
            True,
            alpha=0.25,
        )

        self._figure.tight_layout()

        self._canvas.draw_idle()

    def display(
        self,
        recorded: RecordedExperiment,
    ) -> None:

        self._figure.clear()

        axis = self._figure.add_subplot(
            111
        )

        manifest = (
            recorded
            .experiment
            .manifest
        )

        plotted = 0

        for probe in recorded.probes:

            for series in probe.series:

                # Display Fahrenheit channels only.
                if not (
                    series.name
                    .lower()
                    .endswith("_f")
                ):
                    continue

                x_values = []
                y_values = []

                for (
                    time_value,
                    temperature,
                ) in zip(
                    probe.time_seconds,
                    series.values,
                ):

                    if temperature is None:
                        continue

                    x_values.append(
                        time_value
                    )

                    y_values.append(
                        temperature
                    )

                if not y_values:
                    continue

                channel_name = (
                    series.name
                    .removesuffix("_f")
                    .replace(
                        "_temperature",
                        "",
                    )
                    .replace(
                        "_",
                        " ",
                    )
                    .title()
                )

                label = (
                    f"{probe.friendly_name}"
                    f" — {channel_name}"
                )

                display_values = self._low_pass_filter(
                    x_values,
                    y_values,
                    self.DISPLAY_FILTER_TIME_CONSTANT_SECONDS,
                )

                axis.plot(
                    x_values,
                    display_values,
                    label=label,
                )

                plotted += 1

        axis.set_title(
            manifest.name
        )

        axis.set_xlabel(
            "Elapsed Time (seconds)"
        )

        axis.set_ylabel(
            "Temperature (°F)"
        )

        axis.grid(
            True,
            alpha=0.25,
        )

        if plotted:

            axis.legend(
                loc="upper left",
                bbox_to_anchor=(
                    1.01,
                    1.0,
                ),
                fontsize=7,
                borderaxespad=0.0,
            )

            self._figure.subplots_adjust(
                right=0.72,
                left=0.08,
                bottom=0.12,
                top=0.90,
            )

        else:

            axis.text(
                0.5,
                0.5,
                "No Fahrenheit temperature data found",
                ha="center",
                va="center",
                transform=axis.transAxes,
            )

            self._figure.tight_layout()

        self._canvas.draw_idle()

    @staticmethod
    def _low_pass_filter(
        time_seconds: list[float],
        values: list[float],
        time_constant_seconds: float,
    ) -> list[float]:
        """
        First-order low-pass filter for display only.

        The coefficient is calculated from the actual elapsed time
        between samples, so the behavior remains consistent if the
        acquisition cadence changes.
        """
        if not values:
            return []

        if len(values) == 1 or time_constant_seconds <= 0.0:
            return list(values)

        filtered = [values[0]]

        for index in range(1, len(values)):
            dt = time_seconds[index] - time_seconds[index - 1]

            if dt <= 0.0:
                filtered.append(filtered[-1])
                continue

            alpha = dt / (time_constant_seconds + dt)

            previous = filtered[-1]
            current = values[index]

            filtered.append(
                previous + alpha * (current - previous)
            )

        return filtered

