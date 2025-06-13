#!/usr/bin/env python3
"""
Transportation Problem Solver
Takes a natural language transportation problem and returns the solution in the required format.
"""

import sys
import argparse
from nlToZ3 import NLToZ3Converter


def solveProblemFromText(problemText: str, quiet: bool = False, maxSteps: int = 100) -> str:
    """
    Solve a transportation problem from natural language text.
    
    Args:
        problemText: The problem description in natural language
        quiet: If True, suppress verbose output and return only the solution
        maxSteps: Maximum number of steps to try when solving (default: 100)
    
    Returns:
        Solution in natural language format, or error message if no solution found
    """
    converter = NLToZ3Converter()
    
    try:
        # Parse the problem
        parsedData = converter.parseProblem(problemText)
        
        if not parsedData['species']:
            return "Error: No species found in the problem description."
        
        if parsedData['shuttle_capacity'] == 0:
            return "Error: No shuttle capacity found in the problem description."
        
        if not quiet:
            print("🔍 Parsing problem...", file=sys.stderr)
            print(f"  Species: {parsedData['species']}", file=sys.stderr)
            print(f"  Capacity: {parsedData['shuttle_capacity']}", file=sys.stderr)
            print(f"  Constraints: {len(parsedData['constraints'])}", file=sys.stderr)
            print(f"  Max steps: {maxSteps}", file=sys.stderr)
            print("🎯 Solving...", file=sys.stderr)
        
        # Solve the problem (find first solution, suppress verbose output if quiet)
        if quiet:
            # Redirect stdout to suppress Z3 solver output
            import io
            import contextlib
            
            stdoutBackup = sys.stdout
            with contextlib.redirect_stdout(io.StringIO()):
                solution = converter.solveMultiStep(parsedData, maxSteps=maxSteps, findAllSolutions=False)
        else:
            solution = converter.solveMultiStep(parsedData, maxSteps=maxSteps, findAllSolutions=False)
        
        if solution:
            # Convert to natural language format
            naturalLanguageSolution = converter.formatSolutionAsNaturalLanguage(solution)
            
            if not quiet:
                print(f"✅ Solution found with {len(solution)} steps!", file=sys.stderr)
            
            return naturalLanguageSolution
        else:
            return f"No solution found within {maxSteps} steps."
            
    except Exception as e:
        return f"Error solving problem: {str(e)}"


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Transportation Problem Solver - Convert natural language problems to solutions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Solve from file
  python solveProblem.py --file problem.txt
  
  # Solve from stdin
  cat problem.txt | python solveProblem.py --stdin
  
  # Solve inline problem
  python solveProblem.py --problem "A shuttle with capacity 2 must transport species. - cats: 2 individual(s) - dogs: 1 individual(s)"
  
  # Quiet mode (only output the solution)
  python solveProblem.py --file problem.txt --quiet
  
  # Limit solving to 50 steps maximum
  python solveProblem.py --file problem.txt --max-steps 50
        """
    )
    
    parser.add_argument('--problem', type=str, help='Problem description as text')
    parser.add_argument('--file', type=str, help='Read problem from file')
    parser.add_argument('--stdin', action='store_true', help='Read problem from stdin')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode - only output the solution')
    parser.add_argument('--max-steps', type=int, default=100, help='Maximum number of steps to try when solving (default: 100)')
    
    args = parser.parse_args()
    
    # Determine input source
    problemText = None
    
    if args.file:
        try:
            with open(args.file, 'r') as f:
                problemText = f.read().strip()
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file '{args.file}': {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.stdin:
        problemText = sys.stdin.read().strip()
    
    elif args.problem:
        problemText = args.problem.strip()
    
    else:
        parser.print_help()
        sys.exit(1)
    
    if not problemText:
        print("Error: No problem text provided.", file=sys.stderr)
        sys.exit(1)
    
    # Clean up the problem text (remove solution format instructions)
    lines = problemText.split('\n')
    cleanedLines = []
    
    for line in lines:
        line = line.strip()
        # Skip lines that are solution format instructions
        if (line.lower().startswith('provide the solution') or 
            line.startswith('move ') and ('kraorn' in line or 'oxyelvox' in line) or
            not line):
            continue
        cleanedLines.append(line)
    
    cleanedProblemText = '\n'.join(cleanedLines)
    
    if not args.quiet:
        print("📋 PROBLEM:", file=sys.stderr)
        print(cleanedProblemText, file=sys.stderr)
        print("", file=sys.stderr)
    
    # Solve the problem
    solution = solveProblemFromText(cleanedProblemText, quiet=args.quiet, maxSteps=args.max_steps)
    
    # Output the solution
    print(solution)
    
    # Exit with error code if no solution found
    if solution.startswith('Error:') or solution.startswith('No solution'):
        sys.exit(1)


if __name__ == "__main__":
    main() 