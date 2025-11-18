from intersections.TC2 import signal_plan as base_TC2_signal_plan
from intersections.TC9 import signal_plan as base_TC9_signal_plan
from custom_typings import SignalPhase, SignalPlan

# --- PSU TINIGUIBAN CURRENT CONFIGURATION ---
# Change the light configurations to reflect the actual configuration observed by Jovan
base_TC2_signal_plan_copy = base_TC2_signal_plan.copy()

phase_1: SignalPhase = base_TC2_signal_plan_copy[0]
phase_1.green = 68.0
phase_1.amber = 3.0
phase_1.all_red = 3.0
phase_1.start = 0.0
phase_1.duration = phase_1.green + phase_1.amber + phase_1.all_red

phase_2: SignalPhase = base_TC2_signal_plan_copy[1]
phase_2.green = 32.0
phase_2.amber = 3.0
phase_2.all_red = 3.0
phase_2.start = phase_1.duration
phase_2.duration = phase_2.green + phase_2.amber + phase_2.all_red

phase_3: SignalPhase = base_TC2_signal_plan_copy[2]
phase_3.green = 28.0
phase_3.amber = 3.0
phase_3.all_red = 3.0
phase_3.start = phase_2.start + phase_2.duration
phase_3.duration = phase_3.green + phase_3.amber + phase_3.all_red

TC2_signal_plan: SignalPlan = [phase_1, phase_2, phase_3]


# ---  Rizal Ave-Valencia St. CURRENT CONFIGURATION ---
# Change the light configurations to reflect the actual configuration observed by Jovan
base_TC9_signal_plan_copy = base_TC9_signal_plan.copy()

phase_1: SignalPhase = base_TC9_signal_plan_copy[0]
phase_1.green = 26.0
phase_1.amber = 3.0
phase_1.all_red = 3.0
phase_1.start = 0.0
phase_1.duration = phase_1.green + phase_1.amber + phase_1.all_red

phase_2: SignalPhase = base_TC9_signal_plan_copy[1]
phase_2.green = 18.0
phase_2.amber = 3.0
phase_2.all_red = 1.0
phase_2.start = phase_1.duration
phase_2.duration = phase_2.green + phase_2.amber + phase_2.all_red

phase_3: SignalPhase = base_TC9_signal_plan_copy[2]
phase_3.green = 58.0
phase_3.amber = 3.0
phase_3.all_red = 3.0
phase_3.start = phase_2.start + phase_2.duration
phase_3.duration = phase_3.green + phase_3.amber + phase_3.all_red

TC9_signal_plan: SignalPlan = [phase_1, phase_2, phase_3]
