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
def create_comparative_analysis_csv(intersection: Intersection, num_phase: int, label: str = "") -> None:
    """
    Create a comparative analysis CSV for a given intersection.
    """
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

    folder_path = DOCUMENTATION_CSV_PATH / \
        intersection.name / (label if label else "")
    folder_path.mkdir(parents=True, exist_ok=True)
    file_path = folder_path / "comparative_analysis.csv"

    create_csv_file(file_path=str(file_path), headers=headers)


def create_signal_plans_csv(intersection: Intersection, num_phase: int, label: str = "") -> None:
    """
    Create a signal plans CSV for a given intersection.
    """
    headers = ["signal_plan_name"]
    for i in range(num_phase):
        headers.extend(
            [f"phase_{i+1}_green", f"phase_{i+1}_amber", f"phase_{i+1}_all_red"])

    folder_path = DOCUMENTATION_CSV_PATH / \
        intersection.name / (label if label else "")
    folder_path.mkdir(parents=True, exist_ok=True)
    file_path = folder_path / "signal_plans.csv"

    create_csv_file(file_path=file_path, headers=headers)


def create_scalability_assessment_csv(intersection: Intersection, signal_plan_name: str, label: str) -> None:
    headers = ["scenario", "total_flow",
               "total_queue_length", "avg_queue_length"]

    intersection_name = intersection.name.strip()
    label_clean = label.strip()
    signal_plan_name_clean = signal_plan_name.strip()

    file_path = DOCUMENTATION_CSV_PATH / intersection_name / label_clean / \
        "scalability_assessment" / f"{signal_plan_name_clean}.csv"

    file_path.parent.mkdir(parents=True, exist_ok=True)
    create_csv_file(file_path=str(file_path), headers=headers)


# --- ADD ROW TO CSV FUNCTIONS
def add_report_to_comparative_analysis_csv(
    report: dict,
    signal_plan_name: str,
    num_phase: int,
    intersection: Intersection,
    signal_plan: SignalPlan | None = None,
    label: str = ""
) -> None:
    """
    Add a simulation result (report) into the comparative analysis CSV.
    """
    folder_path = DOCUMENTATION_CSV_PATH / \
        intersection.name / (label if label else "")
    file_path = folder_path / "comparative_analysis.csv"

    row = [
        signal_plan_name,
        report.get("vehicle_count"),
        report.get("expected_vehicles"),
        report.get("avg_delay_timeLoss"),
        report.get("total_delay_timeLoss"),
        report.get("avg_waiting_time"),
        report.get("total_waiting_time"),
        report.get("avg_stops"),
        report.get("total_stops"),
        report.get("avg_queue_length"),
        report.get("total_queue_length"),
        report.get("avg_duration"),
        report.get("total_duration"),
        report.get("fitness_score"),
        report.get("weights", {}).get("delay"),
        report.get("weights", {}).get("queue"),
        report.get("weights", {}).get("stops"),
        report.get("weights", {}).get("duration"),
        report.get("weights", {}).get("waiting"),
        report.get("weights", {}).get("arrival_error"),
    ]

    add_row_to_csv_file(file_path=str(file_path), row=row)


def add_signal_plan_to_signal_plans_csv(
    intersection: Intersection,
    signal_plan_name: str,
    num_phase: int,
    signal_plan: SignalPlan | None = None,
    label: str = ""
) -> None:
    """
    Add a signal plan into the signal plans CSV.
    """
    folder_path = DOCUMENTATION_CSV_PATH / \
        intersection.name / (label if label else "")
    file_path = folder_path / "signal_plans.csv"

    row = [signal_plan_name]

    # --- Phase timing values ---
    if signal_plan is not None:
        for i in range(num_phase):
            phase = signal_plan[i]
            row.extend([phase.green, phase.amber, phase.all_red])
    else:
        # Fill with None if no phase data
        for _ in range(num_phase):
            row.extend([None, None, None])

    add_row_to_csv_file(file_path=str(file_path), row=row)


def add_scalability_assessment_row(
    label: str,
    intersection: Intersection,
    signal_plan_name: str,
    scenario: str,
    total_flow: float,
    total_queue_length: float,
    avg_queue_length: float
) -> None:
    intersection_name = intersection.name.strip()
    label_clean = label.strip()
    signal_plan_name_clean = signal_plan_name.strip()

    file_path = DOCUMENTATION_CSV_PATH / intersection_name / label_clean / \
        "scalability_assessment" / f"{signal_plan_name_clean}.csv"

    file_path.parent.mkdir(parents=True, exist_ok=True)

    row = [scenario, total_flow, total_queue_length, avg_queue_length]
    add_row_to_csv_file(file_path=str(file_path), row=row)
