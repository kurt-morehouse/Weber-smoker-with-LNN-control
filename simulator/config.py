from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Temperature conversion
# ---------------------------------------------------------------------------

FAHRENHEIT_OFFSET: float = 32.0
FAHRENHEIT_TO_CELSIUS_SCALE: float = 5.0 / 9.0
CELSIUS_TO_FAHRENHEIT_SCALE: float = 9.0 / 5.0


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------

SECONDS_PER_MINUTE: float = 60.0
SECONDS_PER_HOUR: float = 3600.0


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

DEFAULT_SIMULATION_STEP_SECONDS: float = 2.0
DEFAULT_CALIBRATION_STEP_SECONDS: float = 5.0
DEFAULT_CALIBRATION_ITERATIONS: int = 10_000
DEFAULT_RANDOM_SEED: int = 42


# ---------------------------------------------------------------------------
# Calibration bounds
# ---------------------------------------------------------------------------

MIN_HEATER_EFFICIENCY: float = 0.10
MAX_HEATER_EFFICIENCY: float = 1.00

MIN_CHAMBER_HEAT_CAPACITY_J_PER_K: float = 1_000.0
MAX_CHAMBER_HEAT_CAPACITY_J_PER_K: float = 200_000.0

MIN_BODY_HEAT_CAPACITY_J_PER_K: float = 5_000.0
MAX_BODY_HEAT_CAPACITY_J_PER_K: float = 1_000_000.0

MIN_CHAMBER_BODY_CONDUCTANCE_W_PER_K: float = 0.1
MAX_CHAMBER_BODY_CONDUCTANCE_W_PER_K: float = 100.0

MIN_CHAMBER_AMBIENT_CONDUCTANCE_W_PER_K: float = 0.1
MAX_CHAMBER_AMBIENT_CONDUCTANCE_W_PER_K: float = 50.0

MIN_BODY_AMBIENT_CONDUCTANCE_W_PER_K: float = 0.1
MAX_BODY_AMBIENT_CONDUCTANCE_W_PER_K: float = 100.0


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

DEFAULT_TARGET_TEMPERATURE_F: float = 225.0
DEFAULT_PREDICTION_DURATION_HOURS: float = 4.0

PREDICTION_WATTAGES_W: tuple[float, ...] = (
    800.0,
    900.0,
    1000.0,
    1100.0,
    1200.0,
    1300.0,
    1400.0,
    1500.0,
    1600.0,
)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEFAULT_EXPERIMENT_DIRECTORY: Path = Path(__file__).resolve().parent / "experiments/baseline_1100w"


@dataclass(frozen=True)
class SimulatorConfig:
    simulation_step_seconds: float = DEFAULT_SIMULATION_STEP_SECONDS
    calibration_step_seconds: float = DEFAULT_CALIBRATION_STEP_SECONDS
    calibration_iterations: int = DEFAULT_CALIBRATION_ITERATIONS
    random_seed: int = DEFAULT_RANDOM_SEED
    target_temperature_f: float = DEFAULT_TARGET_TEMPERATURE_F
    prediction_duration_hours: float = DEFAULT_PREDICTION_DURATION_HOURS
    prediction_wattages_w: tuple[float, ...] = PREDICTION_WATTAGES_W


CONFIG = SimulatorConfig()
