import csv
from pathlib import Path
from typing import List, Any
from custom_typings import Intersection, SignalPlan
from constants import DOCUMENTATION_CSV_PATH


# --- HELPER FUNCTIONS
def create_csv_file(file_path: str, headers: List[str]) -> None:
    """
    Create a new CSV file with the given headers.
    Overwrites if file already exists.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)


def add_row_to_csv_file(file_path: str, row: List[Any]) -> None:
    """
    Append a row to an existing CSV file.
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


# --- CREATE CSV FUNCTIONS
def create_comparative_analysis_csv(intersection: Intersection, num_phase: int) -> None:
    headers = [
        "signal_plan_name",
        "vehicle_count",
        "expected_vehicles",
        "avg_delay_timeLoss",
        "total_delay_timeLoss",
        "avg_waiting_time",
        "total_waiting_time",
        "avg_stops",
        "total_stops",
        "avg_queue_length",
        "total_queue_length",
        "avg_duration",
        "total_duration",
        "fitness_score",
        "weight_delay",
        "weight_queue",
        "weight_stops",
        "weight_duration",
        "weight_waiting",
        "weight_arrival_error"
    ]

    file_path = str(DOCUMENTATION_CSV_PATH /
                    f"{intersection.name}/comparative_analysis.csv")

    create_csv_file(file_path=file_path, headers=headers)


def create_signal_plans_csv(intersection: Intersection, num_phase: int) -> None:
    headers = ["signal_plan_name"]

    for i in range(num_phase):
        headers.extend(
            [f"phase_{i+1}_green", f"phase_{i+1}_amber", f"phase_{i+1}_all_red"])

    file_path = str(DOCUMENTATION_CSV_PATH /
                    f"{intersection.name}/signal_plans.csv")

    create_csv_file(file_path=file_path, headers=headers)


def create_scalability_assessment_csv(intersection: Intersection, signal_plan_name: str) -> None:
    headers = ["scenario", "total_flow",
               "total_queue_length", "avg_queue_length"]

    file_path = str(DOCUMENTATION_CSV_PATH /
                    f"{intersection.name}/scalability_assessment/{signal_plan_name}.csv")

    create_csv_file(file_path=file_path, headers=headers)


# --- ADD ROW TO CSV FUNCTIONS
def add_report_to_comparative_analysis_csv(
    report: dict,
    signal_plan_name: str,
    num_phase: int,
    intersection: Intersection,
    signal_plan: SignalPlan | None = None,
) -> None:
    """
    Add a simulation result (report) into the comparative analysis CSV.
    """

    file_path = DOCUMENTATION_CSV_PATH / \
        intersection.name / "comparative_analysis.csv"

    row = [
        signal_plan_name,
        report["vehicle_count"],
        report["expected_vehicles"],
        report["avg_delay_timeLoss"],
        report["total_delay_timeLoss"],
        report["avg_waiting_time"],
        report["total_waiting_time"],
        report["avg_stops"],
        report["total_stops"],
        report["avg_queue_length"],
        report["total_queue_length"],
        report["avg_duration"],
        report["total_duration"],
        report["fitness_score"],
        report["weights"]["delay"],
        report["weights"]["queue"],
        report["weights"]["stops"],
        report["weights"]["duration"],
        report["weights"]["waiting"],
        report["weights"]["arrival_error"],
    ]

    add_row_to_csv_file(file_path=str(file_path), row=row)


def add_signal_plan_to_signal_plans_csv(intersection: Intersection, signal_plan_name: str, num_phase: int, signal_plan: SignalPlan | None = None) -> None:
    file_path = DOCUMENTATION_CSV_PATH / \
        intersection.name / "signal_plans.csv"

    row = [signal_plan_name]

    # --- Phase timing values ---
    if signal_plan is not None:
        for i in range(num_phase):
            phase = signal_plan[i]
            row.extend([
                phase.green,
                phase.amber,
                phase.all_red
            ])
    else:
        # Fill with None if no phase data
        for _ in range(num_phase):
            row.extend([None, None, None])

    add_row_to_csv_file(file_path=str(file_path), row=row)


def add_scalability_assessment_row(
    intersection: Intersection,
    signal_plan_name: str,
    scenario: str,
    total_flow: float,
    total_queue_length: float,
    avg_queue_length: float
) -> None:
    """
    Append a row to the scalability assessment CSV for a given signal plan.
    """
    file_path = DOCUMENTATION_CSV_PATH / \
        intersection.name / "scalability_assessment" / \
        f"{signal_plan_name}.csv"

    row = [
        scenario,
        total_flow,
        total_queue_length,
        avg_queue_length
    ]

    add_row_to_csv_file(file_path=str(file_path), row=row)
