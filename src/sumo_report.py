import xml.etree.ElementTree as ET
from statistics import mean
from pathlib import Path
from subprocess import DEVNULL
import subprocess
import random
import json
from typing import List
from custom_typings import Intersection, SignalPhase


def compute_expected_arrivals(intersection: Intersection) -> float:
    """
    Compute the expected total arrivals for an intersection based on movement.average_flow.

    Args:
        intersection: Intersection object containing a list of movements, 
                      each with an average_flow attribute (vehicles per hour).

    Returns:
        expected_total_arrivals: float, sum of expected arrivals across all movements 
                                 in the intersection.
    """
    expected_total_arrivals = 0.0

    for mv in intersection.movements:
        # average_flow is in vehicles per hour
        expected_total_arrivals += mv.average_flow

    return expected_total_arrivals


# ===============================
#   RUN SUMO (OPTIONAL)
# ===============================
def run_sumo(
        sumocfg_path: str,
        tripinfo_out: str,
        net_file: str = None,
        detector_out: str = None,
        tls_path: str = None,
        randomize: bool = True):
    """
    Run SUMO with optional randomness in arrival behavior and driver behavior.
    """

    additional_files = []

    # If detectors enabled
    if detector_out is not None:
        if net_file is None:
            raise ValueError(
                "net_file must be provided if detector_out is requested.")
        generate_e2_detectors(net_file, detector_out)
        additional_files.append(detector_out)

    # Traffic lights file if provided
    if tls_path:
        additional_files.append(tls_path)

    cmd = [
        "sumo",
        "-c", sumocfg_path,
        "--tripinfo-output", tripinfo_out,
    ]

    if additional_files:
        cmd += ["--additional-files", ",".join(additional_files)]

    if randomize:
        cmd += [
            "--seed", str(random.randint(1, 99999999)),  # Random seed
            "--random"                                   # Random departure times
        ]

    # print("Running SUMO:", " ".join(cmd))
    subprocess.run(cmd, check=True, stdout=DEVNULL)
    # print("SUMO simulation complete.")


# ===============================
#   GENERATE E2 DETECTORS XML
# ===============================
def generate_e2_detectors(net_path, out_path, use_full_lane=True, detector_length=30):
    """
    Generate E2 lane-area detectors for all incoming lanes at traffic-light junctions.

    Parameters:
        net_path (str): Path to the SUMO network XML (.net.xml)
        out_path (str): Path to output the detectors XML (.xml)
        use_full_lane (bool): If True, detector length = lane length
        detector_length (float): Length of detector in meters (used if use_full_lane=False)
    """
    tree = ET.parse(net_path)
    root = tree.getroot()

    # Step 1: get all lane lengths
    lane_lengths = {lane.attrib["id"]: float(lane.attrib["length"])
                    for lane in root.findall("edge/lane")}
    # print(f"Found {len(lane_lengths)} lanes in network.")

    # Step 2: find incoming lanes at traffic-light junctions
    incoming_lanes = []
    for j in root.findall("junction"):
        if j.attrib.get("type") == "traffic_light":
            incoming_lanes.extend(j.attrib.get("incLanes", "").split())

    # Step 3: build <additional> file
    add = ET.Element("additional")
    for lane in incoming_lanes:
        if lane not in lane_lengths:
            # print(
            #     f"Warning: lane {lane} not found in network, skipping detector.")
            continue

        lane_len = lane_lengths[lane]

        if use_full_lane:
            det_len = lane_len
            pos = 0  # detector covers the whole lane
        else:
            det_len = min(detector_length, lane_len)
            pos = lane_len - det_len  # detector at end of lane

        det = ET.SubElement(add, "e2Detector")
        det.set("id", f"e2_{lane}")
        det.set("lane", lane)
        det.set("pos", str(pos))
        det.set("length", str(det_len))
        det.set("freq", "1")
        det.set("file", f"det_{lane}.xml")

    ET.ElementTree(add).write(out_path, encoding="UTF-8", xml_declaration=True)
    # print(f"E2 detectors generated: {out_path}")


# ===============================
#   PARSE TRIPINFO.XML
# ===============================
def parse_tripinfo(tripinfo_path: str):
    tree = ET.parse(tripinfo_path)
    root = tree.getroot()

    timeLoss_list = []
    waitingTime_list = []
    waitingCount_list = []
    duration_list = []
    vehicle_count = 0

    for trip in root.findall("tripinfo"):
        timeLoss = float(trip.get("timeLoss", 0))
        waitingTime = float(trip.get("waitingTime", 0))
        waitingCount = float(trip.get("waitingCount", 0))
        duration = float(trip.get("duration", 0))

        timeLoss_list.append(timeLoss)
        waitingTime_list.append(waitingTime)
        waitingCount_list.append(waitingCount)
        duration_list.append(duration)
        vehicle_count += 1

    # Prevent division by zero
    if vehicle_count == 0:
        return {
            "vehicle_count": 0,
            "avg_delay": 0,
            "total_delay": 0,
            "avg_waiting": 0,
            "total_waiting": 0,
            "avg_stops": 0,
            "total_stops": 0,
            "avg_duration": 0
        }

    total_delay = sum(timeLoss_list)
    total_waiting = sum(waitingTime_list)
    total_stops = sum(waitingCount_list)

    return {
        "vehicle_count": vehicle_count,
        "avg_delay": total_delay / vehicle_count,
        "total_delay": total_delay,
        "avg_waiting": total_waiting / vehicle_count,
        "total_waiting": total_waiting,
        "avg_stops": total_stops / vehicle_count,
        "total_stops": total_stops,
        "avg_duration": sum(duration_list) / vehicle_count
    }


# ===============================
#   PARSE LANE DETECTOR OUTPUT (OPTIONAL)
# ===============================
def parse_lane_detectors(detector_path: str, base_dir: Path = None):
    if detector_path is None or not Path(detector_path).exists():
        return {
            "avg_queue": 0,
            "total_queue": 0,
            "num_intervals": 0
        }

    tree = ET.parse(detector_path)
    root = tree.getroot()

    queue_values = []

    for e2 in root.findall("e2Detector"):
        det_file = e2.attrib.get("file")
        if det_file is None:
            continue

        det_path = Path(det_file)
        if base_dir is not None:
            det_path = Path(base_dir) / det_file

        if not det_path.exists():
            continue

        det_tree = ET.parse(det_path)
        det_root = det_tree.getroot()

        for interval in det_root.findall(".//interval"):
            # Use meanMaxJamLengthInVehicles as the queue length
            max_queue = float(interval.attrib.get(
                "meanMaxJamLengthInVehicles", 0))
            queue_values.append(max_queue)

    total_queue = sum(queue_values)
    avg_queue = mean(queue_values) if queue_values else 0
    num_intervals = len(queue_values)

    return {
        "avg_queue": avg_queue,
        "total_queue": total_queue,
        "num_intervals": num_intervals
    }


# ===============================
#   FITNESS FUNCTION
# ===============================
def compute_fitness(avg_delay, avg_waiting, avg_queue, avg_stops, avg_duration,
                    expected_arrivals, counted_arrivals,
                    w_delay=0.35, w_waiting=0.10, w_queue=0.25,
                    w_stops=0.20, w_duration=0.05, w_arrival_error=0.05):
    """
    Lower fitness = better performance.
    Uses AVERAGE metrics.
    Penalizes mismatch between expected and served vehicles.
    """

    # Arrival Service Error (percentage)
    if expected_arrivals > 0:
        ase = abs(expected_arrivals - counted_arrivals) / expected_arrivals
    else:
        ase = 0.0

    fitness = (
        (w_delay * avg_delay) +
        (w_waiting * avg_waiting) +
        (w_queue * avg_queue) +
        (w_stops * avg_stops) +
        (w_duration * avg_duration) +
        (w_arrival_error * ase)
    )

    return fitness


# ===============================
#   MASTER REPORT FUNCTION
# ===============================
def generate_report(
        intersection: Intersection,
        tripinfo_path: str,
        detector_path: str = None,
        base_dir: Path = None,
        weights=(0.35, 0.2, 0.2, 0.1, 0.1, 0.05),  # updated weights tuple
        save_json: str = None):

    # --- Parse data sources ---
    tripinfo = parse_tripinfo(tripinfo_path)
    detector = parse_lane_detectors(detector_path, base_dir) if detector_path else {
        "avg_queue": 0, "total_queue": 0}

    avg_delay = tripinfo["avg_delay"]           # from timeLoss
    avg_waiting = tripinfo["avg_waiting"]       # from waitingTime
    avg_stops = tripinfo["avg_stops"]           # from waitingCount
    avg_duration = tripinfo["avg_duration"]
    avg_queue = detector.get("avg_queue", 0)
    vehicle_count = tripinfo["vehicle_count"]

    # Totals
    total_delay = tripinfo.get("total_delay", avg_delay * vehicle_count)
    total_waiting = tripinfo.get("total_waiting", avg_waiting * vehicle_count)
    total_stops = tripinfo.get("total_stops", avg_stops * vehicle_count)
    total_duration = tripinfo.get(
        "total_duration", avg_duration * vehicle_count)
    total_queue = detector.get("total_queue", avg_queue * vehicle_count)

    expected_arrivals = compute_expected_arrivals(intersection)

    # --- Compute fitness ---
    w_delay, w_queue, w_stops, w_duration, w_waiting, w_arrival_error = weights

    fitness = compute_fitness(
        avg_delay=avg_delay,
        avg_waiting=avg_waiting,
        avg_queue=avg_queue,
        avg_stops=avg_stops,
        avg_duration=avg_duration,
        expected_arrivals=expected_arrivals,
        counted_arrivals=vehicle_count,
        w_delay=w_delay,
        w_waiting=w_waiting,
        w_queue=w_queue,
        w_stops=w_stops,
        w_duration=w_duration,
        w_arrival_error=w_arrival_error
    )

    # --- Build final report ---
    report = {
        "vehicle_count": vehicle_count,
        "expected_vehicles": expected_arrivals,
        "avg_delay_timeLoss": avg_delay,
        "total_delay_timeLoss": total_delay,
        "avg_waiting_time": avg_waiting,
        "total_waiting_time": total_waiting,
        "avg_stops": avg_stops,
        "total_stops": total_stops,
        "avg_queue_length": avg_queue,
        "total_queue_length": total_queue,
        "avg_duration": avg_duration,
        "total_duration": total_duration,
        "fitness_score": fitness,
        "weights": {
            "delay": w_delay,
            "queue": w_queue,
            "stops": w_stops,
            "duration": w_duration,
            "waiting": w_waiting,
            "arrival_error": w_arrival_error
        }
    }

    if save_json:
        with open(save_json, "w") as f:
            json.dump(report, f, indent=4)
        # print(f"Saved report to {save_json}")

    return report


def display_report(report: dict, header="SIMULATION REPORT", footer=""):
    print(f"\n=============== {header} ===============")
    print(f"Vehicles Simulated:       {report['vehicle_count']}")
    print(f"Average Delay:            {report['avg_delay_timeLoss']:.2f} s")
    print(f"Average Waiting Time:     {report['avg_waiting_time']:.2f} s")
    print(f"Average Stops:            {report['avg_stops']:.2f}")
    print(f"Average Queue Length:     {report['avg_queue_length']:.2f} veh")
    print(f"Average Duration:         {report['avg_duration']:.2f} s")
    print(f"Total Delay:              {report['total_delay_timeLoss']:.2f} s")
    print(f"Total Waiting Time:       {report['total_waiting_time']:.2f} s")
    print(f"Total Stops:              {report['total_stops']:.2f}")
    print(f"Total Queue Length:       {report['total_queue_length']:.2f} veh")
    print(f"Total Duration:           {report['total_duration']:.2f} s")
    print("----------------------------------------------")
    print(f"Fitness Score:            {report['fitness_score']:.2f}")
    if footer:
        print(f"---------------- {footer} ----------------")
    print("==============================================\n")


def display_signal_plan(signal_plan: List[SignalPhase]):
    """
    Display a readable summary of the signal light configuration for each phase.

    Args:
        signal_plan: List of SignalPhase objects containing phase timings and movements.
    """
    print("\n=============== SIGNAL LIGHT CONFIGURATION ===============")
    for idx, phase in enumerate(signal_plan, start=1):
        print(f"\nPhase {idx}:")
        print(f"  Green:    {phase.green:.1f} s")
        print(f"  Amber:    {phase.amber:.1f} s")
        print(f"  All Red:  {phase.all_red:.1f} s")
        print(f"  Start:    {phase.start:.1f} s")
        print(f"  Duration: {phase.duration:.1f} s")
        print("  Movements:")

        for mv in phase.movements:
            print(f"    From '{mv.from_approach.name}' lane {mv.lane_index} "
                  f"to '{mv.to_approach.name}' | Type: {mv.movement_type} "
                  f"| Avg Flow: {mv.average_flow} veh/h "
                  f"| Saturation/Lane: {getattr(mv.from_approach, 'saturation_flow_per_lane', 'N/A')}")
    print("==========================================================\n")
