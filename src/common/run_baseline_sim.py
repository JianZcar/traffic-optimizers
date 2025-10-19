from . import data_capture
from .export_data import generate_traffic_report
import subprocess


def runBaseline():
    subprocess.run(
        [
            "sumo",
            "-n", "sumo/base/network.net.xml",
            "-r", "sumo/base/routes.xml",
            "--tripinfo-output", "tripinfo.xml",
            "--verbose"
        ],
        check=True,       # raises if SUMO exits non-zero
        capture_output=True,
        text=True
    )
    # data_capture.get_average_flow()
    generate_traffic_report(
        "tripinfo.xml", "Initial_notrafficlight_bySUMO.png")
