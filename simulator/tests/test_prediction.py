import unittest

from simulator.models import ThermalParameters
from simulator.prediction import (
    celsius_to_fahrenheit,
    fahrenheit_to_celsius,
    estimate_required_power_for_target,
)


class PredictionTests(
    unittest.TestCase
):

    def test_temperature_round_trip(
        self,
    ) -> None:

        original_f = 225.0

        converted_c = fahrenheit_to_celsius(
            original_f
        )

        converted_f = celsius_to_fahrenheit(
            converted_c
        )

        self.assertAlmostEqual(
            converted_f,
            original_f,
            places=6,
        )

    def test_required_power_is_positive(
        self,
    ) -> None:

        parameters = ThermalParameters(
            chamber_heat_capacity_j_per_k=20_000.0,
            body_heat_capacity_j_per_k=100_000.0,
            chamber_body_conductance_w_per_k=10.0,
            chamber_ambient_conductance_w_per_k=2.0,
            body_ambient_conductance_w_per_k=5.0,
            heater_efficiency=0.8,
        )

        required_power = (
            estimate_required_power_for_target(
                parameters=parameters,
                ambient_temperature_c=20.0,
                target_temperature_f=225.0,
            )
        )

        self.assertIsNotNone(
            required_power
        )

        self.assertGreater(
            required_power,
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
