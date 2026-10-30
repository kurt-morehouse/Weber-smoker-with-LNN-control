import unittest

from simulator.physics import (
    simulate,
    steady_state_chamber_temperature_c,
)
from simulator.models import ThermalParameters


class PhysicsTests(
    unittest.TestCase
):

    def setUp(self) -> None:

        self.parameters = ThermalParameters(
            chamber_heat_capacity_j_per_k=20_000.0,
            body_heat_capacity_j_per_k=100_000.0,
            chamber_body_conductance_w_per_k=10.0,
            chamber_ambient_conductance_w_per_k=2.0,
            body_ambient_conductance_w_per_k=5.0,
            heater_efficiency=0.8,
        )

    def test_heating_increases_temperature(
        self,
    ) -> None:

        result = simulate(
            parameters=self.parameters,
            heater_power_w=1100.0,
            ambient_temperature_c=20.0,
            initial_chamber_temperature_c=20.0,
            initial_body_temperature_c=20.0,
            duration_seconds=600.0,
            time_step_seconds=1.0,
        )

        self.assertGreater(
            result.chamber_temperature_c[-1],
            20.0,
        )

    def test_zero_power_does_not_create_heat(
        self,
    ) -> None:

        result = simulate(
            parameters=self.parameters,
            heater_power_w=0.0,
            ambient_temperature_c=20.0,
            initial_chamber_temperature_c=20.0,
            initial_body_temperature_c=20.0,
            duration_seconds=600.0,
            time_step_seconds=1.0,
        )

        self.assertAlmostEqual(
            result.chamber_temperature_c[-1],
            20.0,
            places=5,
        )

    def test_more_power_produces_higher_steady_state(
        self,
    ) -> None:

        low = steady_state_chamber_temperature_c(
            parameters=self.parameters,
            heater_power_w=800.0,
            ambient_temperature_c=20.0,
        )

        high = steady_state_chamber_temperature_c(
            parameters=self.parameters,
            heater_power_w=1500.0,
            ambient_temperature_c=20.0,
        )

        self.assertGreater(
            high,
            low,
        )


if __name__ == "__main__":
    unittest.main()
