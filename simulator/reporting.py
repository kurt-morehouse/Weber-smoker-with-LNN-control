from simulator.models import (
    CalibrationResult,
    ExperimentData,
    PredictionReport,
)
from simulator.prediction import (
    celsius_to_fahrenheit,
)


REPORT_WIDTH: int = 72


def print_experiment_summary(
    experiment: ExperimentData,
) -> None:

    print()
    print(
        "WEBER SMOKER THERMAL SIMULATOR V3.1"
    )
    print("=" * REPORT_WIDTH)

    print(
        f"Experiment: "
        f"{experiment.metadata.name}"
    )

    print(
        f"Heater power: "
        f"{experiment.metadata.heater_power_w:.0f} W"
    )

    print(
        f"Internal samples: "
        f"{len(experiment.internal.time_seconds):,}"
    )

    print(
        f"External samples: "
        f"{len(experiment.external.time_seconds):,}"
    )

    print()


def print_calibration_result(
    result: CalibrationResult,
) -> None:

    parameters = result.parameters

    print()
    print("CALIBRATION RESULT")
    print("=" * REPORT_WIDTH)

    print(
        f"Combined RMSE: "
        f"{result.rmse_c:.3f} °C"
    )

    print(
        f"Heater efficiency: "
        f"{parameters.heater_efficiency:.3f}"
    )

    print(
        f"Chamber heat capacity: "
        f"{parameters.chamber_heat_capacity_j_per_k:,.0f} J/K"
    )

    print(
        f"Body heat capacity: "
        f"{parameters.body_heat_capacity_j_per_k:,.0f} J/K"
    )

    print(
        f"Chamber/body conductance: "
        f"{parameters.chamber_body_conductance_w_per_k:.3f} W/K"
    )

    print(
        f"Chamber/ambient conductance: "
        f"{parameters.chamber_ambient_conductance_w_per_k:.3f} W/K"
    )

    print(
        f"Body/ambient conductance: "
        f"{parameters.body_ambient_conductance_w_per_k:.3f} W/K"
    )


def print_prediction_report(
    report: PredictionReport,
    target_temperature_f: float,
) -> None:

    print()
    print("HEATER POWER PREDICTIONS")
    print("=" * REPORT_WIDTH)

    print(
        "Power      4-hour temp      "
        "Steady-state temp"
    )

    print("-" * REPORT_WIDTH)

    for point in report.points:

        final_f = celsius_to_fahrenheit(
            point.final_temperature_c
        )

        steady_f = celsius_to_fahrenheit(
            point.steady_state_temperature_c
        )

        print(
            f"{point.heater_power_w:5.0f} W"
            f"      "
            f"{final_f:7.1f} °F"
            f"          "
            f"{steady_f:7.1f} °F"
        )

    print()

    required_power = (
        report
        .estimated_power_for_target_w
    )

    if required_power is None:
        print(
            "Unable to estimate required "
            "heater power."
        )

    else:
        print(
            f"Estimated heater power required "
            f"for {target_temperature_f:.0f} °F "
            f"steady state:"
        )

        print(
            f"    {required_power:.0f} W"
        )
