def print_phase_flow_ratios(signal_plan, sat_per_lane: float = 1850):
    """
    Aggregate all flows and lanes in a phase before computing flow ratio.
    Y_phase = sum(q_all_movements) / sum(s_all_lanes)
    """
    print("\n=============================================")
    print("  TOTAL AGGREGATED FLOW RATIOS PER PHASE")
    print("=============================================\n")

    for phase_idx, phase in enumerate(signal_plan, start=1):
        print(f"\n--- PHASE {phase_idx} ---\n")

        total_flow = 0.0
        total_lanes = 0

        # Collect flows and lane counts for unique from_approach
        approaches_seen = set()
        for mv in phase.movements:
            total_flow += mv.expected_flow
            if mv.from_approach.name not in approaches_seen:
                total_lanes += mv.from_approach.num_lanes
                approaches_seen.add(mv.from_approach.name)

        total_saturation = total_lanes * sat_per_lane
        Y_phase = total_flow / total_saturation if total_saturation > 0 else 0

        print(f"Total flow sum(q) for phase: {total_flow:.1f} veh/h")
        print(f"Total saturation sum(s) for phase: {total_saturation:.1f} veh/h ({total_lanes} lanes)")
        print(f"Phase critical flow ratio Y_phase = {Y_phase:.4f}")
        print("-" * 60)
