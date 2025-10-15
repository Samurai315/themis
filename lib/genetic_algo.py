import random
import numpy as np
from deap import base, creator, tools, algorithms
import streamlit as st

class ScheduleGA:
    """Genetic Algorithm for Schedule Optimization using DEAP"""
    
    def __init__(self, entities, constraints, config=None):
        self.entities = entities
        self.constraints = constraints
        
        # Default configuration with all tunable parameters
        self.config = config or {}
        self.config.setdefault("population_size", 100)
        self.config.setdefault("generations", 500)
        self.config.setdefault("crossover_prob", 0.7)
        self.config.setdefault("mutation_prob", 0.1)
        self.config.setdefault("tournament_size", 3)
        self.config.setdefault("elitism_rate", 0.1)
        
        # Constraint weights (adjustable from frontend)
        self.config.setdefault("weight_no_overlap", 100)
        self.config.setdefault("weight_room_capacity", 80)
        self.config.setdefault("weight_availability", 90)
        self.config.setdefault("weight_preferred_time", 20)
        self.config.setdefault("weight_balanced_distribution", 30)
        self.config.setdefault("weight_consecutive_slots", 15)
        self.config.setdefault("weight_gap_penalty", 10)
        
        # Fitness calculation method
        self.config.setdefault("fitness_method", "weighted")  # or "penalty_based"
        
        # Mutation strategy
        self.config.setdefault("mutation_strategy", "swap")  # swap, shift, random
        
        # Time slots and resources (customizable)
        self.days = self.config.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        self.time_slots = self.config.get("time_slots", ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"])
        self.rooms = self.config.get("rooms", ["R101", "R102", "R103", "R104", "R105"])
        
        self.setup_deap()
    
    def setup_deap(self):
        """Initialize DEAP framework"""
        # Clear any existing definitions
        if hasattr(creator, "FitnessMax"):
            del creator.FitnessMax
        if hasattr(creator, "Individual"):
            del creator.Individual
        
        # Create fitness and individual classes
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)
        
        # Initialize toolbox
        self.toolbox = base.Toolbox()
        
        # Register genetic operators
        self.toolbox.register("individual", self.create_individual)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        self.toolbox.register("evaluate", self.evaluate_fitness)
        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", self.mutate_schedule)
        self.toolbox.register("select", tools.selTournament, tournsize=self.config["tournament_size"])
    
    def create_individual(self):
        """Create random schedule (individual)"""
        schedule = []
        for entity in self.entities:
            gene = {
                "entity_id": entity["id"],
                "entity_name": entity.get("name", entity["id"]),
                "day": random.choice(self.days),
                "time": random.choice(self.time_slots),
                "room": random.choice(self.rooms),
                "duration": entity.get("duration", 2)
            }
            schedule.append(gene)
        return creator.Individual(schedule)
    
    def evaluate_fitness(self, individual):
        """Calculate fitness score based on constraints with configurable weights"""
        score = 1000.0
        
        # Hard constraints
        for constraint in self.constraints:
            if constraint["type"] == "no_overlap":
                violations = self.check_overlaps(individual)
                score -= violations * self.config["weight_no_overlap"]
            
            elif constraint["type"] == "room_capacity":
                violations = self.check_room_capacity(individual)
                score -= violations * self.config["weight_room_capacity"]
            
            elif constraint["type"] == "availability":
                violations = self.check_availability(individual, constraint)
                score -= violations * self.config["weight_availability"]
        
        # Soft constraints (preferences)
        for constraint in self.constraints:
            if constraint["type"] == "preferred_time":
                matches = self.check_preferred_times(individual, constraint)
                score += matches * self.config["weight_preferred_time"]
            
            elif constraint["type"] == "balanced_distribution":
                balance_score = self.check_balance(individual)
                score += balance_score * self.config["weight_balanced_distribution"]
            
            elif constraint["type"] == "consecutive_slots":
                bonus = self.check_consecutive_preference(individual, constraint)
                score += bonus * self.config["weight_consecutive_slots"]
            
            elif constraint["type"] == "minimize_gaps":
                gaps = self.check_gaps(individual)
                score -= gaps * self.config["weight_gap_penalty"]
        
        # Apply fitness method
        if self.config["fitness_method"] == "penalty_based":
            # Exponential penalty for violations
            if score < 0:
                score = 1000.0 / (1 + abs(score))
        
        return (max(score, 0),)
    
    def check_overlaps(self, individual):
        """Check for room/time conflicts"""
        conflicts = 0
        for i, slot1 in enumerate(individual):
            for slot2 in individual[i+1:]:
                if (slot1["day"] == slot2["day"] and 
                    slot1["time"] == slot2["time"] and 
                    slot1["room"] == slot2["room"]):
                    conflicts += 1
        return conflicts
    
    def check_room_capacity(self, individual):
        """Check if room capacity constraints are met"""
        violations = 0
        for slot in individual:
            entity = next((e for e in self.entities if e["id"] == slot["entity_id"]), None)
            if entity:
                required = entity.get("capacity_needed", 0)
                room_capacity = self.get_room_capacity(slot["room"])
                if required > room_capacity:
                    violations += 1
        return violations
    
    def check_availability(self, individual, constraint):
        """Check entity availability constraints"""
        violations = 0
        entity_id = constraint.get("entity_id")
        unavailable = constraint.get("unavailable_slots", [])
        
        for slot in individual:
            if slot["entity_id"] == entity_id:
                slot_key = f"{slot['day']}_{slot['time']}"
                if slot_key in unavailable:
                    violations += 1
        return violations
    
    def check_preferred_times(self, individual, constraint):
        """Reward preferred time slot assignments"""
        matches = 0
        entity_id = constraint.get("entity_id")
        preferred = constraint.get("preferred_slots", [])
        
        for slot in individual:
            if slot["entity_id"] == entity_id:
                slot_key = f"{slot['day']}_{slot['time']}"
                if slot_key in preferred:
                    matches += 1
        return matches
    
    def check_balance(self, individual):
        """Check workload distribution balance across days"""
        day_counts = {day: 0 for day in self.days}
        for slot in individual:
            day_counts[slot["day"]] += 1
        
        # Calculate variance (lower is better)
        variance = np.var(list(day_counts.values()))
        
        # Return negative variance as penalty (or use std deviation)
        balance_score = 100 / (1 + variance)
        return balance_score
    
    def check_consecutive_preference(self, individual, constraint):
        """Reward consecutive time slots for same entity"""
        bonus = 0
        entity_id = constraint.get("entity_id")
        
        # Group slots by day for this entity
        entity_slots = [s for s in individual if s["entity_id"] == entity_id]
        
        for day in self.days:
            day_slots = sorted([s for s in entity_slots if s["day"] == day], 
                              key=lambda x: self.time_slots.index(x["time"]))
            
            # Check for consecutive times
            for i in range(len(day_slots) - 1):
                time1_idx = self.time_slots.index(day_slots[i]["time"])
                time2_idx = self.time_slots.index(day_slots[i+1]["time"])
                if time2_idx == time1_idx + 1:
                    bonus += 1
        
        return bonus
    
    def check_gaps(self, individual):
        """Calculate gaps between slots in a day"""
        total_gaps = 0
        
        for day in self.days:
            day_slots = sorted([s for s in individual if s["day"] == day],
                              key=lambda x: self.time_slots.index(x["time"]))
            
            if len(day_slots) > 1:
                for i in range(len(day_slots) - 1):
                    time1_idx = self.time_slots.index(day_slots[i]["time"])
                    time2_idx = self.time_slots.index(day_slots[i+1]["time"])
                    gap = time2_idx - time1_idx - 1
                    if gap > 0:
                        total_gaps += gap
        
        return total_gaps
    
    def get_room_capacity(self, room):
        """Get room capacity"""
        capacities = self.config.get("room_capacities", {
            "R101": 30, "R102": 50, "R103": 100,
            "R104": 40, "R105": 60
        })
        return capacities.get(room, 30)
    
    def mutate_schedule(self, individual):
        """Custom mutation operator with configurable strategy"""
        if random.random() < self.config["mutation_prob"]:
            strategy = self.config["mutation_strategy"]
            
            if strategy == "swap":
                # Swap two random genes
                if len(individual) >= 2:
                    i, j = random.sample(range(len(individual)), 2)
                    individual[i], individual[j] = individual[j], individual[i]
            
            elif strategy == "shift":
                # Shift one gene to different time/day/room
                idx = random.randint(0, len(individual) - 1)
                mutation_type = random.choice(["day", "time", "room"])
                
                if mutation_type == "day":
                    individual[idx]["day"] = random.choice(self.days)
                elif mutation_type == "time":
                    individual[idx]["time"] = random.choice(self.time_slots)
                else:
                    individual[idx]["room"] = random.choice(self.rooms)
            
            elif strategy == "random":
                # Complete random reassignment
                idx = random.randint(0, len(individual) - 1)
                individual[idx]["day"] = random.choice(self.days)
                individual[idx]["time"] = random.choice(self.time_slots)
                individual[idx]["room"] = random.choice(self.rooms)
        
        return (individual,)
    
    def evolve(self, progress_callback=None):
        """Run genetic algorithm evolution with real-time progress"""
        population = self.toolbox.population(n=self.config["population_size"])
        
        # Statistics tracking
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("max", np.max)
        stats.register("min", np.min)
        stats.register("std", np.std)
        
        # Hall of fame (best individuals)
        hof = tools.HallOfFame(1)
        
        history = []
        
        # Evolution loop
        for gen in range(self.config["generations"]):
            # Evaluate population
            fitnesses = map(self.toolbox.evaluate, population)
            for ind, fit in zip(population, fitnesses):
                ind.fitness.values = fit
            
            # Update statistics
            record = stats.compile(population)
            hof.update(population)
            
            history.append({
                "generation": gen,
                "avg_fitness": record["avg"],
                "max_fitness": record["max"],
                "min_fitness": record["min"],
                "std_fitness": record["std"]
            })
            
            # Progress callback for UI updates
            if progress_callback:
                progress_callback(gen, record["max"], record["avg"], record["std"])
            
            # Early stopping if perfect solution found
            if record["max"] >= 1000:
                break
            
            # Selection
            offspring = self.toolbox.select(population, len(population))
            offspring = list(map(self.toolbox.clone, offspring))
            
            # Apply elitism
            elite_count = max(1, int(len(population) * self.config["elitism_rate"]))
            elites = tools.selBest(population, elite_count)
            
            # Crossover
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < self.config["crossover_prob"]:
                    self.toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values
            
            # Mutation
            for mutant in offspring:
                self.toolbox.mutate(mutant)
                del mutant.fitness.values
            
            # Replace population with offspring + elites
            population[:] = offspring[:-elite_count] + elites
        
        # Return best solution
        best = hof[0]
        return {
            "schedule": list(best),
            "fitness": best.fitness.values[0],
            "history": history,
            "config_used": self.config
        }
