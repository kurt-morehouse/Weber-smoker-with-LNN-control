import unittest

from simulator.calibration import _interpolate


class CalibrationTests(
    unittest.TestCase
):

    def test_linear_interpolation(
        self,
    ) -> None:

        value = _interpolate(
            target_time=5.0,
            times=(
                0.0,
                10.0,
            ),
            values=(
                20.0,
                30.0,
            ),
        )

        self.assertAlmostEqual(
            value,
            25.0,
        )


if __name__ == "__main__":
    unittest.main()
