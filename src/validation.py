import subprocess
import tempfile
from pathlib import Path
from constants import BASE_SUMO_PATH
from sumo_report import compute_expected_arrivals, run_sumo, generate_report
# from intersections.TC2 import intersection_hourly, avg_flow_intersection
from intersections.TC9 import intersection_hourly, avg_flow_intersection
from sumo_functions import (
    generate_routes_xml,
    generate_viewsettings_xml,
    create_sumo_config
)
from record_data import create_scalability_assessment_csv, add_scalability_assessment_row

# --- Configuration ---
traffic_volumes = [
    "MIN_FLOW",
    "AVG_FLOW",
    "MAX_FLOW",
]
tls_types = ["original", "websters_baseline", "ga_enhanced", "pso"]

INTERSECTION_FOLDER = avg_flow_intersection.name
BASE_NETWORK_PATH = BASE_SUMO_PATH / INTERSECTION_FOLDER

if __name__ == "__main__":
    print("Starting scalability validation...\n")

    # --- Sort intersections by expected arrivals ---
    inter_with_flow = [(inter, compute_expected_arrivals(inter))
                       for inter in intersection_hourly]
    inter_with_flow.sort(key=lambda x: x[1])
    intersection_hourly_sorted = [inter for inter, _ in inter_with_flow]

    # --- Loop through traffic volumes ---
    for volume in traffic_volumes:
        print(f"\n=== Processing traffic volume: {volume} ===")
        volume_folder = BASE_NETWORK_PATH / volume
        gui_settings_path = volume_folder / "viewsettings.xml"

        # TLS XML paths per volume
        tls_paths = {
            tls_name: volume_folder / tls_name / "traffic_light_signal.tls.xml"
            for tls_name in tls_types
        }

        # --- Prepare scalability CSVs ---
        for tls_name in tls_types:
            create_scalability_assessment_csv(
                # replace underscores with spaces
                label=volume.replace("_", " "),
                intersection=avg_flow_intersection,
                signal_plan_name=tls_name
            )

        for idx, inter in enumerate(intersection_hourly_sorted):
            print(f"Running hourly scenario {idx + 1}")
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)

                # --- Network and routes ---
                nodes_path = BASE_NETWORK_PATH / volume / "nodes.xml"
                edges_path = BASE_NETWORK_PATH / volume / "edges.xml"
                connections_path = BASE_NETWORK_PATH / volume / "connections.xml"
                net_path = tmp_path / "network.net.xml"
                routes_path = tmp_path / "routes.xml"

                generate_routes_xml(inter, routes_path)

                # --- Netconvert ---
                subprocess.run([
                    "netconvert",
                    "--node-files", str(nodes_path),
                    "--edge-files", str(edges_path),
                    "--connection-files", str(connections_path),
                    "--output-file", str(net_path)
                ], check=True)

                # --- TLS scenario folders inside temp ---
                tls_tmp_folders = {name: tmp_path / name for name in tls_types}
                for folder in tls_tmp_folders.values():
                    folder.mkdir()

                # --- SUMO config paths ---
                sumo_cfg_paths = {name: folder / "simulation.sumocfg"
                                  for name, folder in tls_tmp_folders.items()}

                # --- Create SUMO configs ---
                for tls_name in tls_types:
                    create_sumo_config(
                        routes_path=routes_path,
                        net_path=net_path,
                        gui_settings_path=gui_settings_path,
                        output_path=sumo_cfg_paths[tls_name],
                        tls_path=tls_paths[tls_name]
                    )

                # --- Run SUMO and generate reports ---
                for tls_name in tls_types:
                    base_dir = tls_tmp_folders[tls_name]
                    sumo_cfg = sumo_cfg_paths[tls_name]
                    tls_file = tls_paths[tls_name]

                    tripinfo_path = base_dir / "tripinfo.xml"
                    detector_path = base_dir / "detectors.xml"
                    report_path = base_dir / "report.json"

                    run_sumo(
                        net_file=str(net_path),
                        sumocfg_path=str(sumo_cfg),
                        tripinfo_out=str(tripinfo_path),
                        detector_out=str(detector_path),
                        tls_path=str(tls_file)
                    )

                    report = generate_report(
                        intersection=inter,
                        tripinfo_path=str(tripinfo_path),
                        detector_path=str(detector_path),
                        base_dir=base_dir,
                        save_json=str(report_path)
                    )

                    total_flow = compute_expected_arrivals(inter)
                    total_queue = report["total_queue_length"]
                    avg_queue = report["avg_queue_length"]

                    add_scalability_assessment_row(
                        label=volume.replace("_", " "),
                        intersection=avg_flow_intersection,
                        signal_plan_name=tls_name,
                        scenario=f"{volume}_scenario_{idx + 1}",
                        total_flow=total_flow,
                        total_queue_length=total_queue,
                        avg_queue_length=avg_queue
                    )

            print(f"Completed scenario {idx + 1} for volume {volume}.\n")

    print("All hourly scenarios validated successfully. Please check CSV files.")
