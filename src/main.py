import subprocess
import os
from algorithms.ga import generate_population
from algorithms.websters import websters_method
from common.data_capture import get_average_flow, get_saturation_flow
from common.typings import IntersectionParams
from common.xml_generators import generate_tl_logic

# Main CLI

