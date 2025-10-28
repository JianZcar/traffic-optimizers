T_INTERSECTION = {
    "name": "T-Intersection",
    "type": "T",
    "approaches": [
        {"name": "1_in", "x": 0.0, "y": 250, "edge_id": "1_in", "num_lanes": 2},
        {"name": "1_out", "x": 0.0, "y": 250, "edge_id": "1_out", "num_lanes": 2},
        {"name": "3_in", "x": 0.0, "y": -250, "edge_id": "3_in", "num_lanes": 2},
        {"name": "3_out", "x": 0.0, "y": -250, "edge_id": "3_out", "num_lanes": 2},
        {"name": "4_in", "x": -250, "y": 0.0, "edge_id": "4_in", "num_lanes": 2},
        {"name": "4_out", "x": -250, "y": 0.0, "edge_id": "4_out", "num_lanes": 2},
    ],
    "movements": [
        {"from_edge": "1_in", "to_edge": "3_out",
            "movement_type": "straight", "average_flow": 500, "num_lanes": 1},
        {"from_edge": "1_in", "to_edge": "4_out",
            "movement_type": "right", "average_flow": 400, "num_lanes": 1},
        {"from_edge": "3_in", "to_edge": "1_out",
            "movement_type": "straight", "average_flow": 600, "num_lanes": 1},
        {"from_edge": "3_in", "to_edge": "4_out",
            "movement_type": "left", "average_flow": 350, "num_lanes": 1},
        {"from_edge": "4_in", "to_edge": "3_out",
            "movement_type": "right", "average_flow": 450, "num_lanes": 1},
        {"from_edge": "4_in", "to_edge": "1_out",
            "movement_type": "left", "average_flow": 300, "num_lanes": 1},
    ]
}


X_INTERSECTION = {
    "name": "X-Intersection",
    "type": "X",
    "approaches": [
        {"name": "N_in", "x": 0.0, "y": 100, "edge_id": "N_in", "num_lanes": 2},
        {"name": "N_out", "x": 0.0, "y": 100, "edge_id": "N_out", "num_lanes": 2},
        {"name": "S_in", "x": 0.0, "y": -100, "edge_id": "S_in", "num_lanes": 2},
        {"name": "S_out", "x": 0.0, "y": -100, "edge_id": "S_out", "num_lanes": 2},
        {"name": "E_in", "x": 100, "y": 0.0, "edge_id": "E_in", "num_lanes": 2},
        {"name": "E_out", "x": 100, "y": 0.0, "edge_id": "E_out", "num_lanes": 2},
        {"name": "W_in", "x": -100, "y": 0.0, "edge_id": "W_in", "num_lanes": 2},
        {"name": "W_out", "x": -100, "y": 0.0, "edge_id": "W_out", "num_lanes": 2},
    ],
    "movements": [
        {"from_edge": "N_in", "to_edge": "S_out",
            "movement_type": "straight", "average_flow": 600, "num_lanes": 1},
        {"from_edge": "N_in", "to_edge": "E_out",
            "movement_type": "right", "average_flow": 400, "num_lanes": 1},
        {"from_edge": "N_in", "to_edge": "W_out",
            "movement_type": "left", "average_flow": 300, "num_lanes": 1},

        {"from_edge": "S_in", "to_edge": "N_out",
            "movement_type": "straight", "average_flow": 600, "num_lanes": 1},
        {"from_edge": "S_in", "to_edge": "W_out",
            "movement_type": "right", "average_flow": 400, "num_lanes": 1},
        {"from_edge": "S_in", "to_edge": "E_out",
            "movement_type": "left", "average_flow": 300, "num_lanes": 1},

        {"from_edge": "E_in", "to_edge": "W_out",
            "movement_type": "straight", "average_flow": 500, "num_lanes": 1},
        {"from_edge": "E_in", "to_edge": "N_out",
            "movement_type": "right", "average_flow": 350, "num_lanes": 1},
        {"from_edge": "E_in", "to_edge": "S_out",
            "movement_type": "left", "average_flow": 300, "num_lanes": 1},

        {"from_edge": "W_in", "to_edge": "E_out",
            "movement_type": "straight", "average_flow": 500, "num_lanes": 1},
        {"from_edge": "W_in", "to_edge": "S_out",
            "movement_type": "right", "average_flow": 350, "num_lanes": 1},
        {"from_edge": "W_in", "to_edge": "N_out",
            "movement_type": "left", "average_flow": 300, "num_lanes": 1},
    ]
}
