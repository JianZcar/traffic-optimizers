import subprocess
import copy
import tempfile
from pprint import pprint
from pathlib import Path
from custom_typings import SignalPlan
from record_data import (create_comparative_analysis_csv,
                         create_signal_plans_csv,
                         add_report_to_comparative_analysis_csv,
                         add_signal_plan_to_signal_plans_csv)

# --- TC2
from intersections.TC2 import intersection
from intersections.TC2 import signal_plan as base_signal_plan
from preset_signal_plans import TC2_signal_plan as original_signal_plan
# --- TC9
# from intersections.TC9 import intersection
# from intersections.TC9 import signal_plan as base_signal_plan
# from preset_signal_plans import TC9_signal_plan as original_signal_plan

from constants import DOCUMENTATION_DOCX_PATH, BASE_SUMO_PATH
from sumo_functions import (generate_connections_xml,
                            generate_edges_xml,
                            generate_routes_xml,
                            generate_nodes_xml,
                            generate_traffic_lights_xml,
                            create_sumo_config,
                            generate_viewsettings_xml,
                            parse_signal_plan)
from sumo_report import display_report, generate_report, run_sumo
from algorithms.ga import generate_population, run_evolution

INTERSECTION_FOLDER = intersection.name
BASE_NETWORK_PATH = BASE_SUMO_PATH / INTERSECTION_FOLDER
ORIGINAL_BASELINE_PATH = BASE_NETWORK_PATH / "original/"
PSO_PATH = BASE_NETWORK_PATH / "pso/"
WEBSTERS_PATH = BASE_NETWORK_PATH / "websters_baseline/"
GA_ENHANCED_PATH = BASE_NETWORK_PATH / "ga_enhanced/"
NUMBER_OF_PHASE = len(base_signal_plan)

if __name__ == "__main__":
    for path in [DOCUMENTATION_DOCX_PATH, BASE_NETWORK_PATH, ORIGINAL_BASELINE_PATH, WEBSTERS_PATH, GA_ENHANCED_PATH]:
        path.mkdir(parents=True, exist_ok=True)

    create_comparative_analysis_csv(
        intersection=intersection, num_phase=NUMBER_OF_PHASE)
    create_signal_plans_csv(intersection=intersection,
                            num_phase=NUMBER_OF_PHASE)

    # --- BUILDING THE INTERSECTION IN SUMO ---
    base_nodes_path = BASE_NETWORK_PATH / "nodes.xml"
    base_edges_path = BASE_NETWORK_PATH / "edges.xml"
    base_connections_path = BASE_NETWORK_PATH / "connections.xml"
    base_routes_path = BASE_NETWORK_PATH / "routes.xml"
    base_net_path = BASE_NETWORK_PATH / "network.net.xml"
    base_gui_settings_path = BASE_NETWORK_PATH / "viewsettings.xml"

    generate_nodes_xml(intersection, base_nodes_path)
    generate_edges_xml(intersection, base_edges_path)
    generate_connections_xml(intersection, base_connections_path)
    generate_routes_xml(intersection, base_routes_path)

    # --- GUI SETTINGS ---
    generate_viewsettings_xml(output_path=base_gui_settings_path)

    subprocess.run([
        "netconvert",
        "--node-files", str(base_nodes_path),
        "--edge-files", str(base_edges_path),
        "--connection-files", str(base_connections_path),
        "--output-file", str(base_net_path)
    ], check=True)

    # --- SUMO BUILT-IN TRAFFIC LIGHTS ---
    # base_sumo_config_path = BASE_NETWORK_PATH / "simulation.sumocfg"
    # base_tripinfo_path = BASE_NETWORK_PATH / "tripinfo.xml"
    # base_detector_path = BASE_NETWORK_PATH / "detectors.xml"
    # base_report_path = BASE_NETWORK_PATH / "report.json"

    # create_sumo_config(
    #     routes_path=base_routes_path,
    #     net_path=base_net_path,
    #     output_path=base_sumo_config_path,
    #     gui_settings_path=base_gui_settings_path
    # )

    # run_sumo(
    #     net_file=str(base_net_path),
    #     sumocfg_path=str(base_sumo_config_path),
    #     tripinfo_out=str(base_tripinfo_path),
    #     detector_out=str(base_detector_path),
    # )

    # base_report = generate_report(
    #     intersection=intersection,
    #     tripinfo_path=str(base_tripinfo_path),
    #     detector_path=str(base_detector_path),
    #     base_dir=BASE_NETWORK_PATH,
    #     save_json=str(base_report_path)
    # )

    # display_report(base_report, header="SUMO BUILT-IN")
    # add_report_to_comparative_analysis_csv(
    #     report=base_report, signal_plan_name="SUMO BUILT-IN", num_phase=NUMBER_OF_PHASE, intersection=intersection)
    # add_signal_plan_to_signal_plans_csv(
    #     intersection=intersection, signal_plan_name="SUMO BUILT-IN", num_phase=NUMBER_OF_PHASE)

    # SIMULATE ORIGINAL SETUP AND GENERATE REPORT
    original_sumo_config_path = ORIGINAL_BASELINE_PATH / "simulation.sumocfg"
    original_tls_path = ORIGINAL_BASELINE_PATH / "traffic_light_signal.tls.xml"

    generate_traffic_lights_xml(signal_plan=original_signal_plan,
                                net_path=base_net_path,
                                output_path=original_tls_path)

    create_sumo_config(
        routes_path=base_routes_path,
        net_path=base_net_path,
        tls_path=original_tls_path,
        output_path=original_sumo_config_path,
        gui_settings_path=base_gui_settings_path
    )

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
        intersection=intersection,
        tripinfo_path=str(original_tripinfo_path),
        detector_path=str(original_detector_path),
        base_dir=ORIGINAL_BASELINE_PATH,
        save_json=str(original_report_path)
    )

    display_report(original_report, header="ORIGINAL CONFIG")
    add_report_to_comparative_analysis_csv(
        report=original_report, signal_plan_name="ORIGINAL CONFIG", num_phase=NUMBER_OF_PHASE, signal_plan=original_signal_plan, intersection=intersection)
    add_signal_plan_to_signal_plans_csv(
        intersection=intersection, signal_plan_name="ORIGINAL CONFIG", num_phase=NUMBER_OF_PHASE, signal_plan=original_signal_plan)

    # PSO GENERATED TRAFFIC LIGHT SIGNAL TIMINGS
    pso_sumo_config_path = PSO_PATH / "simulation.sumocfg"
    pso_tls_path = PSO_PATH / "traffic_light_signal.tls.xml"
    assert pso_tls_path.exists(), f"TLS file not found: {pso_tls_path}"
    print(pso_tls_path.read_text())
    pso_signal_plan = parse_signal_plan(
        template_plan=copy.deepcopy(base_signal_plan), tls_path=pso_tls_path)

    create_sumo_config(
        routes_path=base_routes_path,
        net_path=base_net_path,
        tls_path=pso_tls_path,
        output_path=pso_sumo_config_path,
        gui_settings_path=base_gui_settings_path
    )

    pso_tripinfo_path = PSO_PATH / "tripinfo.xml"
    pso_detector_path = PSO_PATH / "detectors.xml"
    pso_report_path = PSO_PATH / "report.json"

    run_sumo(
        net_file=str(base_net_path),
        sumocfg_path=str(pso_sumo_config_path),
        tripinfo_out=str(pso_tripinfo_path),
        detector_out=str(pso_detector_path),
        tls_path=str(pso_tls_path)
    )

    pso_report = generate_report(
        intersection=intersection,
        tripinfo_path=str(pso_tripinfo_path),
        detector_path=str(pso_detector_path),
        base_dir=PSO_PATH,
        save_json=str(pso_report_path)
    )

    display_report(pso_report, header="PSO")
    add_report_to_comparative_analysis_csv(
        report=pso_report, signal_plan_name="PSO", num_phase=NUMBER_OF_PHASE, signal_plan=pso_signal_plan, intersection=intersection)
    add_signal_plan_to_signal_plans_csv(
        intersection=intersection, signal_plan_name="PSO", num_phase=NUMBER_OF_PHASE, signal_plan=pso_signal_plan)

    # TODO: GENERATE INITIAL POPULATIONS FOR GENETIC ALGORITHM BASED USING MODIFIED WEBSTER'S METHOD
    population = generate_population(20, copy.deepcopy(base_signal_plan))

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

        for idx, plan in enumerate(population):
            # Generate TLS and SUMO config in temp folder
            generate_traffic_lights_xml(signal_plan=plan,
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
                intersection=intersection,
                tripinfo_path=str(tmp_tripinfo),
                detector_path=str(tmp_detector),
                base_dir=tmp_path,
                save_json=str(tmp_report)
            )

            # Track best fitness
            if report["fitness_score"] < best_fitness:
                best_fitness = report["fitness_score"]
                best_signal_plan = copy.deepcopy(plan)

    webster_signal_plan = best_signal_plan
    generate_traffic_lights_xml(
        signal_plan=best_signal_plan,
        net_path=base_net_path,
        output_path=websters_tls_path
    )

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
        intersection=intersection,
        tripinfo_path=websters_tripinfo_path,
        detector_path=websters_detector_path,
        base_dir=WEBSTERS_PATH,
        save_json=websters_report_path
    )

    display_report(websters_report, header="WEBSTER BASELINE")
    add_report_to_comparative_analysis_csv(report=websters_report, signal_plan_name="WEBSTER BASELINE",
                                           num_phase=NUMBER_OF_PHASE, intersection=intersection, signal_plan=webster_signal_plan)
    add_signal_plan_to_signal_plans_csv(intersection=intersection, signal_plan_name="WEBSTER BASELINE",
                                        num_phase=NUMBER_OF_PHASE, signal_plan=webster_signal_plan)

    # TODO: RUN GENETIC ALGORITHM TO OPTIMIZE THE TRAFFIC LIGHT TIMINGS
    final_population, generation = run_evolution(
        intersection=intersection,
        signal_plan_template=copy.deepcopy(base_signal_plan),
        population=population,
        routes_path=base_routes_path,
        net_path=base_net_path,
    )

    ga_enhanced_signal_plan = final_population[0]
    ga_enhanced_sumo_config_path = GA_ENHANCED_PATH / "simulation.sumocfg"
    ga_enhanced_tls_path = GA_ENHANCED_PATH / "traffic_light_signal.tls.xml"
    ga_enhanced_tripinfo_path = GA_ENHANCED_PATH / "tripinfo.xml"
    ga_enhanced_detector_path = GA_ENHANCED_PATH / "detectors.xml"
    ga_enhaced_report_path = GA_ENHANCED_PATH / "report.json"

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
        intersection=intersection,
        tripinfo_path=ga_enhanced_tripinfo_path,
        detector_path=ga_enhanced_detector_path,
        base_dir=GA_ENHANCED_PATH,
        save_json=ga_enhaced_report_path
    )

    display_report(ga_enhnaced_report, header="GA ENHANCED")
    add_report_to_comparative_analysis_csv(report=ga_enhnaced_report, signal_plan_name="GA ENHANCED",
                                           num_phase=NUMBER_OF_PHASE, intersection=intersection, signal_plan=ga_enhanced_signal_plan)
    add_signal_plan_to_signal_plans_csv(intersection=intersection, signal_plan_name="GA ENHANCED",
                                        num_phase=NUMBER_OF_PHASE, signal_plan=ga_enhanced_signal_plan)
