import math
import random

from simulator.config import (
    MAX_BODY_AMBIENT_CONDUCTANCE_W_PER_K,
    MAX_BODY_HEAT_CAPACITY_J_PER_K,
    MAX_CHAMBER_AMBIENT_CONDUCTANCE_W_PER_K,
    MAX_CHAMBER_BODY_CONDUCTANCE_W_PER_K,
    MAX_CHAMBER_HEAT_CAPACITY_J_PER_K,
    MAX_HEATER_EFFICIENCY,
    MIN_BODY_AMBIENT_CONDUCTANCE_W_PER_K,
    MIN_BODY_HEAT_CAPACITY_J_PER_K,
    MIN_CHAMBER_AMBIENT_CONDUCTANCE_W_PER_K,
    MIN_CHAMBER_BODY_CONDUCTANCE_W_PER_K,
    MIN_CHAMBER_HEAT_CAPACITY_J_PER_K,
    MIN_HEATER_EFFICIENCY,
    SimulatorConfig,
)

from simulator.models import (
    CalibrationResult,
    ExperimentData,
    ThermalParameters,
)

from simulator.physics import simulate


def calibrate(
    experiment: ExperimentData,
    config: SimulatorConfig,
) -> CalibrationResult:

    rng = random.Random(
        config.random_seed
    )

    ambient_temperature_c = (
        _ambient_temperature_c(
            experiment
        )
    )

    duration_seconds = min(
        experiment.internal.time_seconds[-1],
        experiment.external.time_seconds[-1],
    )

    best_parameters: ThermalParameters | None = None
    best_rmse_c = math.inf

    print(
        f"Calibration iterations: "
        f"{config.calibration_iterations:,}"
    )

    for iteration in range(
        config.calibration_iterations
    ):

        parameters = _random_parameters(
            rng
        )

        simulation = simulate(
            parameters=parameters,
            heater_power_w=(
                experiment
                .metadata
                .heater_power_w
            ),
            ambient_temperature_c=(
                ambient_temperature_c
            ),
            initial_chamber_temperature_c=(
                experiment
                .internal
                .temperature_c[0]
            ),
            initial_body_temperature_c=(
                experiment
                .external
                .temperature_c[0]
            ),
            duration_seconds=duration_seconds,
            time_step_seconds=(
                config
                .calibration_step_seconds
            ),
        )

        rmse_c = _combined_rmse(
            experiment=experiment,
            simulated_time=(
                simulation.time_seconds
            ),
            simulated_chamber=(
                simulation
                .chamber_temperature_c
            ),
            simulated_body=(
                simulation
                .body_temperature_c
            ),
        )

        if rmse_c < best_rmse_c:

            best_rmse_c = rmse_c
            best_parameters = parameters

            print(
                f"  iteration "
                f"{iteration:5d} | "
                f"best RMSE "
                f"{rmse_c:6.3f} °C"
            )

    if best_parameters is None:
        raise RuntimeError(
            "Calibration failed."
        )

    return CalibrationResult(
        parameters=best_parameters,
        rmse_c=best_rmse_c,
    )


def _ambient_temperature_c(
    experiment: ExperimentData,
) -> float:

    ambient_f = (
        experiment
        .metadata
        .ambient_temperature_f
    )

    if ambient_f is None:
        return (
            experiment
            .external
            .temperature_c[0]
        )

    return (
        ambient_f - 32.0
    ) * 5.0 / 9.0


def _random_parameters(
    rng: random.Random,
) -> ThermalParameters:

    return ThermalParameters(
        chamber_heat_capacity_j_per_k=(
            _log_uniform(
                rng,
                MIN_CHAMBER_HEAT_CAPACITY_J_PER_K,
                MAX_CHAMBER_HEAT_CAPACITY_J_PER_K,
            )
        ),
        body_heat_capacity_j_per_k=(
            _log_uniform(
                rng,
                MIN_BODY_HEAT_CAPACITY_J_PER_K,
                MAX_BODY_HEAT_CAPACITY_J_PER_K,
            )
        ),
        chamber_body_conductance_w_per_k=(
            _log_uniform(
                rng,
                MIN_CHAMBER_BODY_CONDUCTANCE_W_PER_K,
                MAX_CHAMBER_BODY_CONDUCTANCE_W_PER_K,
            )
        ),
        chamber_ambient_conductance_w_per_k=(
            _log_uniform(
                rng,
                MIN_CHAMBER_AMBIENT_CONDUCTANCE_W_PER_K,
                MAX_CHAMBER_AMBIENT_CONDUCTANCE_W_PER_K,
            )
        ),
        body_ambient_conductance_w_per_k=(
            _log_uniform(
                rng,
                MIN_BODY_AMBIENT_CONDUCTANCE_W_PER_K,
                MAX_BODY_AMBIENT_CONDUCTANCE_W_PER_K,
            )
        ),
        heater_efficiency=(
            rng.uniform(
                MIN_HEATER_EFFICIENCY,
                MAX_HEATER_EFFICIENCY,
            )
        ),
    )


def _log_uniform(
    rng: random.Random,
    minimum: float,
    maximum: float,
) -> float:

    return math.exp(
        rng.uniform(
            math.log(minimum),
            math.log(maximum),
        )
    )


def _combined_rmse(
    *,
    experiment: ExperimentData,
    simulated_time: tuple[float, ...],
    simulated_chamber: tuple[float, ...],
    simulated_body: tuple[float, ...],
) -> float:

    squared_errors: list[float] = []

    for (
        time_seconds,
        measured_temperature_c,
    ) in zip(
        experiment.internal.time_seconds,
        experiment.internal.temperature_c,
    ):

        prediction = _interpolate(
            target_time=time_seconds,
            times=simulated_time,
            values=simulated_chamber,
        )

        squared_errors.append(
            (
                prediction
                - measured_temperature_c
            ) ** 2
        )

    for (
        time_seconds,
        measured_temperature_c,
    ) in zip(
        experiment.external.time_seconds,
        experiment.external.temperature_c,
    ):

        prediction = _interpolate(
            target_time=time_seconds,
            times=simulated_time,
            values=simulated_body,
        )

        squared_errors.append(
            (
                prediction
                - measured_temperature_c
            ) ** 2
        )

    return math.sqrt(
        sum(squared_errors)
        / len(squared_errors)
    )


def _interpolate(
    *,
    target_time: float,
    times: tuple[float, ...],
    values: tuple[float, ...],
) -> float:

    if target_time <= times[0]:
        return values[0]

    if target_time >= times[-1]:
        return values[-1]

    for index in range(
        1,
        len(times),
    ):

        if times[index] < target_time:
            continue

        left_time = times[index - 1]
        right_time = times[index]

        left_value = values[index - 1]
        right_value = values[index]

        fraction = (
            target_time - left_time
        ) / (
            right_time - left_time
        )

        return (
            left_value
            + fraction
            * (
                right_value
                - left_value
            )
        )

    return values[-1]
