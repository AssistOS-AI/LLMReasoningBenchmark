#!/usr/bin/env python3
"""
Enhanced Random Transportation Problem Generator and Solver
Generates random transportation problems with configurable individuals per species.
"""

import random
import argparse
import sys
from nlToZ3 import NLToZ3Converter


class RandomProblemGenerator:
    def __init__(self):
        # Components for generating random species names
        self.prefixes = [
            "vor", "zul", "kra", "thi", "mor", "vel", "dra", "gol", "sar", "nex",
            "qua", "xer", "zep", "wol", "vir", "kor", "lux", "hex", "pry", "tox",
            "blu", "cyn", "flo", "gri", "hol", "ivy", "jam", "kel", "lum", "myr",
            "noc", "oxy", "pix", "qin", "rio", "sky", "tor", "ulu", "vex", "wyr"
        ]
        
        self.suffixes = [
            "nix", "por", "thy", "rex", "lok", "dar", "ven", "mar", "tul", "fox",
            "bel", "cur", "dex", "fin", "gor", "hyx", "jin", "kep", "lyr", "mex",
            "nol", "pyx", "qor", "rix", "sol", "tyx", "ulm", "vox", "wex", "zyx",
            "aks", "elf", "imp", "orc", "fey", "kin", "orn", "ian", "oid", "ant"
        ]
        
        self.middleParts = [
            "a", "e", "i", "o", "u", "y", "ar", "er", "ir", "or", "ur", 
            "an", "en", "in", "on", "un", "al", "el", "il", "ol", "ul"
        ]
        
        # Constraint templates
        self.constraintTemplates = [
            "if {protected} are present, they must not be outnumbered by {threatening}",
            "on either bank, if {protected} are present, they must not be outnumbered by {threatening}",
        ]
        
        # Additional constraint types for variety
        self.advancedConstraints = [
            "if {species1} are present without {species2}, they must not be with {species3}",
            "{species1} must always be accompanied by at least one {species2}",
        ]
    
    def generateRandomSpeciesName(self) -> str:
        """Generate a single random species name."""
        # Choose structure: prefix + middle + suffix (80%) or prefix + suffix (20%)
        if random.random() < 0.8:
            # Three-part name
            prefix = random.choice(self.prefixes)
            middle = random.choice(self.middleParts)
            suffix = random.choice(self.suffixes)
            name = prefix + middle + suffix
        else:
            # Two-part name
            prefix = random.choice(self.prefixes)
            suffix = random.choice(self.suffixes)
            name = prefix + suffix
        
        return name
    
    def generateSpeciesNames(self, numSpecies: int) -> list:
        """Generate unique random species names."""
        generatedNames = set()
        attempts = 0
        maxAttempts = numSpecies * 10  # Prevent infinite loop
        
        while len(generatedNames) < numSpecies and attempts < maxAttempts:
            name = self.generateRandomSpeciesName()
            generatedNames.add(name)
            attempts += 1
        
        if len(generatedNames) < numSpecies:
            raise ValueError(f"Could only generate {len(generatedNames)} unique species names after {maxAttempts} attempts")
        
        return list(generatedNames)
    
    def generateSpeciesCounts(self, speciesNames: list, individualsPerSpecies: int = None, 
                             minCount: int = 1, maxCount: int = 4) -> dict:
        """Generate counts for each species."""
        if individualsPerSpecies is not None:
            # Use fixed count for all species
            return {species: individualsPerSpecies for species in speciesNames}
        else:
            # Use random counts within range
            return {species: random.randint(minCount, maxCount) for species in speciesNames}
    
    def generateShuttleCapacity(self, totalIndividuals: int, capacityMode: str = "auto") -> int:
        """Generate a reasonable shuttle capacity."""
        if capacityMode == "auto":
            # Capacity should be less than total to make it interesting
            # but not too small to make it impossible
            minCapacity = max(1, totalIndividuals // 4)
            maxCapacity = max(2, totalIndividuals // 2)
            return random.randint(minCapacity, maxCapacity)
        elif capacityMode == "tight":
            # Very small capacity for challenging problems
            return max(1, totalIndividuals // 6)
        elif capacityMode == "generous":
            # Larger capacity for easier problems
            return max(2, totalIndividuals // 2)
        else:
            return 2  # Default capacity
    
    def generateConstraints(self, speciesNames: list, numConstraints: int) -> list:
        """Generate random constraints between species."""
        if numConstraints == 0:
            return []
        
        constraints = []
        usedPairs = set()
        
        for _ in range(numConstraints):
            attempts = 0
            while attempts < 50:  # Prevent infinite loop
                # Choose constraint type
                if random.random() < 0.8:  # 80% chance for "not outnumbered" constraints
                    template = random.choice(self.constraintTemplates)
                    protected = random.choice(speciesNames)
                    threatening = random.choice([s for s in speciesNames if s != protected])
                    
                    pair = (protected, threatening)
                    if pair not in usedPairs:
                        constraint = template.format(protected=protected, threatening=threatening)
                        constraints.append(constraint)
                        usedPairs.add(pair)
                        break
                
                attempts += 1
            
            if attempts >= 50:
                print(f"Warning: Could only generate {len(constraints)} constraints instead of {numConstraints}")
                break
        
        return constraints
    
    def generateProblem(self, numSpecies: int, numConstraints: int, 
                       individualsPerSpecies: int = None, minCount: int = 1, 
                       maxCount: int = 4, capacity: int = None, capacityMode: str = "auto") -> str:
        """Generate a complete random transportation problem."""
        # Generate species
        speciesNames = self.generateSpeciesNames(numSpecies)
        speciesCounts = self.generateSpeciesCounts(speciesNames, individualsPerSpecies, 
                                                  minCount, maxCount)
        
        # Calculate total individuals and shuttle capacity
        totalIndividuals = sum(speciesCounts.values())
        if capacity is not None:
            shuttleCapacity = capacity
        else:
            shuttleCapacity = self.generateShuttleCapacity(totalIndividuals, capacityMode)
        
        # Generate constraints
        constraints = self.generateConstraints(speciesNames, numConstraints)
        
        # Build the problem description
        problemLines = [
            f"A shuttle with capacity {shuttleCapacity} must transport a group of species from the start to the target bank."
        ]
        
        # Add species
        for species, count in speciesCounts.items():
            problemLines.append(f"  - {species}: {count} individual(s)")
        
        # Add constraints
        for constraint in constraints:
            problemLines.append(f"* {constraint}.")
        
        return '\n'.join(problemLines)


def solveRandomProblem(numSpecies: int, numConstraints: int, individualsPerSpecies: int = None,
                      minCount: int = 1, maxCount: int = 4, capacity: int = None, 
                      capacityMode: str = "auto", showCode: bool = False, seed: int = None, 
                      findAllSolutions: bool = False, maxSteps: int = 100):
    """Generate and solve a random transportation problem."""
    if seed is not None:
        random.seed(seed)
        print(f"🎲 Using random seed: {seed}")
    
    print("🎯 Enhanced Random Transportation Problem Generator")
    print("=" * 60)
    
    if individualsPerSpecies is not None:
        if capacity is not None:
            print(f"Generating problem with {numSpecies} species, {individualsPerSpecies} individuals each, capacity {capacity}, and {numConstraints} constraints...")
        else:
            print(f"Generating problem with {numSpecies} species, {individualsPerSpecies} individuals each, and {numConstraints} constraints...")
    else:
        if capacity is not None:
            print(f"Generating problem with {numSpecies} species ({minCount}-{maxCount} individuals each), capacity {capacity}, and {numConstraints} constraints...")
        else:
            print(f"Generating problem with {numSpecies} species ({minCount}-{maxCount} individuals each) and {numConstraints} constraints...")
    print()
    
    # Generate the problem
    generator = RandomProblemGenerator()
    
    try:
        problemText = generator.generateProblem(numSpecies, numConstraints, 
                                               individualsPerSpecies, minCount, 
                                               maxCount, capacity, capacityMode)
        
        print("📋 GENERATED PROBLEM:")
        print("=" * 60)
        print(problemText)
        print()
        
        # Solve using nlToZ3
        print("🔍 SOLVING WITH nlToZ3...")
        print("=" * 60)
        
        converter = NLToZ3Converter()
        z3Code = converter.solveProblem(problemText, findAllSolutions=findAllSolutions, maxSteps=maxSteps)
        
        if showCode:
            print("\n" + "💻 GENERATED Z3 CODE:")
            print("=" * 60)
            print(z3Code)
        
        return problemText, z3Code
        
    except Exception as e:
        print(f"❌ Error generating or solving problem: {e}")
        return None, None


def batchTest(numProblems: int, maxSpecies: int = 4, maxConstraints: int = 2,
             individualsPerSpecies: int = None, capacity: int = None, findAllSolutions: bool = False, maxSteps: int = 100):
    """Generate and test multiple random problems."""
    print(f"🧪 BATCH TESTING - Generating {numProblems} random problems")
    if individualsPerSpecies is not None:
        print(f"Using {individualsPerSpecies} individuals per species")
    if capacity is not None:
        print(f"Using shuttle capacity {capacity}")
    print("=" * 80)
    
    successes = 0
    failures = 0
    
    for i in range(numProblems):
        print(f"\n🔄 Problem {i+1}/{numProblems}")
        print("-" * 40)
        
        # Random parameters
        numSpecies = random.randint(2, maxSpecies)
        numConstraints = random.randint(0, min(maxConstraints, numSpecies // 2))
        seed = random.randint(1, 10000)
        
        try:
            problemText, z3Code = solveRandomProblem(
                numSpecies, numConstraints, individualsPerSpecies, capacity=capacity, 
                seed=seed, findAllSolutions=findAllSolutions, maxSteps=maxSteps
            )
            
            if problemText and z3Code:
                successes += 1
                print("✅ Success")
            else:
                failures += 1
                print("❌ Failed")
                
        except Exception as e:
            failures += 1
            print(f"❌ Exception: {e}")
    
    print(f"\n📊 BATCH RESULTS:")
    print(f"Successes: {successes}/{numProblems}")
    print(f"Failures: {failures}/{numProblems}")
    print(f"Success Rate: {(successes/numProblems)*100:.1f}%")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Enhanced Random Transportation Problem Generator and Solver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generateRandomProblems.py --species 3 --constraints 1 --individuals 2 --capacity 2
  python generateRandomProblems.py --species 4 --constraints 2 --individuals 3 --capacity 3 --show-code
  python generateRandomProblems.py --batch 10 --individuals 2 --capacity 1
  python generateRandomProblems.py --species 3 --constraints 1 --individuals 2 --seed 42
  python generateRandomProblems.py --species 3 --constraints 1 --min-count 1 --max-count 3 --capacity 2
        """
    )
    
    parser.add_argument('--species', '-s', type=int, default=3,
                       help='Number of species to generate (default: 3)')
    parser.add_argument('--constraints', '-c', type=int, default=1,
                       help='Number of constraints to generate (default: 1)')
    parser.add_argument('--individuals', '-i', type=int,
                       help='Fixed number of individuals per species (overrides min/max-count)')
    parser.add_argument('--min-count', type=int, default=1,
                       help='Minimum individuals per species when --individuals not specified (default: 1)')
    parser.add_argument('--max-count', type=int, default=4,
                       help='Maximum individuals per species when --individuals not specified (default: 4)')
    parser.add_argument('--capacity', '-cap', type=int,
                       help='Fixed shuttle capacity (overrides capacity-mode)')
    parser.add_argument('--capacity-mode', choices=['auto', 'tight', 'generous'], default='auto',
                       help='Shuttle capacity generation mode when --capacity not specified (default: auto)')
    parser.add_argument('--show-code', action='store_true',
                       help='Show generated Z3 code')
    parser.add_argument('--all-solutions', action='store_true',
                       help='Find all optimal solutions (minimum steps) instead of just the first one')
    parser.add_argument('--seed', type=int,
                       help='Random seed for reproducible results')
    parser.add_argument('--batch', type=int,
                       help='Run batch test with N random problems')
    parser.add_argument('--max-steps', type=int, default=100,
                       help='Maximum number of steps to try when solving (default: 100)')
    
    args = parser.parse_args()
    
    if args.batch:
        batchTest(args.batch, individualsPerSpecies=args.individuals, 
                  capacity=args.capacity, findAllSolutions=args.all_solutions, maxSteps=args.max_steps)
    else:
        solveRandomProblem(
            args.species, 
            args.constraints,
            args.individuals,
            args.min_count,
            args.max_count,
            args.capacity,
            args.capacity_mode,
            args.show_code,
            args.seed,
            args.all_solutions,
            args.max_steps
        )


if __name__ == "__main__":
    main() 