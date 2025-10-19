from pathlib import Path

# Base network folder (nodes.xml, edges.xml, connections.xml)
BASE_NETWORK_PATH = Path("sumo/base")

# Saturation flow simulations folder (each movement gets its own subfolder)
SATURATION_ROOT_PATH = Path("sumo/saturation")

# Path where cached saturation flows are stored
SATURATION_CACHE_FILE = Path("data/saturation/saturation_flows.json")
