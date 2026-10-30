import traceback

from simulator.calibration import calibrate
from simulator.config import CONFIG, DEFAULT_EXPERIMENT_DIRECTORY
from simulator.experiment import load_experiment
from simulator.physics import simulate
from simulator.plotting import plot_comparison
from simulator.prediction import create_prediction_report
from simulator.reporting import print_calibration_result, print_experiment_summary, print_prediction_report

def main() -> None:
    print()
    print("Starting Weber simulator V3.1...")
    print()
    try:
        print(f"Experiment directory: {DEFAULT_EXPERIMENT_DIRECTORY}")
        print("Loading experiment metadata...")
        experiment = load_experiment(DEFAULT_EXPERIMENT_DIRECTORY)
        print("Loading experiment metadata... OK")
        print_experiment_summary(experiment)
        print("Running calibration...")
        calibration = calibrate(experiment, CONFIG)
        print_calibration_result(calibration)
        ambient_temperature_c = experiment.external.temperature_c[0]
        duration_seconds = min(experiment.internal.time_seconds[-1], experiment.external.time_seconds[-1])
        baseline_simulation = simulate(
            parameters=calibration.parameters,
            heater_power_w=experiment.metadata.heater_power_w,
            ambient_temperature_c=ambient_temperature_c,
            initial_chamber_temperature_c=experiment.internal.temperature_c[0],
            initial_body_temperature_c=experiment.external.temperature_c[0],
            duration_seconds=duration_seconds,
            time_step_seconds=CONFIG.simulation_step_seconds,
        )
        prediction_report = create_prediction_report(
            parameters=calibration.parameters,
            ambient_temperature_c=ambient_temperature_c,
            config=CONFIG,
        )
        print_prediction_report(prediction_report, CONFIG.target_temperature_f)
        print()
        print("Opening calibration plot...")
        plot_comparison(experiment, baseline_simulation)
        print()
        print("Simulation complete.")
    except Exception as exc:
        print()
        print("=" * 72)
        print("SIMULATOR ERROR")
        print("=" * 72)
        print(f"{type(exc).__name__}: {exc}")
        print()
        print("Full traceback:")
        print()
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
