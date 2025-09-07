from random import choices, randint, sample, uniform
from typing import List, Tuple
import copy
import pprint
import subprocess
import xml.etree.ElementTree as ET
import os
import tempfile

from src.common.typings import (
    TrafficConfiguration,
    Population,
    FitnessFunc,
    IntersectionParams
)
from src.common.xml_generators import generate_tl_logic
from src.algorithms.websters.websters import compute_signal_config_with_poisson


def generate_population(
    size: int,
    intersection_params: IntersectionParams
) -> List[List[TrafficConfiguration]]:
    population = dict()

    for idx in range(size):
        signal_config = compute_signal_config_with_poisson(
            saturation_flows=intersection_params.saturation_flows,
            lambda_rates=intersection_params.lambda_rates,
            reaction_time=intersection_params.reaction_time,
            road_widths=intersection_params.road_widths,
            vehicle_speed=intersection_params.vehicle_speed,
            deceleration_rate=intersection_params.deceleration_rate,
            vehicle_length=intersection_params.vehicle_length
        )
        population[idx + 1] = signal_config

    return population


def selection(
    population: Population,
    fitness_func: FitnessFunc
) -> Population:
    """
    Selects two individuals from the population based on fitness-proportional selection (roulette wheel).

    Each individual is assigned a selection probability proportional to its fitness score.
    Higher-fitness individuals are more likely to be selected, allowing the algorithm to favor
    better-performing configurations while maintaining diversity.

    Args:
        population (Population): A list of traffic configurations (individuals).
        fitness_func (FitnessFunc): A function that takes a traffic configuration and returns its fitness score.

    Returns:
        Population: A list containing two selected individuals from the input population.
    """
    return choices(
        population=population,
        weights=[fitness_func(traffic_configuration)
                 for traffic_configuration in population],
        k=2
    )


def _evaluate_config(traffic_configuration: TrafficConfiguration, workdir: str) -> float:
    """Run SUMO in `workdir`, parse tripinfo.xml, and compute the weighted score."""
    # write TL‐logic
    generate_tl_logic('data/connections.xml',
                      f'{workdir}/tl_logic.xml', traffic_configuration)
    xml_path = os.path.join(workdir, "tl_logic.xml")

    # run SUMO
    tripinfo_path = os.path.join(workdir, "tripinfo.xml")
    sumo_cmd = [
        "sumo",
        "-n", "data/net.xml",
        "-r", "data/routes.xml",
        "--additional-files", xml_path,
        "--tripinfo-output", tripinfo_path,
        "--verbose"
    ]
    subprocess.run(sumo_cmd, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=True)

    # parse results
    tree = ET.parse(tripinfo_path)
    root = tree.getroot()
    total_time_loss = total_waiting = 0.0
    total_stops = delayed = count = 0

    for trip in root.findall('tripinfo'):
        count += 1
        total_time_loss += float(trip.get('timeLoss', 0))
        total_waiting += float(trip.get('waitingTime', 0))
        total_stops += int(trip.get('waitingCount', 0))
        if float(trip.get('departDelay', 0)) > 0:
            delayed += 1

    if count == 0:
        return float('inf')

    # averages
    avg_time_loss = total_time_loss / count
    avg_waiting = total_waiting / count
    stops_per_trip = total_stops / count
    delayed_ratio = delayed / count

    # weighted score
    w = {'time_loss': 0.5, 'waiting': 0.4, 'stops': 0.4, 'delays': 0.05}
    score = (
        w['time_loss'] * avg_time_loss +
        w['waiting'] * avg_waiting +
        w['stops'] * stops_per_trip +
        w['delays'] * delayed_ratio
    )
    return round(score, 2)


def fitness(traffic_configuration: TrafficConfiguration) -> float:
    """Evaluate traffic config using SUMO simulation metrics."""
    # quick green‐time sanity check
    min_green = 5
    if any(phase.green < min_green for phase in traffic_configuration):
        return float('inf')

    # isolate each run in its own tempdir
    with tempfile.TemporaryDirectory() as workdir:
        try:
            return _evaluate_config(traffic_configuration, workdir)
        except Exception as e:
            print(f"Simulation failed: {e}")
            return float('inf')


def n_point_crossover(
    a: TrafficConfiguration,
    b: TrafficConfiguration,
    n: int = 1,
    min_green: int = 5
) -> Tuple[TrafficConfiguration, TrafficConfiguration]:
    """
    Performs n-point crossover between two parent configurations.

    Args:
        a: First parent configuration
        b: Second parent configuration
        n: Number of crossover points (default: 1)
        min_green: Minimum green time enforcement

    Returns:
        Tuple of two offspring configurations
    """
    if len(a) != len(b):
        raise ValueError("Parent configurations must have equal length")

    num_phases = len(a)
    if n >= num_phases:
        n = num_phases - 1

    # Generate sorted crossover points
    crossover_points = sorted(sample(range(1, num_phases), n))
    crossover_points.append(num_phases)  # Add endpoint

    # Initialize offspring
    child1 = []
    child2 = []
    prev_point = 0

    # Alternate parents at each crossover segment
    use_a = True
    for point in crossover_points:
        segment = slice(prev_point, point)

        if use_a:
            child1.extend(copy.deepcopy(a[segment]))
            child2.extend(copy.deepcopy(b[segment]))
        else:
            child1.extend(copy.deepcopy(b[segment]))
            child2.extend(copy.deepcopy(a[segment]))

        use_a = not use_a
        prev_point = point

    # Enforce minimum green times
    for phase in child1 + child2:
        phase.green = max(min_green, phase.green)

    return child1, child2


def crossover(
    a: TrafficConfiguration,
    b: TrafficConfiguration,
    num_offspring: int = 3,
    max_points: int = 2
) -> List[TrafficConfiguration]:
    """
    Generates multiple offspring using varied n-point crossover.

    Args:
        a: First parent
        b: Second parent
        num_offspring: Number of offspring to generate
        max_points: Maximum crossover points to try

    Returns:
        List of offspring configurations
    """
    offspring = []

    for _ in range(num_offspring):
        # Vary the number of crossover points
        n = randint(1, min(max_points, len(a)-1))
        child1, child2 = n_point_crossover(a, b, n=n)

        offspring.append(child1)
        if len(offspring) < num_offspring:
            offspring.append(child2)

    return offspring[:num_offspring]


def mutation(
    traffic_configuration: TrafficConfiguration,
    delta: float = 5.0,
    min_green: float = 5.0
) -> TrafficConfiguration:
    """
    Applies Green Time Shift Mutation to a traffic signal configuration.

    This mutation operator selects a random signal phase and adjusts its green time
    by a small random value in the range [-delta, +delta]. To maintain the overall
    cycle time, the change is proportionally redistributed among the other phases.
    Green times are clamped to a minimum threshold to ensure safety and feasibility.

    Args:
        traffic_configuration (TrafficConfiguration): The traffic signal configuration
            to be mutated, consisting of multiple phases.
        delta (float, optional): Maximum magnitude of the mutation shift in seconds.
            Defaults to 5.0.
        min_green (float, optional): Minimum allowed green time per phase in seconds.
            Defaults to 5.0.

    Returns:
        TrafficConfiguration: A new traffic configuration with the green time
        of one phase mutated and the rest adjusted accordingly.
    """
    num_phases = len(traffic_configuration)
    if num_phases <= 1:
        return traffic_configuration

    mutated_configuration = copy.deepcopy(traffic_configuration)

    i = randint(0, num_phases - 1)
    mutation = uniform(-delta, delta)

    mutated_configuration[i].green += int(mutation)

    if mutated_configuration[i].green < min_green:
        mutation += min_green - mutated_configuration[i].green
        mutated_configuration[i].green = min_green

    redistribution = int(-mutation / (num_phases - 1))

    for j in range(num_phases):
        if j == i:
            continue
        mutated_configuration[j].green += redistribution
        if mutated_configuration[j].green < min_green:
            mutated_configuration[j].green = min_green

    for phase in mutated_configuration:
        if phase.green < min_green:
            phase.green = min_green

    return mutated_configuration


def run_evolution(
    population_dict: dict,
    fitness_func: FitnessFunc = fitness,
    generation_limit: int = 50
) -> Tuple[Population, int]:
    # Convert dictionary to list of configurations
    population = list(population_dict.values())

    pprint.pprint(population)

    for generation in range(generation_limit):
        print(f"\n--- Generation {generation+1}/{generation_limit} ---")
        # Evaluate and sort population by fitness (lower is better)
        population.sort(key=lambda config: fitness_func(config))

        top_1 = population[0]
        print(f"{top_1}")
        print(f"{fitness_func(top_1)}")

        # pprint.pprint(population)

        next_gen = population[1:]

        # Fill remaining slots through selection, crossover and mutation
        while len(next_gen) < len(population) - 1:

            # Select parents using tournament selection
            parents = selection(population, fitness_func)

            # Generate offspring
            offspring = crossover(parents[0], parents[1])

            # Mutate and add to new generation
            next_gen.extend(offspring)

        next_gen = [mutation(config) for config in next_gen]

        # pprint.pprint(next_gen)

        next_gen.append(top_1)

        population = next_gen

        # print(population)

    best_score = fitness_func(population[-1])
    print(f"Best fitness: {best_score}")
    print(f"Worst fitness: {fitness_func(population[-2])}")

    # Return sorted population and generation count
    return sorted(population, key=lambda config: fitness_func(config)), generation
