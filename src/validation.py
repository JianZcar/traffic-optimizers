import subprocess
from pathlib import Path
from constants import BASE_SUMO_PATH
from sumo_report import compute_expected_arrivals, run_sumo, generate_report
from intersections.TC2 import intersection_hourly, intersection
from sumo_functions import (
    generate_routes_xml,
    generate_viewsettings_xml,
    create_sumo_config
)
from record_data import create_scalability_assessment_csv, add_scalability_assessment_row


INTERSECTION_FOLDER = intersection.name
VALIDATION_NETWORK_PATH = BASE_SUMO_PATH / f"{INTERSECTION_FOLDER}_validation"
BASE_NETWORK_PATH = BASE_SUMO_PATH / INTERSECTION_FOLDER

ORIGINAL_BASELINE_PATH = BASE_NETWORK_PATH / "original/"
WEBSTERS_PATH = BASE_NETWORK_PATH / "websters_baseline/"
GA_ENHANCED_PATH = BASE_NETWORK_PATH / "ga_enhanced/"
PSO_PATH = BASE_NETWORK_PATH / "pso/"

if __name__ == "__main__":
    # Compute expected vehicles and sort intersections by total flow (lowest first)
    inter_with_flow = [(inter, compute_expected_arrivals(inter))
                       for inter in intersection_hourly]
    inter_with_flow.sort(key=lambda x: x[1])
    intersection_hourly_sorted = [inter for inter, _ in inter_with_flow]

    # Generate GUI settings once (same for all scenarios)
    gui_settings_path = BASE_NETWORK_PATH / "viewsettings.xml"
    generate_viewsettings_xml(output_path=gui_settings_path)

    # --- Prepare scalability CSVs once per TLS type ---
    for tls_name in ["original", "websters_baseline", "ga_enhanced", "pso"]:
        create_scalability_assessment_csv(intersection, tls_name)

    # --- Loop over each hourly intersection scenario ---
    for idx, inter in enumerate(intersection_hourly_sorted):
        scenario_folder = VALIDATION_NETWORK_PATH / f"scenario_{idx + 1}"
        scenario_folder.mkdir(parents=True, exist_ok=True)

        # Paths for network
        nodes_path = BASE_NETWORK_PATH / "nodes.xml"
        edges_path = BASE_NETWORK_PATH / "edges.xml"
        connections_path = BASE_NETWORK_PATH / "connections.xml"
        net_path = scenario_folder / "network.net.xml"
        routes_path = scenario_folder / "routes.xml"

        # TLS subfolders
        tls_original_folder = scenario_folder / "original"
        tls_websters_folder = scenario_folder / "websters_baseline"
        tls_ga_folder = scenario_folder / "ga_enhanced"
        tls_pso_folder = scenario_folder / "pso"
        tls_original_folder.mkdir(parents=True, exist_ok=True)
        tls_websters_folder.mkdir(parents=True, exist_ok=True)
        tls_ga_folder.mkdir(parents=True, exist_ok=True)
        tls_pso_folder.mkdir(parents=True, exist_ok=True)

        # TLS files from base intersection
        tls_original_path = ORIGINAL_BASELINE_PATH / "traffic_light_signal.tls.xml"
        tls_websters_path = WEBSTERS_PATH / "traffic_light_signal.tls.xml"
        tls_ga_path = GA_ENHANCED_PATH / "traffic_light_signal.tls.xml"
        tls_pso_path = PSO_PATH / "traffic_light_signal.tls.xml"

        # SUMO config paths
        sumo_cfg_original = tls_original_folder / "simulation.sumocfg"
        sumo_cfg_websters = tls_websters_folder / "simulation.sumocfg"
        sumo_cfg_ga = tls_ga_folder / "simulation.sumocfg"
        sumo_cfg_pso = tls_pso_folder / "simulation.sumocfg"

        # --- Routes file (depends on this intersection) ---
        generate_routes_xml(inter, routes_path)

        # --- Netconvert ---
        subprocess.run([
            "netconvert",
            "--node-files", str(nodes_path),
            "--edge-files", str(edges_path),
            "--connection-files", str(connections_path),
            "--output-file", str(net_path)
        ], check=True)

        # --- SUMO configs for each TLS scenario ---
        create_sumo_config(routes_path=routes_path, net_path=net_path,
                           gui_settings_path=gui_settings_path, output_path=sumo_cfg_original, tls_path=tls_original_path)
        create_sumo_config(routes_path=routes_path, net_path=net_path,
                           gui_settings_path=gui_settings_path, output_path=sumo_cfg_websters, tls_path=tls_websters_path)
        create_sumo_config(routes_path=routes_path, net_path=net_path,
                           gui_settings_path=gui_settings_path, output_path=sumo_cfg_ga, tls_path=tls_ga_path)
        create_sumo_config(routes_path=routes_path, net_path=net_path,
                           gui_settings_path=gui_settings_path, output_path=sumo_cfg_pso, tls_path=tls_pso_path)

        # --- Run SUMO and generate reports ---
        for sumo_cfg, tls_file, base_dir, tls_name in [
            (sumo_cfg_original, tls_original_path, tls_original_folder, "original"),
            (sumo_cfg_websters, tls_websters_path,
             tls_websters_folder, "websters_baseline"),
            (sumo_cfg_ga, tls_ga_path, tls_ga_folder, "ga_enhanced"),
            (sumo_cfg_pso, tls_pso_path, tls_pso_folder, "pso"),
        ]:
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
                intersection=intersection,
                signal_plan_name=tls_name,
                scenario=f"scenario_{idx + 1}",
                total_flow=total_flow,
                total_queue_length=total_queue,
                avg_queue_length=avg_queue
            )
