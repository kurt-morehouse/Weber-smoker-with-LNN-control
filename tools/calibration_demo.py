from core.calibration import ThermalCalibration
from core.calibrated_simulator import CalibratedChamberModel


def main() -> None:
    calibration = ThermalCalibration(
        schema_version=1,
        created_utc="demo",
        source_session="demo",
        source_probe="demo",
        source_channel="ambient_temperature_f",
        heater_power_w=1100.0,
        outside_temperature_f=75.0,
        initial_temperature_f=75.0,
        equilibrium_temperature_f=175.0,
        time_constant_seconds=7200.0,
        fit_r_squared=0.99,
        heat_loss_coefficient_w_per_f=11.0,
        effective_thermal_capacitance_j_per_f=79200.0,
    )

    model = CalibratedChamberModel(calibration)

    print(f"K: {model.heat_loss_coefficient_w_per_f:.3f} W/°F")
    print(f"C: {model.thermal_capacitance_j_per_f:.1f} J/°F")
    print(f"tau: {model.time_constant_seconds / 3600.0:.2f} h")
    print(
        "Power for 225°F:",
        f"{model.required_power_w(target_temperature_f=225.0, outside_temperature_f=75.0):.0f} W",
    )

    prediction = model.temperature_after(
        initial_temperature_f=75.0,
        elapsed_seconds=3 * 3600.0,
        heater_power_w=1100.0,
        outside_temperature_f=75.0,
    )

    print(
        "Predicted chamber after 3 h:",
        f"{prediction.chamber_temperature_f:.1f} °F",
    )


if __name__ == "__main__":
    main()
