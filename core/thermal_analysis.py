from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class ThermalPowerEstimate:
    equilibrium_temperature_f: float
    time_constant_seconds: float
    initial_temperature_f: float
    r_squared: float
    heater_power_w: float
    target_temperature_f: float
    outside_temperature_f: float
    estimated_required_power_w: float | None

    @property
    def additional_power_w(self) -> float | None:
        if self.estimated_required_power_w is None:
            return None
        return self.estimated_required_power_w - self.heater_power_w


def _linear_fit(x: list[float], y: list[float]) -> tuple[float, float, float]:
    n = len(x)
    sx = sum(x)
    sy = sum(y)
    sxx = sum(v * v for v in x)
    sxy = sum(a * b for a, b in zip(x, y))
    denom = n * sxx - sx * sx

    if abs(denom) < 1e-12:
        raise ValueError("Insufficient variation for thermal fit.")

    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    sse = sum(
        (actual - (intercept + slope * xv)) ** 2
        for xv, actual in zip(x, y)
    )
    return intercept, slope, sse


def estimate_full_power_response(
    time_seconds: Iterable[float],
    temperature_f: Iterable[float],
    heater_power_w: float,
    target_temperature_f: float,
    outside_temperature_f: float,
) -> ThermalPowerEstimate:
    """
    Fit a first-order heating response:

        T(t) = T_inf + (T0 - T_inf) * exp(-t/tau)

    No SciPy dependency is required. Tau is found by logarithmic grid search.
    """
    pairs = [
        (float(t), float(temp))
        for t, temp in zip(time_seconds, temperature_f)
        if math.isfinite(float(t)) and math.isfinite(float(temp))
    ]

    if len(pairs) < 20:
        raise ValueError("At least 20 valid samples are required.")

    pairs.sort(key=lambda item: item[0])

    temperatures = [p[1] for p in pairs]
    peak_index = max(range(len(temperatures)), key=temperatures.__getitem__)
    pairs = pairs[: peak_index + 1]

    if len(pairs) < 20:
        raise ValueError("Not enough heating data before the temperature peak.")

    t0 = pairs[0][0]
    times = [p[0] - t0 for p in pairs]
    temps = [p[1] for p in pairs]
    duration = times[-1]

    if duration <= 0:
        raise ValueError("Experiment duration must be greater than zero.")

    max_fit_points = 2000
    stride = max(1, len(times) // max_fit_points)
    fit_t = times[::stride]
    fit_y = temps[::stride]

    tau_min = max(10.0, duration / 100.0)
    tau_max = max(tau_min * 1.01, duration * 10.0)

    best = None
    steps = 300

    for i in range(steps):
        fraction = i / (steps - 1)
        tau = tau_min * ((tau_max / tau_min) ** fraction)
        x = [math.exp(-t / tau) for t in fit_t]

        try:
            equilibrium, coefficient, sse = _linear_fit(x, fit_y)
        except ValueError:
            continue

        if equilibrium <= fit_y[0] or coefficient >= 0:
            continue

        if best is None or sse < best[0]:
            best = (sse, tau, equilibrium, coefficient)

    if best is None:
        raise ValueError("Could not obtain a physically plausible heating fit.")

    sse, tau, equilibrium, coefficient = best
    mean_y = sum(fit_y) / len(fit_y)
    sst = sum((v - mean_y) ** 2 for v in fit_y)
    r_squared = 1.0 - sse / sst if sst > 0 else 0.0

    required = None
    achieved_rise = equilibrium - outside_temperature_f
    target_rise = target_temperature_f - outside_temperature_f

    if heater_power_w > 0 and achieved_rise > 1.0 and target_rise > 0:
        required = heater_power_w * target_rise / achieved_rise

    return ThermalPowerEstimate(
        equilibrium_temperature_f=equilibrium,
        time_constant_seconds=tau,
        initial_temperature_f=fit_y[0],
        r_squared=r_squared,
        heater_power_w=heater_power_w,
        target_temperature_f=target_temperature_f,
        outside_temperature_f=outside_temperature_f,
        estimated_required_power_w=required,
    )
