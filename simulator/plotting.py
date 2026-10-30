import matplotlib.pyplot as plt

from simulator.models import (
    ExperimentData,
    SimulationResult,
)
from simulator.prediction import (
    celsius_to_fahrenheit,
)


def plot_comparison(
    experiment: ExperimentData,
    simulation: SimulationResult,
) -> None:

    measured_internal_minutes = [
        seconds / 60.0
        for seconds
        in experiment.internal.time_seconds
    ]

    measured_external_minutes = [
        seconds / 60.0
        for seconds
        in experiment.external.time_seconds
    ]

    simulated_minutes = [
        seconds / 60.0
        for seconds
        in simulation.time_seconds
    ]

    measured_internal_f = [
        celsius_to_fahrenheit(value)
        for value
        in experiment.internal.temperature_c
    ]

    measured_external_f = [
        celsius_to_fahrenheit(value)
        for value
        in experiment.external.temperature_c
    ]

    simulated_internal_f = [
        celsius_to_fahrenheit(value)
        for value
        in simulation.chamber_temperature_c
    ]

    simulated_external_f = [
        celsius_to_fahrenheit(value)
        for value
        in simulation.body_temperature_c
    ]

    plt.figure()

    plt.plot(
        measured_internal_minutes,
        measured_internal_f,
        label="Measured internal",
    )

    plt.plot(
        measured_external_minutes,
        measured_external_f,
        label="Measured external",
    )

    plt.plot(
        simulated_minutes,
        simulated_internal_f,
        label="Model internal",
    )

    plt.plot(
        simulated_minutes,
        simulated_external_f,
        label="Model external",
    )

    plt.xlabel(
        "Elapsed time (minutes)"
    )

    plt.ylabel(
        "Temperature (°F)"
    )

    plt.title(
        experiment.metadata.name
    )

    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.show()
