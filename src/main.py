import subprocess
import copy
import tempfile
import shutil
from pathlib import Path
from pprint import pprint
import documentation
from custom_typings import SignalPhase, SignalPlan
from intersections.T_shape import intersection as T_intersection
from intersections.T_shape import signal_plan as T_signal_plan
from constants import DOCUMENTATION_PATH, BASE_NETWORK_PATH, ORIGINAL_BASELINE_PATH, WEBSTERS_PATH, GA_ENHANCED_PATH
from sumo_functions import (generate_connections_xml,
                            generate_edges_xml,
                            generate_routes_xml,
                            generate_nodes_xml,
                            generate_traffic_lights_xml,
                            create_sumo_config,
                            generate_viewsettings_xml)
from sumo_report import display_report, generate_report, run_sumo, display_signal_plan
from algorithms.websters import compute_signal_config_with_poisson_and_websters
from algorithms.ga import generate_population, run_evolution


if __name__ == "__main__":
    for path in [DOCUMENTATION_PATH, BASE_NETWORK_PATH, ORIGINAL_BASELINE_PATH, WEBSTERS_PATH, GA_ENHANCED_PATH]:
        path.mkdir(parents=True, exist_ok=True)

    # --- PSU TINIGUIBAN CURRENT CONFIGURATION ---
    # Change the light configurations to reflect the actual configuration observed by Jovan
    T_signal_plan_copy = T_signal_plan.copy()

    phase_1: SignalPhase = T_signal_plan_copy[0]
    phase_1.green = 68.0
    phase_1.amber = 3.0
    phase_1.all_red = 3.0
    phase_1.start = 0.0
    phase_1.duration = phase_1.green + phase_1.amber + phase_1.all_red

    phase_2: SignalPhase = T_signal_plan_copy[1]
    phase_2.green = 32.0
    phase_2.amber = 3.0
    phase_2.all_red = 3.0
    phase_2.start = phase_1.duration
    phase_2.duration = phase_2.green + phase_2.amber + phase_2.all_red

    phase_3: SignalPhase = T_signal_plan_copy[2]
    phase_3.green = 28.0
    phase_3.amber = 3.0
    phase_3.all_red = 3.0
    phase_3.start = phase_2.start + phase_2.duration
    phase_3.duration = phase_3.green + phase_3.amber + phase_3.all_red

    PSU_signal_plan: SignalPlan = [phase_1, phase_2, phase_3]

    # --- BUILDING THE INTERSECTION IN SUMO ---
    base_nodes_path = BASE_NETWORK_PATH / "nodes.xml"
    base_edges_path = BASE_NETWORK_PATH / "edges.xml"
    base_connections_path = BASE_NETWORK_PATH / "connections.xml"
    base_routes_path = BASE_NETWORK_PATH / "routes.xml"
    base_net_path = BASE_NETWORK_PATH / "network.net.xml"
    base_gui_settings_path = BASE_NETWORK_PATH / "viewsettings.xml"

    generate_nodes_xml(T_intersection, base_nodes_path)
    generate_edges_xml(T_intersection, base_edges_path)
    generate_connections_xml(T_intersection, base_connections_path)
    generate_routes_xml(T_intersection, base_routes_path)

    # --- GUI SETTINGS ---
    generate_viewsettings_xml(output_path=base_gui_settings_path)

    subprocess.run([
        "netconvert",
        "--node-files", str(base_nodes_path),
        "--edge-files", str(base_edges_path),
        "--connection-files", str(base_connections_path),
        "--output-file", str(base_net_path)
    ], check=True)

    # SIMULATE ORIGINAL SETUP AND GENERATE REPORT
    original_sumo_config_path = ORIGINAL_BASELINE_PATH / "simulation.sumocfg"
    original_tls_path = ORIGINAL_BASELINE_PATH / "traffic_light_signal.tls.xml"

    generate_traffic_lights_xml(signal_plan=PSU_signal_plan,
                                net_path=base_net_path,
                                output_path=original_tls_path)

    create_sumo_config(
        routes_path=base_routes_path,
        net_path=base_net_path,
        tls_path=original_tls_path,
        output_path=original_sumo_config_path
    )

    print(f"SUMO CONFIG: {str(original_sumo_config_path)}")

    original_tripinfo_path = ORIGINAL_BASELINE_PATH / "tripinfo.xml"
    original_detector_path = ORIGINAL_BASELINE_PATH / "detectors.xml"
    original_report_path = ORIGINAL_BASELINE_PATH / "report.json"

    run_sumo(
        net_file=str(base_net_path),
        sumocfg_path=str(original_sumo_config_path),
        tripinfo_out=str(original_tripinfo_path),
        detector_out=str(original_detector_path),
        tls_path=str(original_tls_path)
    )

    original_report = generate_report(
        intersection=T_intersection,
        tripinfo_path=str(original_tripinfo_path),
        detector_path=str(original_detector_path),
        base_dir=ORIGINAL_BASELINE_PATH,
        save_json=str(original_report_path)
    )

    display_report(original_report, header="ORIGINAL SETUP (PSU)")

    # TODO: GENERATE INITIAL POPULATIONS FOR GENETIC ALGORITHM BASED USING MODIFIED WEBSTER'S METHOD
    population = generate_population(20, copy.deepcopy(T_signal_plan))

    best_fitness = 9999
    best_signal_plan: SignalPlan | None = None

    # Define the final paths to store the best individual
    websters_sumo_config_path = WEBSTERS_PATH / "simulation.sumocfg"
    websters_tls_path = WEBSTERS_PATH / "traffic_light_signal.tls.xml"
    websters_tripinfo_path = WEBSTERS_PATH / "tripinfo.xml"
    websters_detector_path = WEBSTERS_PATH / "detectors.xml"
    websters_report_path = WEBSTERS_PATH / "report.json"

    # TODO: RUN INITIAL POPULATION TO DETERMINE BEST PERFORMING BASELINE
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        tmp_sumocfg = tmp_path / "simulation.sumocfg"
        tmp_tls = tmp_path / "traffic_light_signal_tls.xml"
        tmp_tripinfo = tmp_path / "tripinfo.xml"
        tmp_detector = tmp_path / "detectors.xml"
        tmp_report = tmp_path / "report.json"

        for idx, signal_plan in enumerate(population):
            # Generate TLS and SUMO config in temp folder
            generate_traffic_lights_xml(signal_plan=signal_plan,
                                        net_path=base_net_path,
                                        output_path=tmp_tls)

            create_sumo_config(
                routes_path=base_routes_path,
                net_path=base_net_path,
                tls_path=tmp_tls,
                output_path=tmp_sumocfg,
                gui_settings_path=base_gui_settings_path
            )

            # Run SUMO
            run_sumo(
                net_file=str(base_net_path),
                sumocfg_path=str(tmp_sumocfg),
                tripinfo_out=str(tmp_tripinfo),
                detector_out=str(tmp_detector),
                tls_path=str(tmp_tls)
            )

            # Generate report
            report = generate_report(
                intersection=T_intersection,
                tripinfo_path=str(tmp_tripinfo),
                detector_path=str(tmp_detector),
                base_dir=tmp_path,
                save_json=str(tmp_report)
            )

            # Track best fitness
            if report["fitness_score"] < best_fitness:
                best_fitness = report["fitness_score"]
                best_signal_plan = copy.deepcopy(signal_plan)

    # TODO: GENERATE REPORT FOR THE BASELINE PERFORMANCE
    create_sumo_config(
        routes_path=base_routes_path,
        net_path=base_net_path,
        tls_path=websters_tls_path,
        output_path=websters_sumo_config_path,
        gui_settings_path=base_gui_settings_path
    )

    run_sumo(
        net_file=str(base_net_path),
        sumocfg_path=str(websters_sumo_config_path),
        tripinfo_out=str(websters_tripinfo_path),
        detector_out=str(websters_detector_path),
        tls_path=str(websters_tls_path)
    )

    websters_report = generate_report(
        intersection=T_intersection,
        tripinfo_path=websters_tripinfo_path,
        detector_path=websters_detector_path,
        base_dir=WEBSTERS_PATH,
        save_json=websters_report_path
    )

    display_report(websters_report, header="WEBSTER BASELINE")

    # TODO: RUN GENETIC ALGORITHM TO OPTIMIZE THE TRAFFIC LIGHT TIMINGS
    final_plans, generation = run_evolution(
        intersection=T_intersection,
        signal_plan_template=copy.deepcopy(T_signal_plan),
        population=population,
        routes_path=base_routes_path,
        net_path=base_net_path,
    )

    ga_enhanced_signal_plan = final_plans[0]
    ga_enhanced_sumo_config_path = GA_ENHANCED_PATH / "simulation.sumocfg"
    ga_enhanced_tls_path = GA_ENHANCED_PATH / "traffic_light_signal.tls.xml"
    ga_enhanced_tripinfo_path = GA_ENHANCED_PATH / "tripinfo.xml"
    ga_enhanced_detector_path = GA_ENHANCED_PATH / "detectors.xml"
    ga_enhaced_report_path = GA_ENHANCED_PATH / "report.xml"

    generate_traffic_lights_xml(signal_plan=ga_enhanced_signal_plan,
                                net_path=base_net_path, output_path=ga_enhanced_tls_path)

    # TODO: GENERATE REPORT FOR THE OPTIMIZED PERFORMANCE AFTER GA
    create_sumo_config(
        routes_path=base_routes_path,
        net_path=base_net_path,
        tls_path=ga_enhanced_tls_path,
        output_path=ga_enhanced_sumo_config_path,
        gui_settings_path=base_gui_settings_path
    )

    run_sumo(
        net_file=str(base_net_path),
        sumocfg_path=str(ga_enhanced_sumo_config_path),
        tripinfo_out=str(ga_enhanced_tripinfo_path),
        detector_out=str(ga_enhanced_detector_path),
        tls_path=str(ga_enhanced_tls_path)
    )

    ga_enhnaced_report = generate_report(
        intersection=T_intersection,
        tripinfo_path=ga_enhanced_tripinfo_path,
        detector_path=ga_enhanced_detector_path,
        base_dir=GA_ENHANCED_PATH,
        save_json=ga_enhaced_report_path
    )

    display_report(ga_enhnaced_report, header="GA-ENHANCED")

    # TODO: COMPARE THE THREE REPORTS AND SUMMARIZE RESULTS
    # TODO: ANALYZE AND VISUALIZE THE RESULTS
