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

# This script runs SUMO simulations for a given intersection.
# The intersection files contain the modelling details, lane configurations,
# phase designs, and vehicle flow data. This script focuses on building
# the network, running simulations, and storing results for analysis,
# discussion, and reporting.

# --- TC2 - PSU TINIGUIBAN
from intersections.TC2 import min_flow_intersection, avg_flow_intersection, max_flow_intersection
from intersections.TC2 import min_signal_plan, avg_signal_plan, max_signal_plan
from preset_signal_plans import TC2_min_signal_plan as original_min_signal_plan
from preset_signal_plans import TC2_avg_signal_plan as original_avg_signal_plan
from preset_signal_plans import TC2_max_signal_plan as original_max_signal_plan

# --- TC9 - VALENCIA-RIZAL AVE
# from intersections.TC9 import min_flow_intersection, avg_flow_intersection, max_flow_intersection
# from intersections.TC9 import min_signal_plan, avg_signal_plan, max_signal_plan
# from preset_signal_plans import TC9_min_signal_plan as original_min_signal_plan
# from preset_signal_plans import TC9_avg_signal_plan as original_avg_signal_plan
# from preset_signal_plans import TC9_max_signal_plan as original_max_signal_plan

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

INTERSECTION_FOLDER = avg_flow_intersection.name
BASE_NETWORK_PATH = BASE_SUMO_PATH / INTERSECTION_FOLDER
ORIGINAL_BASELINE_PATH = BASE_NETWORK_PATH / "original/"
PSO_PATH = BASE_NETWORK_PATH / "pso/"
WEBSTERS_PATH = BASE_NETWORK_PATH / "websters_baseline/"
GA_ENHANCED_PATH = BASE_NETWORK_PATH / "ga_enhanced/"


def run_sumo_scenario(
    label: str,
    intersection,
    signal_plan,
    routes_path: Path,
    net_path: Path,
    base_path: Path,
    gui_settings_path: Path,
    signal_plan_name: str,
    use_temp: bool = False,
    skip_tls_generation: bool = False,
    display: bool = True,
):
    """
    Runs a SUMO simulation and generates a report for a given signal plan.

    Parameters
    ----------
    intersection : Intersection object
        Intersection data for simulation.
    signal_plan : SignalPlan
        Signal plan to simulate.
    routes_path : Path
        Routes XML file.
    net_path : Path
        Network XML file.
    base_path : Path
        Folder to save SUMO files and report.
        Ignored if use_temp=True.
    gui_settings_path : Path
        GUI settings XML path.
    signal_plan_name : str
        Name of the signal plan (for CSV/report labeling).
    use_temp : bool
        If True, runs everything in a TemporaryDirectory and cleans up after.
    skip_tls_generation : bool
        If True, assumes TLS XML is already present and does not generate it.
        Useful for PSO signal plans.
    display : bool
        If True, prints the report to console.
    Returns
    -------
    dict
        The simulation report.
    """
    if use_temp:
        tmp_dir = tempfile.TemporaryDirectory()
        base_path = Path(tmp_dir.name)

    base_path.mkdir(parents=True, exist_ok=True)

    sumo_cfg_path = base_path / "simulation.sumocfg"
    tls_path = base_path / "traffic_light_signal.tls.xml"
    tripinfo_path = base_path / "tripinfo.xml"
    detector_path = base_path / "detectors.xml"
    report_path = base_path / "report.json"

    # Generate TLS XML if not skipped
    if not skip_tls_generation:
        generate_traffic_lights_xml(
            signal_plan=signal_plan, net_path=net_path, output_path=tls_path
        )

    # Generate SUMO config
    create_sumo_config(
        routes_path=routes_path,
        net_path=net_path,
        tls_path=tls_path,
        output_path=sumo_cfg_path,
        gui_settings_path=gui_settings_path
    )

    # Run SUMO
    run_sumo(
        net_file=str(net_path),
        sumocfg_path=str(sumo_cfg_path),
        tripinfo_out=str(tripinfo_path),
        detector_out=str(detector_path),
        tls_path=str(tls_path)
    )

    # Generate report
    report = generate_report(
        intersection=intersection,
        tripinfo_path=str(tripinfo_path),
        detector_path=str(detector_path),
        base_dir=base_path,
        save_json=str(report_path)
    )

    # Optionally display the report
    if display:
        display_report(report, header=signal_plan_name)

    if not use_temp:
        # Record in CSVs
        add_report_to_comparative_analysis_csv(
            report=report,
            signal_plan_name=signal_plan_name,
            num_phase=len(signal_plan),
            signal_plan=signal_plan,
            intersection=intersection,
            label=label
        )
        add_signal_plan_to_signal_plans_csv(
            intersection=intersection,
            signal_plan_name=signal_plan_name,
            num_phase=len(signal_plan),
            signal_plan=signal_plan,
            label=label
        )

    if use_temp:
        tmp_dir.cleanup()

    return report


if __name__ == "__main__":
    scenarios = [
        ("MIN FLOW", min_flow_intersection),
        ("AVG FLOW", avg_flow_intersection),
        ("MAX FLOW", max_flow_intersection),
    ]

    base_signal_plans = {
        "MIN FLOW": min_signal_plan,
        "AVG FLOW": avg_signal_plan,
        "MAX FLOW": max_signal_plan,
    }

    original_signal_plans = {
        "MIN FLOW": original_min_signal_plan,
        "AVG FLOW": original_avg_signal_plan,
        "MAX FLOW": original_max_signal_plan,
    }

    for label, intersection_obj in scenarios:

        print(f"\n===== RUNNING {label} SCENARIO =====\n")

        scenario_folder = BASE_NETWORK_PATH / label.replace(" ", "_")
        scenario_folder.mkdir(parents=True, exist_ok=True)

        ORIGINAL_BASELINE_PATH = scenario_folder / "original/"
        PSO_PATH = scenario_folder / "pso/"
        WEBSTERS_PATH = scenario_folder / "websters_baseline/"
        GA_ENHANCED_PATH = scenario_folder / "ga_enhanced/"

        for path in [ORIGINAL_BASELINE_PATH, WEBSTERS_PATH, GA_ENHANCED_PATH, PSO_PATH]:
            path.mkdir(parents=True, exist_ok=True)

        base_signal_plan = base_signal_plans[label]
        original_signal_plan = original_signal_plans[label]
        NUMBER_OF_PHASE = len(base_signal_plan)
        
        # pprint(original_signal_plan)

        # CSVs for this scenario
        create_comparative_analysis_csv(
            intersection=intersection_obj, num_phase=NUMBER_OF_PHASE, label=label
        )
        create_signal_plans_csv(
            intersection=intersection_obj, num_phase=NUMBER_OF_PHASE, label=label
        )

        # --- BUILD NETWORK ---
        base_nodes_path = scenario_folder / "nodes.xml"
        base_edges_path = scenario_folder / "edges.xml"
        base_connections_path = scenario_folder / "connections.xml"
        base_routes_path = scenario_folder / "routes.xml"
        base_net_path = scenario_folder / "network.net.xml"
        base_gui_settings_path = scenario_folder / "viewsettings.xml"

        generate_nodes_xml(intersection_obj, base_nodes_path)
        generate_edges_xml(intersection_obj, base_edges_path)
        generate_connections_xml(intersection_obj, base_connections_path)
        generate_routes_xml(intersection_obj, base_routes_path)

        generate_viewsettings_xml(output_path=base_gui_settings_path)

        subprocess.run([
            "netconvert",
            "--node-files", str(base_nodes_path),
            "--edge-files", str(base_edges_path),
            "--connection-files", str(base_connections_path),
            "--output-file", str(base_net_path)
        ], check=True)

        # --- ORIGINAL PLAN ---
        run_sumo_scenario(
            label=label,
            intersection=intersection_obj,
            signal_plan=original_signal_plan,
            routes_path=base_routes_path,
            net_path=base_net_path,
            base_path=ORIGINAL_BASELINE_PATH,
            gui_settings_path=base_gui_settings_path,
            signal_plan_name=f"{label} - ORIGINAL CONFIG"
        )

        # --- PSO ---
        pso_tls_path = PSO_PATH / "traffic_light_signal.tls.xml"
        pso_signal_plan = parse_signal_plan(
            template_plan=copy.deepcopy(base_signal_plan),
            tls_path=pso_tls_path
        )

        run_sumo_scenario(
            label=label,
            intersection=intersection_obj,
            signal_plan=pso_signal_plan,
            routes_path=base_routes_path,
            net_path=base_net_path,
            base_path=PSO_PATH,
            gui_settings_path=base_gui_settings_path,
            signal_plan_name=f"{label} - PSO",
            skip_tls_generation=True
        )

        # --- GA INITIAL POPULATION ---
        population = generate_population(20, copy.deepcopy(base_signal_plan))
        best_fitness = float("inf")
        best_signal_plan = None

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            for idx, plan in enumerate(population):
                report = run_sumo_scenario(
                    label=label,
                    intersection=intersection_obj,
                    signal_plan=plan,
                    routes_path=base_routes_path,
                    net_path=base_net_path,
                    base_path=tmp_path,
                    gui_settings_path=base_gui_settings_path,
                    signal_plan_name=f"{label} - Population {idx+1}",
                    use_temp=True,
                    skip_tls_generation=False,
                    display=False
                )

                if report["fitness_score"] < best_fitness:
                    best_fitness = report["fitness_score"]
                    best_signal_plan = copy.deepcopy(plan)

        # --- WEBSTER BASELINE ---
        webster_signal_plan = best_signal_plan
        run_sumo_scenario(
            label=label,
            intersection=intersection_obj,
            signal_plan=webster_signal_plan,
            routes_path=base_routes_path,
            net_path=base_net_path,
            base_path=WEBSTERS_PATH,
            gui_settings_path=base_gui_settings_path,
            signal_plan_name=f"{label} - WEBSTER BASELINE"
        )

        # --- GA ENHANCED ---
        final_population, generation = run_evolution(
            intersection=intersection_obj,
            signal_plan_template=copy.deepcopy(base_signal_plan),
            population=population,
            routes_path=base_routes_path,
            net_path=base_net_path,
        )
        ga_enhanced_signal_plan = final_population[0]

        run_sumo_scenario(
            label=label,
            intersection=intersection_obj,
            signal_plan=ga_enhanced_signal_plan,
            routes_path=base_routes_path,
            net_path=base_net_path,
            base_path=GA_ENHANCED_PATH,
            gui_settings_path=base_gui_settings_path,
            signal_plan_name=f"{label} - GA ENHANCED"
        )
