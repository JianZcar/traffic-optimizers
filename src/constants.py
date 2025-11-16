from pathlib import Path

# Documentation folder
DOCUMENTATION_PATH = Path("documentation").resolve()

# Base network folder (nodes.xml, edges.xml, connections.xml)
BASE_NETWORK_PATH = Path("sumo/base").resolve()

# --- Additional folders for control strategies ---

# Webster’s baseline simulation folder
ORIGINAL_BASELINE_PATH = Path("sumo/original").resolve()

# Webster’s baseline simulation folder
WEBSTERS_PATH = Path("sumo/websters_baseline").resolve()

# Genetic Algorithm–enhanced (GA) control simulation folder
GA_ENHANCED_PATH = Path("sumo/ga_enhanced").resolve()


