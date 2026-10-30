from simulator.models import (
    SimulationResult,
    ThermalParameters,
)


def simulate(
    *,
    parameters: ThermalParameters,
    heater_power_w: float,
    ambient_temperature_c: float,
    initial_chamber_temperature_c: float,
    initial_body_temperature_c: float,
    duration_seconds: float,
    time_step_seconds: float,
) -> SimulationResult:

    chamber_temperature_c = (
        initial_chamber_temperature_c
    )

    body_temperature_c = (
        initial_body_temperature_c
    )

    times: list[float] = []
    chamber_values: list[float] = []
    body_values: list[float] = []

    elapsed_seconds = 0.0

    while (
        elapsed_seconds
        <= duration_seconds
    ):

        times.append(
            elapsed_seconds
        )

        chamber_values.append(
            chamber_temperature_c
        )

        body_values.append(
            body_temperature_c
        )

        useful_heater_power_w = (
            heater_power_w
            * parameters.heater_efficiency
        )

        chamber_to_body_w = (
            parameters
            .chamber_body_conductance_w_per_k
            * (
                chamber_temperature_c
                - body_temperature_c
            )
        )

        chamber_to_ambient_w = (
            parameters
            .chamber_ambient_conductance_w_per_k
            * (
                chamber_temperature_c
                - ambient_temperature_c
            )
        )

        body_to_ambient_w = (
            parameters
            .body_ambient_conductance_w_per_k
            * (
                body_temperature_c
                - ambient_temperature_c
            )
        )

        chamber_net_power_w = (
            useful_heater_power_w
            - chamber_to_body_w
            - chamber_to_ambient_w
        )

        body_net_power_w = (
            chamber_to_body_w
            - body_to_ambient_w
        )

        chamber_rate_c_per_second = (
            chamber_net_power_w
            / parameters
            .chamber_heat_capacity_j_per_k
        )

        body_rate_c_per_second = (
            body_net_power_w
            / parameters
            .body_heat_capacity_j_per_k
        )

        chamber_temperature_c += (
            chamber_rate_c_per_second
            * time_step_seconds
        )

        body_temperature_c += (
            body_rate_c_per_second
            * time_step_seconds
        )

        elapsed_seconds += (
            time_step_seconds
        )

    return SimulationResult(
        time_seconds=tuple(times),
        chamber_temperature_c=tuple(
            chamber_values
        ),
        body_temperature_c=tuple(
            body_values
        ),
    )


def steady_state_chamber_temperature_c(
    *,
    parameters: ThermalParameters,
    heater_power_w: float,
    ambient_temperature_c: float,
) -> float:

    chamber_body = (
        parameters
        .chamber_body_conductance_w_per_k
    )

    chamber_ambient = (
        parameters
        .chamber_ambient_conductance_w_per_k
    )

    body_ambient = (
        parameters
        .body_ambient_conductance_w_per_k
    )

    effective_body_path = (
        chamber_body
        * body_ambient
        / (
            chamber_body
            + body_ambient
        )
    )

    total_effective_loss = (
        chamber_ambient
        + effective_body_path
    )

    useful_power = (
        heater_power_w
        * parameters.heater_efficiency
    )

    temperature_rise_c = (
        useful_power
        / total_effective_loss
    )

    return (
        ambient_temperature_c
        + temperature_rise_c
    )
