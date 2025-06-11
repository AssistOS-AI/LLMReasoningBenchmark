#!/usr/bin/env python3
"""
Solution Verifier for Transportation Problems
Verifies if a given solution in natural language format is correct.
"""

import re
import argparse
from typing import Dict, List, Tuple, Optional
from nlToZ3 import NLToZ3Converter, ProblemMetrics


class SolutionVerifier:
    def __init__(self):
        self.converter = NLToZ3Converter()
    
    def showProblemDifficulty(self, problemText: str) -> None:
        """Show difficulty analysis for the problem."""
        analysis = ProblemMetrics.calculateOverallDifficulty(self.converter.parseProblem(problemText))
        
        print("📊 PROBLEM DIFFICULTY ANALYSIS")
        print("=" * 50)
        print(f"Overall Difficulty: {analysis['overallDifficulty']} ({analysis['difficultyCategory']})")
        print(f"Complication: {analysis['complication']} | Complexity: {analysis['complexity']}")
        print(f"Species: {analysis['speciesCount']} | Individuals: {analysis['totalIndividuals']} | Capacity: {analysis['shuttleCapacity']}")
        if analysis['constraintCount'] > 0:
            breakdown = analysis['complexityBreakdown']
            constraintInfo = []
            if breakdown.get('binaryRelations', 0) > 0:
                constraintInfo.append(f"{breakdown['binaryRelations']} binary")
            if breakdown.get('ternaryRelations', 0) > 0:
                constraintInfo.append(f"{breakdown['ternaryRelations']} ternary")
            if breakdown.get('higherArity', 0) > 0:
                constraintInfo.append(f"{breakdown['higherArity']} higher-arity")
            print(f"Constraints: {analysis['constraintCount']} ({', '.join(constraintInfo)})")
        else:
            print("Constraints: None (unconstrained)")
        print()
    
    def parseSolutionStep(self, stepText: str) -> Tuple[Dict[str, int], str]:
        """
        Parse a solution step in format: "move 1 x 2 y left -> right"
        Returns tuple of (species moves dict, direction)
        direction is either 'leftToRight' or 'rightToLeft'
        """
        stepText = stepText.strip().lower()
        
        # Determine direction
        direction = 'leftToRight'  # default
        if re.search(r'right\s*->\s*left|right\s+to\s+left|to\s+start', stepText):
            direction = 'rightToLeft'
        
        # Remove "move" and direction indicators (support both old and new formats)
        stepText = re.sub(r'^move\s+', '', stepText)
        stepText = re.sub(r'\s+(left\s*->\s*right|left\s+to\s+right|right\s*->\s*left|right\s+to\s+left|to\s+target|to\s+start).*$', '', stepText)
        
        moves = {}
        
        # Find all patterns like "1 x", "2 y", "3 species_name" or "1x", "2y" (backward compatibility)
        movePattern = r'(\d+)\s*([a-zA-Z_]+)'
        matches = re.findall(movePattern, stepText)
        
        for count, species in matches:
            moves[species] = int(count)
        
        return moves, direction
    
    def parseSolution(self, solutionText: str) -> List[Tuple[Dict[str, int], str]]:
        """
        Parse complete solution text into list of (moves, direction) tuples per step.
        Expected format (new):
        move 1 x 2 y left -> right
        move 3 z right -> left
        
        Also supports old format:
        Step 1: move 1 x 2 y left to right
        Step 2: move 3 z right to left
        """
        steps = []
        lines = solutionText.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for old format with "Step X:"
            stepMatch = re.match(r'step\s+(\d+):\s*(.+)', line, re.IGNORECASE)
            if stepMatch:
                stepNum = int(stepMatch.group(1))
                stepText = stepMatch.group(2)
                moves, direction = self.parseSolutionStep(stepText)
                
                # Ensure we have the right number of steps
                while len(steps) < stepNum:
                    steps.append(({}, 'leftToRight'))
                
                steps[stepNum - 1] = (moves, direction)
            else:
                # New format - each line is a move command
                if line.lower().startswith('move '):
                    moves, direction = self.parseSolutionStep(line)
                    steps.append((moves, direction))
        
        return steps
    
    def verifySolution(self, problemText: str, solutionText: str) -> Tuple[bool, str]:
        """
        Verify if the given solution is correct for the problem.
        Returns (isValid, message)
        """
        try:
            # Parse the problem
            parsedProblem = self.converter.parseProblem(problemText)
            if not parsedProblem['species']:
                return False, "Error: Could not parse problem - no species found"
            
            # Parse the solution
            solutionSteps = self.parseSolution(solutionText)
            if not solutionSteps:
                return False, "Error: Could not parse solution - no steps found"
            
            # Initialize state tracking
            speciesNames = list(parsedProblem['species'].keys())
            capacity = parsedProblem['shuttle_capacity']
            
            # Start state: all on start bank, none on target bank
            startBank = dict(parsedProblem['species'])
            targetBank = {species: 0 for species in speciesNames}
            
            print(f"🔍 Verifying solution with {len(solutionSteps)} steps...")
            print(f"Initial state - Start: {startBank}, Target: {targetBank}")
            
            # Verify each step
            for stepNum, (moves, direction) in enumerate(solutionSteps, 1):
                print(f"\nStep {stepNum}: {moves} ({direction})")
                
                # Check capacity constraint
                totalMoves = sum(moves.values())
                if totalMoves > capacity:
                    return False, f"Step {stepNum}: Capacity violation - moving {totalMoves} individuals, capacity is {capacity}"
                
                if totalMoves == 0:
                    return False, f"Step {stepNum}: No moves specified"
                
                # Determine source and destination banks based on direction
                if direction == 'leftToRight':
                    sourceBank = startBank
                    destBank = targetBank
                    sourceName = "start"
                else:  # rightToLeft
                    sourceBank = targetBank
                    destBank = startBank
                    sourceName = "target"
                
                # Check availability constraint  
                for species, count in moves.items():
                    if species not in speciesNames:
                        return False, f"Step {stepNum}: Unknown species '{species}'"
                    
                    if count < 0:
                        return False, f"Step {stepNum}: Invalid negative count for {species}"
                    
                    if sourceBank[species] < count:
                        return False, f"Step {stepNum}: Insufficient {species} on {sourceName} bank - trying to move {count}, only {sourceBank[species]} available"
                
                # Apply the moves
                for species, count in moves.items():
                    sourceBank[species] -= count
                    destBank[species] += count
                
                # Check safety constraints after the move
                for constraint in parsedProblem['constraints']:
                    if constraint['type'] == 'not_outnumbered':
                        protected = constraint['protected']
                        threatening = constraint['threatening']
                        
                        # Check start bank safety
                        if startBank[protected] > 0 and startBank[protected] < startBank[threatening]:
                            return False, f"Step {stepNum}: Safety violation on start bank - {protected} ({startBank[protected]}) outnumbered by {threatening} ({startBank[threatening]})"
                        
                        # Check target bank safety  
                        if targetBank[protected] > 0 and targetBank[protected] < targetBank[threatening]:
                            return False, f"Step {stepNum}: Safety violation on target bank - {protected} ({targetBank[protected]}) outnumbered by {threatening} ({targetBank[threatening]})"
                
                print(f"  After step - Start: {startBank}, Target: {targetBank}")
            
            # Check if all individuals reached target
            for species, count in parsedProblem['species'].items():
                if targetBank[species] != count:
                    return False, f"Final state: {species} not fully transported - expected {count}, got {targetBank[species]} on target bank"
                
                if startBank[species] != 0:
                    return False, f"Final state: {species} still on start bank - {startBank[species]} remaining"
            
            return True, f"✅ Solution is VALID! Successfully transported all species in {len(solutionSteps)} steps."
            
        except Exception as e:
            return False, f"Error during verification: {str(e)}"
    
    def formatSolutionAsNaturalLanguage(self, solution: List[Tuple[Dict[str, int], str]]) -> str:
        """
        Convert solution from internal format to natural language format.
        Input: [({'species1': 2, 'species2': 1}, 'leftToRight'), ({'species3': 1}, 'rightToLeft')]
        Output: "move 2 species1 1 species2 left -> right\nmove 1 species3 right -> left"
        """
        if not solution:
            return "No solution steps"
        
        solutionLines = []
        for stepNum, (moves, direction) in enumerate(solution, 1):
            if not moves:
                continue
                
            moveItems = []
            for species, count in moves.items():
                moveItems.append(f"{count} {species}")
            
            moveText = " ".join(moveItems)
            directionText = "left -> right" if direction == 'leftToRight' else "right -> left"
            solutionLines.append(f"move {moveText} {directionText}")
        
        return "\n".join(solutionLines)


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Verify Transportation Problem Solutions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify a solution from files
  python verifySolution.py --problem problem.txt --solution solution.txt
  
  # Verify inline
  python verifySolution.py --problem "A shuttle with capacity 2 must transport species. - cats: 2 individual(s) - dogs: 1 individual(s)" --solution "Step 1: move 2cats 1dogs left to right"
  
  # Interactive mode
  python verifySolution.py --interactive
        """
    )
    
    parser.add_argument('--problem', type=str, help='Problem description or file path')
    parser.add_argument('--solution', type=str, help='Solution description or file path') 
    parser.add_argument('--interactive', action='store_true', help='Interactive verification mode')
    
    args = parser.parse_args()
    
    verifier = SolutionVerifier()
    
    if args.interactive:
        print("🔍 Interactive Solution Verifier")
        print("=" * 50)
        
        while True:
            print("\nEnter problem description (or 'quit' to exit):")
            problemText = input().strip()
            
            if problemText.lower() in ['quit', 'exit', 'q']:
                break
            
            print("\nEnter solution (multiple lines, end with empty line):")
            solutionLines = []
            while True:
                line = input().strip()
                if not line:
                    break
                solutionLines.append(line)
            
            solutionText = "\n".join(solutionLines)
            
            if not solutionText:
                print("❌ No solution provided")
                continue
            
            isValid, message = verifier.verifySolution(problemText, solutionText)
            print(f"\n{message}")
            
    elif args.problem and args.solution:
        # Read from files if they exist, otherwise treat as direct text
        try:
            with open(args.problem, 'r') as f:
                problemText = f.read()
        except FileNotFoundError:
            problemText = args.problem
        
        try:
            with open(args.solution, 'r') as f:
                solutionText = f.read()
        except FileNotFoundError:
            solutionText = args.solution
        
        print("🔍 Solution Verifier")
        print("=" * 50)
        print("PROBLEM:")
        print(problemText)
        print("\nSOLUTION:")
        print(solutionText)
        print()
        
        # Show difficulty analysis
        verifier.showProblemDifficulty(problemText)
        
        print("VERIFICATION:")
        print("-" * 30)
        
        isValid, message = verifier.verifySolution(problemText, solutionText)
        print(message)
        
        if isValid:
            exit(0)
        else:
            exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 