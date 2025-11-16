import copy
import tempfile
import random
import numpy as np
from pathlib import Path
from typing import List, Tuple
from custom_typings import (Movement, SignalPlan, SignalPopulation, Intersection,
                            FitnessFunc, PopulateFunc, SelectionFunc,
                            CrossoverFunc, MutationFunc)
from algorithms.websters import compute_signal_config_with_poisson_and_websters
from sumo_functions import generate_traffic_lights_xml, create_sumo_config
from sumo_report import generate_report, run_sumo
from constants import GA_ENHANCED_PATH


def generate_population(size: int, signal_plan: SignalPlan) -> SignalPopulation:
    """
    Generate a population of traffic signal configurations using Poisson flow simulation.

    Args:
        size: Number of candidate configurations to generate
        movements: List of Movement objects defining each allowed movement

    Returns:
        SignalPopulation: List of SignalPlan objects, each a list of SignalPhase objects
    """
    population: SignalPopulation = []

    for _ in range(size):
        # Use Poisson-based computation to get realistic green/amber/all-red times
        tl_config = compute_signal_config_with_poisson_and_websters(
            copy.deepcopy(signal_plan))

        # The function already populates SignalPhase objects with SUMO-compatible states
        population.append(tl_config)

    return population


def selection(
    fitness_scores: list[tuple[SignalPlan, float]]
) -> list[SignalPlan]:
    """
    Selects two individuals from the population using fitness-proportional selection
    (roulette wheel) based on precomputed fitness scores.

    Args:
        fitness_scores (list[tuple[SignalPlan, float]]): List of tuples (signal_plan, fitness_score).

    Returns:
        list[SignalPlan]: Two selected signal plans.
    """
    # Extract individuals and their fitness
    individuals, scores = zip(*fitness_scores)

    # Convert fitness to selection weights (higher fitness -> lower probability)
    # Assuming lower fitness is better
    max_score = max(scores)
    # small epsilon to avoid zero weight
    weights = [max_score - s + 1e-6 for s in scores]

    selected = random.choices(individuals, weights=weights, k=2)
    return selected


def crossover(
    parent1: SignalPlan,
    parent2: SignalPlan,
    num_offspring: int = 3,
    alpha_range: Tuple[float, float] = (-0.25, 1.25),
    min_green: float = 5.0,
    min_amber: float = 2.0,
    min_all_red: float = 1.0
) -> List[SignalPlan]:
    """
    Linear (blended) crossover for continuous-valued SignalPlans.

    Each child phase timing parameter is computed as:
        child = p1 + α * (p2 - p1)

    where α ∈ [alpha_range[0], alpha_range[1]] controls blending/extrapolation.

    This preserves feasibility and introduces diversity through random α values.
    """

    if len(parent1) != len(parent2):
        raise ValueError("Parent SignalPlans must have equal number of phases")

    offspring: List[SignalPlan] = []

    for _ in range(num_offspring):
        α = random.uniform(*alpha_range)
        child_plan: SignalPlan = []

        for phase1, phase2 in zip(parent1, parent2):
            child_phase = copy.deepcopy(phase1)

            # Weighted average of each timing parameter
            child_phase.green = phase1.green + \
                α * (phase2.green - phase1.green)
            child_phase.amber = phase1.amber + \
                α * (phase2.amber - phase1.amber)
            child_phase.all_red = phase1.all_red + \
                α * (phase2.all_red - phase1.all_red)
            child_phase.duration = phase1.duration + \
                α * (phase2.duration - phase1.duration)
            child_phase.start = phase1.start + \
                α * (phase2.start - phase1.start)

            # Clamp + round for realism / feasibility
            child_phase.green = max(min_green, round(child_phase.green))
            child_phase.amber = max(min_amber, round(child_phase.amber))
            child_phase.all_red = max(min_all_red, round(child_phase.all_red))

            child_plan.append(child_phase)

        offspring.append(child_plan)

    return offspring


def compute_diversity(population: SignalPopulation) -> float:
    """
    Compute population diversity D as the variance of green times across all phases.
    Equation 3.23.
    """
    greens = []
    for plan in population:
        for phase in plan:
            greens.append(phase.green)
    if not greens:
        return 0.0
    return float(np.var(greens))  # variance as diversity measure


def mutation(
    signal_plan: SignalPlan,
    population: SignalPopulation,
    generation: int,
    generation_limit: int,
    min_green: float = 5.0,
    delta_base: float = 5.0
) -> SignalPlan:

    mutated = copy.deepcopy(signal_plan)
    num_phases = len(mutated)
    if num_phases == 0:
        return mutated

    # Diversity
    D = max(0.0, min(1.0, compute_diversity(population)))

    # Generation progress
    t = generation / max(1, generation_limit - 1)
    decay = (1 - t)**0.75
    diversity_boost = 0.5 + 0.5 * D

    adaptive_delta = delta_base * decay * diversity_boost

    # Select one phase
    idx = random.randint(0, num_phases - 1)

    # Mutate ONLY that phase
    raw_shift = random.uniform(-adaptive_delta, adaptive_delta)

    mutated[idx].green = max(min_green, mutated[idx].green + raw_shift)
    mutated[idx].green = round(mutated[idx].green)

    return mutated


def run_evolution(
    intersection: Intersection,
    signal_plan_template: SignalPlan,
    population: SignalPopulation,
    generation_limit: int = 50,
    elitism_rate: float = 0.2,
    immigration_interval: int = 10,
    immigration_rate: float = 0.2,
    fitness_tolerance: float = 0.03,
    routes_path: str | None = None,
    net_path: str | None = None,

) -> Tuple[SignalPopulation, int]:
    """
    Run GA for signal timing optimization.
    """
    print(f"\n🚦 Starting GA in: {GA_ENHANCED_PATH.resolve()}")
    GA_ENHANCED_PATH.mkdir(parents=True, exist_ok=True)

    pop_size = len(population)
    elite_count = max(1, int(pop_size * elitism_rate))
    best_overall = None
    best_score = 99999

    for generation in range(generation_limit):
        print(f"--- Generation {generation + 1}/{generation_limit} ---")

        # --- 1. Evaluate fitness per individual ---
        fitness_scores = get_fitness_scores(
            population=population, intersection=intersection, routes_path=routes_path, net_path=net_path)

        # --- 2. Sort population ---
        fitness_scores.sort(key=lambda x: x[1])

        # --- 3. Record best individual ---
        best_plan_gen, best_score_gen = fitness_scores[0]

        if best_score_gen < best_score:
            best_score = best_score_gen
            best_overall = copy.deepcopy(best_plan_gen)

        print(f"BEST FITNESS: {best_score_gen}")

        # --- 4. Elitism ---
        # Keep top 'elite_count' individuals for the next generation
        elites = [copy.deepcopy(plan)
                  for plan, score in fitness_scores[:elite_count]]

        # Start next generation with elites
        next_gen = elites.copy()

        # --- 5. Immigration ---
        if (generation + 1) % immigration_interval == 0:
            num_immigrants = int(pop_size * immigration_rate)
            immigrants = generate_population(
                num_immigrants, copy.deepcopy(signal_plan_template))
            next_gen.extend(immigrants)

        # --- 6. Reproduction (Selection + Crossover + Mutation) ---
        while len(next_gen) < pop_size:
            parents = selection(fitness_scores)
            offspring = crossover(parents[0], parents[1])
            mutated_offspring = [
                mutation(child, population, generation, generation_limit)
                for child in offspring
            ]
            next_gen.extend(mutated_offspring)

        population = next_gen[:pop_size]

        # --- 7. Convergence check ---
        fitness_values = [score for _, score in fitness_scores]
        fit_var = float(np.var(fitness_values))
        if fit_var < fitness_tolerance:
            print(f"🛑 Converged early at generation {generation + 1}")
            break

    # --- Final sorting ---
    final_sorted = []
    fitness_scores = get_fitness_scores(
        population=population, intersection=intersection, routes_path=routes_path, net_path=net_path)

    # --- Sort population based on fitness ---
    final_sorted = [plan for plan, _ in sorted(
        fitness_scores, key=lambda x: x[1])]

    return final_sorted, generation + 1


def get_fitness_scores(population: SignalPopulation, intersection: Intersection, routes_path: str, net_path: str) -> List[Tuple[SignalPlan, float]]:
    fitness_scores = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        for idx, plan in enumerate(population):
            # Paths inside temp folder
            tmp_sumocfg = tmp_path / f"simulation_{idx}.sumocfg"
            tmp_tls = tmp_path / f"traffic_light_{idx}.tls.xml"
            tmp_tripinfo = tmp_path / f"tripinfo_{idx}.xml"
            tmp_detector = tmp_path / f"detectors_{idx}.xml"

            # Generate TLS and SUMO config
            generate_traffic_lights_xml(
                signal_plan=plan, net_path=net_path, output_path=tmp_tls)
            create_sumo_config(routes_path=routes_path, net_path=net_path,
                               tls_path=tmp_tls, output_path=tmp_sumocfg)

            # Run SUMO
            run_sumo(net_file=str(net_path), sumocfg_path=str(tmp_sumocfg),
                     tripinfo_out=str(tmp_tripinfo), detector_out=str(tmp_detector),
                     tls_path=str(tmp_tls))

            # Generate report
            report = generate_report(intersection=intersection,
                                     tripinfo_path=str(tmp_tripinfo),
                                     detector_path=str(tmp_detector),
                                     base_dir=tmp_path)

            print(f"Ind {idx + 1}: {report["fitness_score"]}")
            for p_i, phase in enumerate(plan):
                print(
                    f"   Phase {p_i + 1}: green={phase.green}, amber={phase.amber}, all_red={phase.all_red}")

            # Store fitness
            fitness_scores.append(
                (copy.deepcopy(plan), report["fitness_score"]))

        return fitness_scores
