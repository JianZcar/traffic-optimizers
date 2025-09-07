from . import data_capture
from .export_data import generate_traffic_report
import subprocess

subprocess.run(
    [
        "sumo",
        "-n", "road-configuration/net.xml",
        "-r", "road-configuration/routes.xml",
        "--tripinfo-output", "tripinfo.xml",
        "--verbose"
    ],
    check=True,       # raises if SUMO exits non-zero
    capture_output=True,
    text=True
)
data_capture.get_average_flow()
generate_traffic_report("tripinfo.xml", "Initial_notrafficlight_bySUMO.png")
