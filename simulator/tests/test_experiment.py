import unittest

from simulator.experiment import (
    fahrenheit_to_celsius,
)


class ExperimentTests(
    unittest.TestCase
):

    def test_freezing_point(
        self,
    ) -> None:

        self.assertAlmostEqual(
            fahrenheit_to_celsius(
                32.0
            ),
            0.0,
            places=6,
        )

    def test_boiling_point(
        self,
    ) -> None:

        self.assertAlmostEqual(
            fahrenheit_to_celsius(
                212.0
            ),
            100.0,
            places=6,
        )


if __name__ == "__main__":
    unittest.main()
