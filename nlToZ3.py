#!/usr/bin/env python3
"""
Natural Language to Z3 Constraint Converter
"""

import re
import math
from z3 import Int, Solver, And, Or, Not, sat
from typing import Dict, List, Tuple, Optional


class ProblemMetrics:
    """
    Calculate metrics for transportation problem difficulty.
    
    Complication: Combines number of species, individuals per species, and shuttle capacity
    Complexity: Based on n-arity of relations in constraints
    """
    
    @staticmethod
    def calculateComplication(parsedData: Dict) -> float:
        """
        Calculate complication metric that combines:
        - Number of species (more species = more complex, linear growth)
        - Total individuals (more individuals = more complex) 
        - Shuttle capacity constraint (smaller capacity relative to total = more complex)
        
        Returns a float representing problem complication.
        Uses linear/polynomial scaling instead of logarithmic to better reflect
        exponential growth in state space complexity.
        """
        species = parsedData['species']
        capacity = parsedData['shuttle_capacity']
        
        if not species or capacity <= 0:
            return 0.0
        
        # Basic factors
        numSpecies = len(species)
        totalIndividuals = sum(species.values())
        
        # Species complexity: linear growth (species interactions grow quadratically)
        # Use numSpecies^1.2 to account for interaction complexity
        speciesComplexity = numSpecies ** 1.2
        
        # Individual complexity: total count
        individualComplexity = totalIndividuals
        
        # Capacity constraint: ratio of total individuals to capacity
        # Use square root to balance between linear and exponential growth
        # More steps = exponentially more possibilities, but sqrt dampens extreme cases
        capacityRatio = totalIndividuals / capacity
        capacityComplexity = capacityRatio ** 0.8
        
        # Combined complication metric
        complication = speciesComplexity * individualComplexity * capacityComplexity / 10
        
        return round(complication, 2)
    
    @staticmethod
    def calculateComplexity(parsedData: Dict) -> Tuple[float, Dict]:
        """
        Calculate complexity metric based on n-arity of constraint relations.
        
        Returns tuple of (overallComplexity, breakdownDict)
        """
        constraints = parsedData['constraints']
        
        if not constraints:
            return 0.0, {"noConstraints": True}
        
        # Analyze constraint types and their n-arity
        constraintAnalysis = {
            'binaryRelations': 0,      # 2-arity (A op B)
            'ternaryRelations': 0,     # 3-arity (A op B op C)  
            'higherArity': 0,          # 4+ arity
            'constraintTypes': {},
            'totalConstraints': len(constraints)
        }
        
        totalComplexity = 0.0
        
        for constraint in constraints:
            constraintType = constraint.get('type', 'unknown')
            constraintAnalysis['constraintTypes'][constraintType] = constraintAnalysis['constraintTypes'].get(constraintType, 0) + 1
            
            if constraintType == 'not_outnumbered':
                # Binary relation: protected species vs threatening species
                constraintAnalysis['binaryRelations'] += 1
                totalComplexity += 1.0  # Base complexity for binary relation
                
            elif constraintType == 'ternaryConstraint':
                # Hypothetical 3-arity constraint (A + B vs C)
                constraintAnalysis['ternaryRelations'] += 1
                totalComplexity += 2.0  # Higher complexity for ternary
                
            elif constraintType == 'higherArityConstraint':
                # Hypothetical 4+ arity constraint
                constraintAnalysis['higherArity'] += 1
                totalComplexity += 3.0  # Even higher complexity
                
            else:
                # Unknown constraint type, assume binary
                constraintAnalysis['binaryRelations'] += 1
                totalComplexity += 1.0
        
        # Apply scaling factor based on constraint interaction
        # More constraints can interact in complex ways
        if len(constraints) > 1:
            interactionFactor = 1 + (len(constraints) - 1) * 0.2  # 20% increase per additional constraint
            totalComplexity *= interactionFactor
        
        constraintAnalysis['interactionFactor'] = interactionFactor if len(constraints) > 1 else 1.0
        
        return round(totalComplexity, 2), constraintAnalysis
    
    @staticmethod
    def calculateOverallDifficulty(parsedData: Dict) -> Dict:
        """
        Calculate overall problem difficulty combining complication and complexity.
        
        Returns comprehensive difficulty analysis.
        """
        complication = ProblemMetrics.calculateComplication(parsedData)
        complexity, complexityBreakdown = ProblemMetrics.calculateComplexity(parsedData)
        
        # Combined difficulty score
        # Complication represents the "size" of the problem
        # Complexity represents the "logical difficulty" of constraints
        overallDifficulty = complication * (1 + complexity / 10)  # Complexity as multiplier
        
        # Difficulty categories
        if overallDifficulty < 10:
            category = "Trivial"
        elif overallDifficulty < 50:
            category = "Easy"
        elif overallDifficulty < 200:
            category = "Medium"
        elif overallDifficulty < 500:
            category = "Hard"
        else:
            category = "Very Hard"
        
        return {
            'complication': complication,
            'complexity': complexity,
            'complexityBreakdown': complexityBreakdown,
            'overallDifficulty': round(overallDifficulty, 2),
            'difficultyCategory': category,
            'speciesCount': len(parsedData['species']),
            'totalIndividuals': sum(parsedData['species'].values()),
            'shuttleCapacity': parsedData['shuttle_capacity'],
            'constraintCount': len(parsedData['constraints'])
        }


class NLToZ3Converter:
    def __init__(self):
        self.speciesCounts = {}
        self.shuttleCapacity = 0
        self.constraints = []
        
    def parseProblem(self, problemText: str) -> Dict:
        """Parse natural language problem description."""
        lines = [line.strip() for line in problemText.strip().split('\n') if line.strip()]
        
        result = {
            'shuttle_capacity': 0,
            'species': {},
            'constraints': []
        }
        
        for line in lines:
            # Parse shuttle capacity
            capacityMatch = re.search(r'capacity\s+(\d+)', line.lower())
            if capacityMatch:
                result['shuttle_capacity'] = int(capacityMatch.group(1))
                continue
            
            # Parse species counts (e.g., "- vwpmy: 2 individual(s)")
            speciesMatch = re.search(r'-\s*([a-zA-Z_]+):\s*(\d+)\s*individual', line)
            if speciesMatch:
                speciesName = speciesMatch.group(1)
                count = int(speciesMatch.group(2))
                result['species'][speciesName] = count
                continue
            
            # Parse constraints (e.g., "* On either bank, if vwpmy are present, they must not be outnumbered by uiatu.")
            if line.startswith('*') or 'must not be outnumbered' in line.lower():
                constraintMatch = re.search(r'if\s+([a-zA-Z_]+).*outnumbered.*by\s+([a-zA-Z_]+)', line)
                if constraintMatch:
                    protectedSpecies = constraintMatch.group(1)
                    threateningSpecies = constraintMatch.group(2)
                    result['constraints'].append({
                        'type': 'not_outnumbered',
                        'protected': protectedSpecies,
                        'threatening': threateningSpecies
                    })
        
        return result
    
    def analyzeProblemDifficulty(self, problemText: str) -> Dict:
        """
        Analyze the difficulty of a transportation problem.
        
        Returns comprehensive difficulty metrics including complication and complexity.
        """
        parsedData = self.parseProblem(problemText)
        return ProblemMetrics.calculateOverallDifficulty(parsedData)
    
    def printDifficultyAnalysis(self, problemText: str) -> None:
        """
        Print a detailed difficulty analysis of the problem.
        """
        analysis = self.analyzeProblemDifficulty(problemText)
        
        print("📊 PROBLEM DIFFICULTY ANALYSIS")
        print("=" * 50)
        print(f"Overall Difficulty: {analysis['overallDifficulty']} ({analysis['difficultyCategory']})")
        print()
        
        print("🔧 COMPLICATION METRICS:")
        print(f"  • Complication Score: {analysis['complication']}")
        print(f"  • Species Count: {analysis['speciesCount']}")
        print(f"  • Total Individuals: {analysis['totalIndividuals']}")
        print(f"  • Shuttle Capacity: {analysis['shuttleCapacity']}")
        print(f"  • Capacity Ratio: {analysis['totalIndividuals']}/{analysis['shuttleCapacity']} = {analysis['totalIndividuals']/analysis['shuttleCapacity']:.1f}")
        print()
        
        print("🧠 COMPLEXITY METRICS:")
        print(f"  • Complexity Score: {analysis['complexity']}")
        print(f"  • Total Constraints: {analysis['constraintCount']}")
        
        breakdown = analysis['complexityBreakdown']
        if breakdown.get('noConstraints'):
            print("  • No constraints (unconstrained problem)")
        else:
            if breakdown.get('binaryRelations', 0) > 0:
                print(f"  • Binary Relations (2-arity): {breakdown['binaryRelations']}")
            if breakdown.get('ternaryRelations', 0) > 0:
                print(f"  • Ternary Relations (3-arity): {breakdown['ternaryRelations']}")
            if breakdown.get('higherArity', 0) > 0:
                print(f"  • Higher-Arity Relations (4+): {breakdown['higherArity']}")
            
            if 'constraintTypes' in breakdown:
                print("  • Constraint Types:")
                for constraintType, count in breakdown['constraintTypes'].items():
                    print(f"    - {constraintType}: {count}")
            
            if breakdown.get('interactionFactor', 1.0) > 1.0:
                print(f"  • Interaction Factor: {breakdown['interactionFactor']:.2f}")
        print()
    
    def solveMultiStep(self, parsedData: Dict, maxSteps: int = 100, findAllSolutions: bool = False) -> Optional[List[Dict]]:
        """
        Solve the transportation problem by finding the minimum number of steps.
        
        Args:
            parsedData: Parsed problem data
            maxSteps: Maximum number of steps to try (default: 100)
            findAllSolutions: If True, find all optimal solutions instead of just the first one
        
        Returns:
            Solution as list of step dictionaries, or None if no solution found
        """
        if findAllSolutions:
            return self.findAllSolutions(parsedData, maxSteps)
        
        speciesNames = list(parsedData['species'].keys())
        capacity = parsedData['shuttle_capacity']
        
        # Try to find a solution with increasing number of steps
        for numSteps in range(1, maxSteps + 1):
            print(f"Trying {numSteps}-step solution...")
            
            s = Solver()
            
            # Variables for each step and each bank
            startVars = {}  # startVars[step][species]
            targetVars = {}  # targetVars[step][species]
            shuttleVars = {}  # shuttleVars[step][species]
            
            for step in range(numSteps + 1):  # +1 for final state
                startVars[step] = {}
                targetVars[step] = {}
                if step < numSteps:
                    shuttleVars[step] = {}
                
                for species in speciesNames:
                    startVars[step][species] = Int(f"{species}_start_{step}")
                    targetVars[step][species] = Int(f"{species}_target_{step}")
                    if step < numSteps:
                        shuttleVars[step][species] = Int(f"shuttle_{species}_{step}")
            
            # Initial state
            for species, count in parsedData['species'].items():
                s.add(startVars[0][species] == count)
                s.add(targetVars[0][species] == 0)
            
            # Goal state
            for species, count in parsedData['species'].items():
                s.add(targetVars[numSteps][species] == count)
                s.add(startVars[numSteps][species] == 0)
            
            # Step transitions and constraints
            for step in range(numSteps):
                # Shuttle capacity constraint
                shuttleSum = sum(shuttleVars[step][species] for species in speciesNames)
                s.add(shuttleSum <= capacity)
                s.add(shuttleSum > 0)  # At least one individual must move
                
                # Movement constraints
                for species in speciesNames:
                    s.add(shuttleVars[step][species] >= 0)
                    s.add(shuttleVars[step][species] <= startVars[step][species])
                
                # State transitions
                for species in speciesNames:
                    s.add(startVars[step + 1][species] == startVars[step][species] - shuttleVars[step][species])
                    s.add(targetVars[step + 1][species] == targetVars[step][species] + shuttleVars[step][species])
                
                # Safety constraints for this step
                for constraint in parsedData['constraints']:
                    if constraint['type'] == 'not_outnumbered':
                        protected = constraint['protected']
                        threatening = constraint['threatening']
                        
                        # Safety on start bank after movement
                        s.add(Or(startVars[step + 1][protected] == 0, 
                                startVars[step + 1][protected] >= startVars[step + 1][threatening]))
                        
                        # Safety on target bank after movement
                        s.add(Or(targetVars[step + 1][protected] == 0, 
                                targetVars[step + 1][protected] >= targetVars[step + 1][threatening]))
            
            # Check if this step count can solve the problem
            if s.check() == sat:
                print(f"✓ Solution found with {numSteps} steps!")
                model = s.model()
                
                # Extract the solution
                solution = []
                for step in range(numSteps):
                    stepSolution = {}
                    for species in speciesNames:
                        moves = model[shuttleVars[step][species]].as_long()
                        if moves > 0:
                            stepSolution[species] = moves
                    if stepSolution:
                        solution.append(stepSolution)
                
                return solution
            else:
                print(f"✗ No solution with {numSteps} steps")
        
        return None
    
    def findAllSolutions(self, parsedData: Dict, maxSteps: int = 100) -> List[List[Dict]]:
        """Find all solutions with the minimum number of steps."""
        speciesNames = list(parsedData['species'].keys())
        capacity = parsedData['shuttle_capacity']
        
        # First, find the minimum number of steps required for any solution
        minSteps = None
        for numSteps in range(1, maxSteps + 1):
            print(f"Checking if {numSteps}-step solution exists...")
            
            s = Solver()
            
            # Variables for each step and each bank
            startVars = {}  # startVars[step][species]
            targetVars = {}  # targetVars[step][species]
            shuttleVars = {}  # shuttleVars[step][species]
            
            for step in range(numSteps + 1):  # +1 for final state
                startVars[step] = {}
                targetVars[step] = {}
                if step < numSteps:
                    shuttleVars[step] = {}
                
                for species in speciesNames:
                    startVars[step][species] = Int(f"{species}_start_{step}")
                    targetVars[step][species] = Int(f"{species}_target_{step}")
                    if step < numSteps:
                        shuttleVars[step][species] = Int(f"shuttle_{species}_{step}")
            
            # Initial state
            for species, count in parsedData['species'].items():
                s.add(startVars[0][species] == count)
                s.add(targetVars[0][species] == 0)
            
            # Goal state
            for species, count in parsedData['species'].items():
                s.add(targetVars[numSteps][species] == count)
                s.add(startVars[numSteps][species] == 0)
            
            # Step transitions and constraints
            for step in range(numSteps):
                # Shuttle capacity constraint
                shuttleSum = sum(shuttleVars[step][species] for species in speciesNames)
                s.add(shuttleSum <= capacity)
                s.add(shuttleSum > 0)  # At least one individual must move
                
                # Movement constraints
                for species in speciesNames:
                    s.add(shuttleVars[step][species] >= 0)
                    s.add(shuttleVars[step][species] <= startVars[step][species])
                
                # State transitions
                for species in speciesNames:
                    s.add(startVars[step + 1][species] == startVars[step][species] - shuttleVars[step][species])
                    s.add(targetVars[step + 1][species] == targetVars[step][species] + shuttleVars[step][species])
                
                # Safety constraints for this step
                for constraint in parsedData['constraints']:
                    if constraint['type'] == 'not_outnumbered':
                        protected = constraint['protected']
                        threatening = constraint['threatening']
                        
                        # Safety on start bank after movement
                        s.add(Or(startVars[step + 1][protected] == 0, 
                                startVars[step + 1][protected] >= startVars[step + 1][threatening]))
                        
                        # Safety on target bank after movement
                        s.add(Or(targetVars[step + 1][protected] == 0, 
                                targetVars[step + 1][protected] >= targetVars[step + 1][threatening]))
            
            # Check if this step count can solve the problem
            if s.check() == sat:
                minSteps = numSteps
                print(f"✓ Minimum steps required: {numSteps}")
                break
            else:
                print(f"✗ No solution with {numSteps} steps")
        
        if minSteps is None:
            print("❌ No solution found within maximum steps")
            return []
        
        # Now find ALL solutions with the minimum number of steps
        print(f"\n🎯 Finding all optimal solutions with {minSteps} steps...")
        allSolutions = []
        excludeConstraints = []
        
        while True:
            s = Solver()
            
            # Variables for each step and each bank
            startVars = {}  # startVars[step][species]
            targetVars = {}  # targetVars[step][species]
            shuttleVars = {}  # shuttleVars[step][species]
            
            for step in range(minSteps + 1):  # +1 for final state
                startVars[step] = {}
                targetVars[step] = {}
                if step < minSteps:
                    shuttleVars[step] = {}
                
                for species in speciesNames:
                    startVars[step][species] = Int(f"{species}_start_{step}")
                    targetVars[step][species] = Int(f"{species}_target_{step}")
                    if step < minSteps:
                        shuttleVars[step][species] = Int(f"shuttle_{species}_{step}")
            
            # Initial state
            for species, count in parsedData['species'].items():
                s.add(startVars[0][species] == count)
                s.add(targetVars[0][species] == 0)
            
            # Goal state
            for species, count in parsedData['species'].items():
                s.add(targetVars[minSteps][species] == count)
                s.add(startVars[minSteps][species] == 0)
            
            # Step transitions and constraints
            for step in range(minSteps):
                # Shuttle capacity constraint
                shuttleSum = sum(shuttleVars[step][species] for species in speciesNames)
                s.add(shuttleSum <= capacity)
                s.add(shuttleSum > 0)  # At least one individual must move
                
                # Movement constraints
                for species in speciesNames:
                    s.add(shuttleVars[step][species] >= 0)
                    s.add(shuttleVars[step][species] <= startVars[step][species])
                
                # State transitions
                for species in speciesNames:
                    s.add(startVars[step + 1][species] == startVars[step][species] - shuttleVars[step][species])
                    s.add(targetVars[step + 1][species] == targetVars[step][species] + shuttleVars[step][species])
                
                # Safety constraints for this step
                for constraint in parsedData['constraints']:
                    if constraint['type'] == 'not_outnumbered':
                        protected = constraint['protected']
                        threatening = constraint['threatening']
                        
                        # Safety on start bank after movement
                        s.add(Or(startVars[step + 1][protected] == 0, 
                                startVars[step + 1][protected] >= startVars[step + 1][threatening]))
                        
                        # Safety on target bank after movement
                        s.add(Or(targetVars[step + 1][protected] == 0, 
                                targetVars[step + 1][protected] >= targetVars[step + 1][threatening]))
            
            # Add constraints to exclude previously found solutions
            for excludeConstraint in excludeConstraints:
                s.add(Not(excludeConstraint))
            
            # Check if we can find another solution
            if s.check() == sat:
                model = s.model()
                
                # Extract the solution
                solution = []
                solutionConstraint = []
                
                for step in range(minSteps):
                    stepSolution = {}
                    stepConstraints = []
                    
                    for species in speciesNames:
                        moves = model[shuttleVars[step][species]].as_long()
                        if moves > 0:
                            stepSolution[species] = moves
                        # Create constraint for this exact move
                        stepConstraints.append(shuttleVars[step][species] == moves)
                    
                    if stepSolution:
                        solution.append(stepSolution)
                    
                    # Combine all step constraints for this solution
                    solutionConstraint.extend(stepConstraints)
                
                # Add this solution to the list
                allSolutions.append(solution)
                print(f"  Found optimal solution #{len(allSolutions)}: {solution}")
                
                # Create exclusion constraint for this exact solution
                if solutionConstraint:
                    excludeConstraints.append(And(solutionConstraint))
                
                # Continue searching for more solutions
            else:
                # No more solutions with minimum steps
                break
        
        print(f"✓ Found {len(allSolutions)} optimal solutions with {minSteps} steps!")
        return allSolutions
    
    def generateZ3CodeTemplate(self, parsedData: Dict) -> str:
        """Generate a template Z3 code for the problem."""
        speciesNames = list(parsedData['species'].keys())
        capacity = parsedData['shuttle_capacity']
        
        codeLines = [
            "# Generated Z3 Template for Transportation Problem",
            "from z3 import Int, Solver, And, Or, Not, sat",
            "",
            "def solveTransportationProblem():",
            "    \"\"\"Solve the transportation problem step by step.\"\"\"",
            "    # Problem parameters"
        ]
        
        # Add problem parameters
        codeLines.append(f"    shuttleCapacity = {capacity}")
        for species, count in parsedData['species'].items():
            codeLines.append(f"    {species}Count = {count}")
        
        codeLines.extend([
            "",
            "    # Species list",
            f"    species = {speciesNames}",
            f"    speciesCounts = {dict(parsedData['species'])}",
            "",
            "    # Multi-step solver",
            "    maxSteps = 5",
            "    ",
            "    for numSteps in range(1, maxSteps + 1):",
            "        print(f'Trying {numSteps}-step solution...')",
            "        s = Solver()",
            "",
            "        # Variables for each step",
            "        startVars = {}",
            "        targetVars = {}",
            "        shuttleVars = {}",
            "",
            "        for step in range(numSteps + 1):",
            "            startVars[step] = {}",
            "            targetVars[step] = {}",
            "            if step < numSteps:",
            "                shuttleVars[step] = {}",
            "",
            "            for species in species:",
            "                startVars[step][species] = Int(f'{species}_start_{step}')",
            "                targetVars[step][species] = Int(f'{species}_target_{step}')",
            "                if step < numSteps:",
            "                    shuttleVars[step][species] = Int(f'shuttle_{species}_{step}')",
            "",
            "        # Initial state",
            "        for species, count in speciesCounts.items():",
            "            s.add(startVars[0][species] == count)",
            "            s.add(targetVars[0][species] == 0)",
            "",
            "        # Goal state",  
            "        for species, count in speciesCounts.items():",
            "            s.add(targetVars[numSteps][species] == count)",
            "            s.add(startVars[numSteps][species] == 0)",
            "",
            "        # Step constraints",
            "        for step in range(numSteps):",
            "            # Capacity constraint",
            "            shuttleSum = sum(shuttleVars[step][species] for species in species)",
            "            s.add(shuttleSum <= shuttleCapacity)",
            "            s.add(shuttleSum > 0)",
            "",
            "            # Movement constraints",
            "            for species in species:",
            "                s.add(shuttleVars[step][species] >= 0)",
            "                s.add(shuttleVars[step][species] <= startVars[step][species])",
            "",
            "            # State transitions",
            "            for species in species:",
            "                s.add(startVars[step + 1][species] == startVars[step][species] - shuttleVars[step][species])",
            "                s.add(targetVars[step + 1][species] == targetVars[step][species] + shuttleVars[step][species])"
        ])
        
        # Add safety constraints if present
        if parsedData['constraints']:
            codeLines.extend([
                "",
                "            # Safety constraints"
            ])
            for constraint in parsedData['constraints']:
                if constraint['type'] == 'not_outnumbered':
                    protected = constraint['protected']
                    threatening = constraint['threatening']
                    codeLines.extend([
                        f"            # {protected} must not be outnumbered by {threatening}",
                        f"            s.add(Or(startVars[step + 1]['{protected}'] == 0,",
                        f"                     startVars[step + 1]['{protected}'] >= startVars[step + 1]['{threatening}']))",
                        f"            s.add(Or(targetVars[step + 1]['{protected}'] == 0,",
                        f"                     targetVars[step + 1]['{protected}'] >= targetVars[step + 1]['{threatening}']))"
                    ])
        
        codeLines.extend([
            "",
            "        # Check satisfiability",
            "        if s.check() == sat:",
            "            print(f'✓ Solution found with {numSteps} steps!')",
            "            model = s.model()",
            "            ",
            "            # Display solution",
            "            for step in range(numSteps):",
            "                print(f'Step {step + 1}:')",
            "                for species in species:",
            "                    moves = model[shuttleVars[step][species]].as_long()",
            "                    if moves > 0:",
            "                        print(f'  Move {moves} {species}')",
            "                print()",
            "            return True",
            "        else:",
            "            print(f'✗ No solution with {numSteps} steps')",
            "",
            "    print('No solution found within maximum steps')",
            "    return False",
            "",
            "# Run the solver",
            "solveTransportationProblem()"
        ])
        
        return '\n'.join(codeLines)
    
    def formatSolutionAsNaturalLanguage(self, solution: List[Dict[str, int]]) -> str:
        """
        Convert solution from internal format to natural language format.
        Input: [{'species1': 2, 'species2': 1}, {'species3': 1}]
        Output: "Step 1: move 2species1 1species2 left to right\nStep 2: move 1species3 left to right"
        """
        if not solution:
            return "No solution steps"
        
        solutionLines = []
        for stepNum, moves in enumerate(solution, 1):
            if not moves:
                continue
                
            moveItems = []
            for species, count in moves.items():
                moveItems.append(f"{count} {species}")
            
            moveText = " ".join(moveItems)
            solutionLines.append(f"move {moveText} left -> right")
        
        return "\n".join(solutionLines)
    
    def solveProblem(self, problemText: str, findAllSolutions: bool = False, showDifficulty: bool = True, maxSteps: int = 100) -> str:
        """Main method to solve the transportation problem."""
        parsedData = self.parseProblem(problemText)
        
        if not parsedData['species']:
            return "Error: No species found in the problem description."
        
        if parsedData['shuttle_capacity'] == 0:
            return "Error: No shuttle capacity found in the problem description."
        
        print("Parsed problem:")
        print(f"  Shuttle capacity: {parsedData['shuttle_capacity']}")
        print(f"  Species: {parsedData['species']}")
        print(f"  Constraints: {len(parsedData['constraints'])} constraint(s)")
        print(f"  Maximum steps to try: {maxSteps}")
        print()
        
        if showDifficulty:
            self.printDifficultyAnalysis(problemText)
        
        if findAllSolutions:
            # Find all optimal solutions (minimum steps)
            allSolutions = self.solveMultiStep(parsedData, maxSteps=maxSteps, findAllSolutions=True)
            
            if allSolutions:
                minSteps = len(allSolutions[0]) if allSolutions else 0
                print(f"\n🎉 FOUND {len(allSolutions)} OPTIMAL SOLUTIONS!")
                print(f"All solutions use the minimum {minSteps} steps")
                print("=" * 60)
                
                for i, solution in enumerate(allSolutions):
                    print(f"\nOPTIMAL SOLUTION #{i + 1}:")
                    print("-" * 30)
                    for j, step in enumerate(solution):
                        print(f"Step {j + 1}: {step}")
                    
                    # Show natural language format for each solution
                    naturalLanguageSolution = self.formatSolutionAsNaturalLanguage(solution)
                    naturalLanguageCompact = naturalLanguageSolution.replace('\n', '; ')
                    print(f"Natural language: {naturalLanguageCompact}")
                
                print(f"\n📊 SUMMARY:")
                print("=" * 60)
                print(f"Found {len(allSolutions)} optimal solution(s) with {minSteps} steps")
                print("All solutions shown use the minimum number of steps possible")
            else:
                print(f"\n❌ No solutions found within {maxSteps} steps")
        else:
            # Find just the first solution
            solution = self.solveMultiStep(parsedData, maxSteps=maxSteps)
            
            if solution:
                print("\n🎉 SOLUTION FOUND!")
                print("Transportation plan:")
                for i, step in enumerate(solution):
                    print(f"Step {i + 1}: {step}")
                
                # Also show in natural language format
                naturalLanguageSolution = self.formatSolutionAsNaturalLanguage(solution)
                print(f"\n📝 NATURAL LANGUAGE FORMAT:")
                print(naturalLanguageSolution)
            else:
                print(f"\n❌ No solution found within {maxSteps} steps")
        
        # Also return the generated Z3 code template
        return self.generateZ3CodeTemplate(parsedData)


def main():
    """Main function to demonstrate the multi-step converter."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Natural Language to Z3 Transportation Problem Solver")
    parser.add_argument('--all-solutions', action='store_true', 
                       help='Find all optimal solutions (minimum steps) instead of just the first one')
    parser.add_argument('--problem', type=str, 
                       help='Custom problem description (overrides built-in tests)')
    parser.add_argument('--analyze-difficulty', action='store_true',
                       help='Only analyze problem difficulty without solving')
    parser.add_argument('--no-difficulty', action='store_true',
                       help='Skip difficulty analysis during problem solving')
    parser.add_argument('--max-steps', type=int, default=100,
                       help='Maximum number of steps to try when solving (default: 100)')
    
    args = parser.parse_args()
    
    converter = NLToZ3Converter()
    
    if args.problem:
        # Handle custom problem
        if args.analyze_difficulty:
            print("=" * 80)
            print("PROBLEM DIFFICULTY ANALYSIS")
            print("=" * 80)
            print("PROBLEM:")
            print(args.problem)
            print()
            converter.printDifficultyAnalysis(args.problem)
            return
        else:
            # Solve custom problem
            print("=" * 80)
            print("CUSTOM PROBLEM")
            print("=" * 80)
            print("PROBLEM:")
            print(args.problem)
            print("\nSOLVING...")
            print("-" * 50)
            
            z3Code = converter.solveProblem(args.problem, 
                                           findAllSolutions=args.all_solutions,
                                           showDifficulty=not args.no_difficulty,
                                           maxSteps=args.max_steps)
            
            print("\n" + "=" * 80)
            return
    
    # Test cases
    testProblems = [
        {
            "name": "Original Problem (vwpmy vs uiatu)",
            "problem": """
            A shuttle with capacity 2 must transport a group of species from the start to the target bank.
              - vwpmy: 2 individual(s)
              - uiatu: 2 individual(s)
            * On either bank, if vwpmy are present, they must not be outnumbered by uiatu.
            """
        },
        {
            "name": "Classic Farmer Problem", 
            "problem": """
            A shuttle with capacity 2 must transport species.
              - farmer: 1 individual(s)
              - fox: 1 individual(s)
              - chicken: 1 individual(s)
              - grain: 1 individual(s)
            * If farmer is not present, fox must not be with chicken.
            * If farmer is not present, chicken must not be with grain.
            """
        },
        {
            "name": "Simple Transportation",
            "problem": """
            A shuttle with capacity 3 must transport species.
              - cats: 2 individual(s)
              - dogs: 1 individual(s)
            """
        }
    ]
    
    for test in testProblems:
        print("=" * 80)
        print(f"TEST: {test['name']}")
        print("=" * 80)
        print("PROBLEM:")
        print(test['problem'])
        print("\nSOLVING...")
        print("-" * 50)
        
        z3Code = converter.solveProblem(test['problem'], 
                                       findAllSolutions=args.all_solutions,
                                       showDifficulty=not args.no_difficulty,
                                       maxSteps=args.max_steps)
        
        print("\n" + "=" * 80)
        print()


if __name__ == "__main__":
    main() 