#!/usr/bin/env python3
"""
Enhanced Random Transportation Problem Generator and Solver
Generates random transportation problems with configurable individuals per species.
"""

import random
import argparse
import sys
import os
import glob
from datetime import datetime
from nlToZ3 import NLToZ3Converter


def getNextProblemNumber() -> int:
    """Find the next available problem number by checking existing problem files."""
    problemFiles = glob.glob("problem*.txt")
    if not problemFiles:
        return 1
    
    # Extract numbers from existing problem files
    numbers = []
    for filename in problemFiles:
        # Extract number from filename like "problem3.txt"
        try:
            numStr = filename.replace("problem", "").replace(".txt", "")
            if numStr.isdigit():
                numbers.append(int(numStr))
        except:
            continue
    
    if not numbers:
        return 1
    
    return max(numbers) + 1


def saveProblemToFile(problemText: str, numSpecies: int, totalIndividuals: int, capacity: int) -> str:
    """Save the problem text to a file with format: problem_numSpecies_totalIndividuals_capacity_timestamp.txt"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"problem_{numSpecies}s_{totalIndividuals}i_{capacity}c_{timestamp}.txt"
    
    # Ensure problems directory exists
    problemsDir = "problems"
    if not os.path.exists(problemsDir):
        os.makedirs(problemsDir)
    
    # Save in problems directory
    filepath = os.path.join(problemsDir, filename)
    
    try:
        with open(filepath, 'w') as f:
            f.write(problemText)
        return filepath
    except Exception as e:
        print(f"❌ Error saving problem to {filepath}: {e}")
        return None


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
        
        # All-species constraint templates - these involve ALL species in the problem
        self.allSpeciesConstraints = [
            "on either bank, if {protectedGroup} are present, they must not be outnumbered by {threateningGroup}",
            "if {protectedGroup} are all present together, they must not be outnumbered by {threateningGroup} combined",
            "on either bank, {protectedGroup} must never be outnumbered by {threateningGroup} when all are present",
            "if any of {protectedGroup} are present, they collectively must not be outnumbered by {threateningGroup}",
            "when {protectedGroup} and {threateningGroup} are on the same bank, {protectedGroup} must not be outnumbered",
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
    
    def generateSpeciesCounts(self, speciesNames: list, totalIndividuals: int = None,
                             individualsPerSpecies: int = None, minCount: int = 1, maxCount: int = 4) -> dict:
        """Generate counts for each species."""
        if totalIndividuals is not None:
            # Randomly distribute total individuals among species
            return self._distributeIndividualsRandomly(speciesNames, totalIndividuals)
        elif individualsPerSpecies is not None:
            # Use fixed count for all species
            return {species: individualsPerSpecies for species in speciesNames}
        else:
            # Use random counts within range
            return {species: random.randint(minCount, maxCount) for species in speciesNames}
    
    def _distributeIndividualsRandomly(self, speciesNames: list, totalIndividuals: int) -> dict:
        """Randomly distribute total individuals among species, ensuring each species gets at least 1."""
        numSpecies = len(speciesNames)
        
        if totalIndividuals < numSpecies:
            raise ValueError(f"Total individuals ({totalIndividuals}) must be at least equal to number of species ({numSpecies})")
        
        # Start by giving each species 1 individual
        distribution = {species: 1 for species in speciesNames}
        remaining = totalIndividuals - numSpecies
        
        # Randomly distribute the remaining individuals
        for _ in range(remaining):
            species = random.choice(speciesNames)
            distribution[species] += 1
        
        return distribution
    
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
    
    def generateConstraints(self, speciesNames: list, numConstraints: int, allowHigherArity: bool = True) -> list:
        """Generate random constraints that involve ALL species in the problem."""
        if numConstraints == 0:
            return []
        
        constraints = []
        usedCombinations = set()
        
        numSpecies = len(speciesNames)
        if numSpecies < 2:
            return []  # Need at least 2 species for constraints
        
        for _ in range(numConstraints):
            attempts = 0
            while attempts < 50:  # Prevent infinite loop
                # Generate constraint that involves all species
                constraint, combination = self._generateAllSpeciesConstraint(speciesNames)
                
                # Check if this combination hasn't been used
                if combination not in usedCombinations and constraint:
                    constraints.append(constraint)
                    usedCombinations.add(combination)
                    break
                
                attempts += 1
            
            if attempts >= 50:
                print(f"Warning: Could only generate {len(constraints)} constraints instead of {numConstraints}")
                break
        
        return constraints
    
    def _generateAllSpeciesConstraint(self, speciesNames: list) -> tuple:
        """Generate a constraint that involves ALL species in the problem."""
        if len(speciesNames) < 2:
            return None, None
        
        # Randomly divide species into two groups: protected and threatening
        # Ensure both groups have at least one species
        shuffledSpecies = speciesNames.copy()
        random.shuffle(shuffledSpecies)
        
        # Split roughly in half, but ensure both groups have at least 1 species
        splitPoint = max(1, min(len(shuffledSpecies) - 1, len(shuffledSpecies) // 2))
        
        # Randomly decide which group is larger
        if random.choice([True, False]):
            protectedSpecies = shuffledSpecies[:splitPoint]
            threateningSpecies = shuffledSpecies[splitPoint:]
        else:
            protectedSpecies = shuffledSpecies[splitPoint:]
            threateningSpecies = shuffledSpecies[:splitPoint]
        
        # Format species groups for natural language
        def formatSpeciesList(speciesList):
            if len(speciesList) == 1:
                return speciesList[0]
            elif len(speciesList) == 2:
                return f"{speciesList[0]} and {speciesList[1]}"
            else:
                return ", ".join(speciesList[:-1]) + f", and {speciesList[-1]}"
        
        protectedGroup = formatSpeciesList(protectedSpecies)
        threateningGroup = formatSpeciesList(threateningSpecies)
        
        # Choose a random template
        template = random.choice(self.allSpeciesConstraints)
        
        # Generate the constraint
        constraint = template.format(
            protectedGroup=protectedGroup,
            threateningGroup=threateningGroup
        )
        
        # Create combination key that includes the specific grouping for uniqueness
        # This allows multiple constraints involving all species but with different groupings
        combination = (tuple(sorted(protectedSpecies)), tuple(sorted(threateningSpecies)), template)
        
        return constraint, combination
    
    def generateProblem(self, numSpecies: int, numConstraints: int, 
                       totalIndividuals: int = None, individualsPerSpecies: int = None, 
                       minCount: int = 1, maxCount: int = 4, capacity: int = None, 
                       capacityMode: str = "auto", allowHigherArity: bool = True) -> tuple:
        """Generate a complete random transportation problem. Returns (problemText, actualTotalIndividuals)."""
        # Generate species
        speciesNames = self.generateSpeciesNames(numSpecies)
        speciesCounts = self.generateSpeciesCounts(speciesNames, totalIndividuals, 
                                                  individualsPerSpecies, minCount, maxCount)
        
        # Calculate total individuals and shuttle capacity
        actualTotalIndividuals = sum(speciesCounts.values())
        if capacity is not None:
            shuttleCapacity = capacity
        else:
            shuttleCapacity = self.generateShuttleCapacity(actualTotalIndividuals, capacityMode)
        
        # Generate constraints
        constraints = self.generateConstraints(speciesNames, numConstraints, allowHigherArity)
        
        # Build the problem description
        problemLines = [
            f"A shuttle with capacity {shuttleCapacity} must transport a group of species from the start to the target bank. The shuttle can cross empty from one bank to another."
        ]
        
        # Add species
        for species, count in speciesCounts.items():
            problemLines.append(f"  - {species}: {count} individual(s)")
        
        # Add constraints
        for constraint in constraints:
            problemLines.append(f"* {constraint}.")
        
        return '\n'.join(problemLines), actualTotalIndividuals


def solveRandomProblem(numSpecies: int, numConstraints: int = 1, totalIndividuals: int = None,
                      individualsPerSpecies: int = None, minCount: int = 1, maxCount: int = 4, 
                      capacity: int = None, capacityMode: str = "auto", showCode: bool = False, 
                      seed: int = None, findAllSolutions: bool = False, maxSteps: int = 100, 
                      saveOnly: bool = False, allowHigherArity: bool = True):
    """Generate and solve a random transportation problem."""
    if seed is not None:
        random.seed(seed)
        print(f"🎲 Using random seed: {seed}")
    
    print("🎯 Enhanced Random Transportation Problem Generator")
    print("=" * 60)
    
    if totalIndividuals is not None:
        if capacity is not None:
            print(f"Generating problem with {numSpecies} species, {totalIndividuals} total individuals (randomly distributed), capacity {capacity}, and {numConstraints} constraints...")
        else:
            print(f"Generating problem with {numSpecies} species, {totalIndividuals} total individuals (randomly distributed), and {numConstraints} constraints...")
    elif individualsPerSpecies is not None:
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
        problemText, actualTotalIndividuals = generator.generateProblem(numSpecies, numConstraints, totalIndividuals,
                                               individualsPerSpecies, minCount, maxCount, 
                                               capacity, capacityMode, allowHigherArity)
        
        print("📋 GENERATED PROBLEM:")
        print("=" * 60)
        print(problemText)
        print()
        
        # Extract shuttle capacity from the problem text
        import re
        capacityMatch = re.search(r'capacity\s+(\d+)', problemText.lower())
        extractedCapacity = int(capacityMatch.group(1)) if capacityMatch else capacity or 2
        
        # Save problem to numbered file
        savedFilename = saveProblemToFile(problemText, numSpecies, actualTotalIndividuals, extractedCapacity)
        if savedFilename:
            print(f"💾 Problem saved to: {savedFilename}")
        print()
        
        # Skip solving if saveOnly is True
        if saveOnly:
            print("🔄 Problem generation complete (skipping solve as requested)")
            return problemText, None
        
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
  python generateRandomProblems.py --species 3 --constraints 2 --total-individuals 12
  python generateRandomProblems.py --species 4 --constraints 3 --total-individuals 15 --capacity 3 --show-code
  python generateRandomProblems.py --species 3 --constraints 1 --individuals 2 --capacity 2
  python generateRandomProblems.py --batch 10 --individuals 2 --capacity 1
  python generateRandomProblems.py --species 3 --constraints 2 --total-individuals 9 --seed 42
  python generateRandomProblems.py --species 3 --constraints 1 --min-count 1 --max-count 3 --capacity 2
  python generateRandomProblems.py --species 3 --constraints 1 --total-individuals 8 --save-only
  python generateRandomProblems.py --species 5 --constraints 2 --total-individuals 20 --higher-arity
  python generateRandomProblems.py --species 4 --constraints 3 --total-individuals 12 --binary-only
        """
    )
    
    parser.add_argument('--species', '-s', type=int, default=3,
                       help='Number of species to generate (default: 3)')
    parser.add_argument('--constraints', '-c', type=int, default=1,
                       help='Number of constraints to generate (default: 1)')
    parser.add_argument('--total-individuals', type=int,
                       help='Total number of individuals to distribute randomly among species')
    parser.add_argument('--individuals', '-i', type=int,
                       help='Fixed number of individuals per species (overrides min/max-count and total-individuals)')
    parser.add_argument('--min-count', type=int, default=1,
                       help='Minimum individuals per species when --individuals and --total-individuals not specified (default: 1)')
    parser.add_argument('--max-count', type=int, default=4,
                       help='Maximum individuals per species when --individuals and --total-individuals not specified (default: 4)')
    parser.add_argument('--capacity', '-cap', type=int, default=2,
                       help='Fixed shuttle capacity (default: 2, overrides capacity-mode)')
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
    parser.add_argument('--save-only', action='store_true',
                       help='Only generate and save the problem, skip solving')
    parser.add_argument('--higher-arity', action='store_true', default=True,
                       help='Enable higher-arity constraints (3-arity, 4-arity, etc.) (default: True)')
    parser.add_argument('--binary-only', action='store_true',
                       help='Generate only binary (2-arity) constraints')
    
    args = parser.parse_args()
    
    if args.batch:
        batchTest(args.batch, individualsPerSpecies=args.individuals, 
                  capacity=args.capacity, findAllSolutions=args.all_solutions, maxSteps=args.max_steps)
    else:
        # Determine if higher arity should be allowed
        allowHigherArity = args.higher_arity and not args.binary_only
        
        solveRandomProblem(
            args.species, 
            args.constraints,
            args.total_individuals,
            args.individuals,
            args.min_count,
            args.max_count,
            args.capacity,
            args.capacity_mode,
            args.show_code,
            args.seed,
            args.all_solutions,
            args.max_steps,
            args.save_only,
            allowHigherArity
        )


if __name__ == "__main__":
    main() 