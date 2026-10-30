from simulator.config import (
    CELSIUS_TO_FAHRENHEIT_SCALE,
    FAHRENHEIT_OFFSET,
    FAHRENHEIT_TO_CELSIUS_SCALE,
    SimulatorConfig,
)
from simulator.models import (
    PredictionPoint,
    PredictionReport,
    ThermalParameters,
)
from simulator.physics import (
    simulate,
    steady_state_chamber_temperature_c,
)


def fahrenheit_to_celsius(
    temperature_f: float,
) -> float:

    return (
        temperature_f
        - FAHRENHEIT_OFFSET
    ) * FAHRENHEIT_TO_CELSIUS_SCALE


def celsius_to_fahrenheit(
    temperature_c: float,
) -> float:

    return (
        temperature_c
        * CELSIUS_TO_FAHRENHEIT_SCALE
        + FAHRENHEIT_OFFSET
    )


def create_prediction_report(
    *,
    parameters: ThermalParameters,
    ambient_temperature_c: float,
    config: SimulatorConfig,
) -> PredictionReport:

    points: list[PredictionPoint] = []

    duration_seconds = (
        config.prediction_duration_hours
        * 3600.0
    )

    for heater_power_w in (
        config.prediction_wattages_w
    ):

        simulation = simulate(
            parameters=parameters,
            heater_power_w=heater_power_w,
            ambient_temperature_c=(
                ambient_temperature_c
            ),
            initial_chamber_temperature_c=(
                ambient_temperature_c
            ),
            initial_body_temperature_c=(
                ambient_temperature_c
            ),
            duration_seconds=(
                duration_seconds
            ),
            time_step_seconds=(
                config
                .simulation_step_seconds
            ),
        )

        steady_state_c = (
            steady_state_chamber_temperature_c(
                parameters=parameters,
                heater_power_w=heater_power_w,
                ambient_temperature_c=(
                    ambient_temperature_c
                ),
            )
        )

        points.append(
            PredictionPoint(
                heater_power_w=heater_power_w,
                final_temperature_c=(
                    simulation
                    .chamber_temperature_c[-1]
                ),
                steady_state_temperature_c=(
                    steady_state_c
                ),
            )
        )

    required_power = (
        estimate_required_power_for_target(
            parameters=parameters,
            ambient_temperature_c=(
                ambient_temperature_c
            ),
            target_temperature_f=(
                config
                .target_temperature_f
            ),
        )
    )

    return PredictionReport(
        points=tuple(points),
        estimated_power_for_target_w=(
            required_power
        ),
    )


def estimate_required_power_for_target(
    *,
    parameters: ThermalParameters,
    ambient_temperature_c: float,
    target_temperature_f: float,
) -> float | None:

    target_temperature_c = (
        fahrenheit_to_celsius(
            target_temperature_f
        )
    )

    required_temperature_rise_c = (
        target_temperature_c
        - ambient_temperature_c
    )

    if required_temperature_rise_c <= 0:
        return 0.0

    chamber_body = (
        parameters
        .chamber_body_conductance_w_per_k
    )

    body_ambient = (
        parameters
        .body_ambient_conductance_w_per_k
    )

    chamber_ambient = (
        parameters
        .chamber_ambient_conductance_w_per_k
    )

    effective_body_loss = (
        chamber_body
        * body_ambient
        / (
            chamber_body
            + body_ambient
        )
    )

    total_loss_w_per_k = (
        chamber_ambient
        + effective_body_loss
    )

    useful_power_required_w = (
        required_temperature_rise_c
        * total_loss_w_per_k
    )

    if parameters.heater_efficiency <= 0:
        return None

    return (
        useful_power_required_w
        / parameters.heater_efficiency
    )
