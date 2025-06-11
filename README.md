# Natural Language to Z3 Transportation Problem Solver

This project converts natural language descriptions of transportation problems into Z3 constraint satisfaction problems and finds optimal solutions.

## Features

- 🧠 **Natural Language Parsing**: Converts English descriptions into Z3 constraints
- 🚀 **Multi-Step Planning**: Automatically finds multi-step solutions when single-step isn't possible
- 🔍 **Constraint Detection**: Handles safety constraints like "must not be outnumbered"
- 🎯 **Optimal Solutions**: Find ALL solutions using the minimum number of steps
- 🛠 **Multiple Interfaces**: Command-line, interactive mode, and programmatic API
- 📊 **Solution Visualization**: Clear step-by-step transportation plans with detailed summaries

## Installation

```bash
# Install Z3 solver
pip install z3-solver

# Clone or download the scripts
# No additional installation needed - pure Python!
```

## Quick Start

### Command Line Usage

```bash
# Generate with fixed individuals per species and shuttle capacity
python generateRandomProblems.py --species 3 --constraints 1 --individuals 2 --capacity 2

# Find ALL optimal solutions for a problem (minimum steps)
python generateRandomProblems.py --species 2 --constraints 1 --individuals 2 --capacity 2 --all-solutions

# Generate with specific parameters and show Z3 code
python generateRandomProblems.py --species 4 --constraints 2 --individuals 3 --capacity 3 --show-code

# Generate with automatic capacity control (when --capacity not specified)
python generateRandomProblems.py --species 3 --constraints 1 --individuals 2 --capacity-mode generous

# Batch test multiple problems with fixed parameters
python generateRandomProblems.py --batch 10 --individuals 2 --capacity 2

# Reproducible generation with seed
python generateRandomProblems.py --species 3 --constraints 1 --individuals 2 --capacity 2 --seed 42

# Use random counts per species (when --individuals not specified)
python generateRandomProblems.py --species 3 --constraints 1 --min-count 1 --max-count 4 --capacity 3
```

### Problem Format

Transportation problems should be described in natural language following this format:

```
A shuttle with capacity [NUMBER] must transport [species/individuals].
  - [species_name]: [count] individual(s)
  - [species_name]: [count] individual(s)
* [Safety constraint description]
```

## Examples

### Example 1: Classic River Crossing Problem
```
A shuttle with capacity 2 must transport a group of species from the start to the target bank.
  - vwpmy: 2 individual(s)
  - uiatu: 2 individual(s)
* On either bank, if vwpmy are present, they must not be outnumbered by uiatu.
```

**Solution:**
```
move 2 uiatu left -> right
move 2 vwpmy left -> right
```

### Example 2: Simple Transportation
```
A shuttle with capacity 3 must transport species.
  - cats: 2 individual(s)
  - dogs: 1 individual(s)
```

**Solution:**
```
move 2 cats 1 dogs left -> right
```

### Example 3: Classic Farmer Problem
```
A shuttle with capacity 2 must transport species.
  - farmer: 1 individual(s)
  - fox: 1 individual(s)
  - chicken: 1 individual(s)
  - grain: 1 individual(s)
* If farmer is not present, fox must not be with chicken.
* If farmer is not present, chicken must not be with grain.
```

## Solution Verification

The `verifySolution.py` script can verify if a given solution is correct:

```bash
# Verify a solution (new format)
python verifySolution.py --problem "A shuttle with capacity 2 must transport species. - cats: 2 individual(s) - dogs: 1 individual(s)" --solution "move 2 cats left -> right\nmove 1 dogs left -> right"

# Interactive mode
python verifySolution.py --interactive

# From files
python verifySolution.py --problem problem.txt --solution solution.txt
```

**Solution Format**: Each step should be on a separate line with spaces between numbers and species names:
```
move 2 cats 1 dogs left -> right
move 1 farmer left -> right
```

The verifier supports both the new format (`left -> right`) and old format (`Step X: ... left to right`) for backward compatibility.

## Files

- `nlToZ3.py` - Core multi-step solver engine with natural language parsing
- `generateRandomProblems.py` - Enhanced random problem generator with configurable individuals per species and shuttle capacity
- `verifySolution.py` - Solution verification script that validates transportation plans
- `requirements.txt` - Python package dependencies
- `README.md` - This documentation file

## API Usage

```python
from nlToZ3 import NLToZ3Converter

# Create solver
converter = NLToZ3Converter()

# Define problem
problem = """
A shuttle with capacity 2 must transport species.
  - humans: 2 individual(s)
  - zombies: 2 individual(s)
* If humans are present, they must not be outnumbered by zombies.
"""

# Find first solution
z3Code = converter.solveProblem(problem)
print(z3Code)

# Find ALL optimal solutions (minimum steps)
z3Code = converter.solveProblem(problem, findAllSolutions=True)
print(z3Code)

# Or use the enhanced random problem generator
from generateRandomProblems import RandomProblemGenerator

generator = RandomProblemGenerator()
# Generate with fixed individuals per species and shuttle capacity
randomProblem = generator.generateProblem(3, 1, individualsPerSpecies=2, capacity=2)  # 3 species, 1 constraint, 2 individuals each, capacity 2
print(randomProblem)

# Or generate with random counts and automatic capacity
randomProblem = generator.generateProblem(3, 1, minCount=1, maxCount=4)  # 3 species, 1 constraint, 1-4 individuals each, auto capacity
print(randomProblem)
```

## How It Works

1. **Parsing**: Uses regex patterns to extract:
   - Shuttle capacity
   - Species names and counts  
   - Safety constraints

2. **Constraint Generation**: Creates Z3 variables for:
   - Start/target bank populations at each step
   - Shuttle movements between steps
   - Safety constraints (e.g., "not outnumbered")

3. **Multi-Step Search**: Iteratively tries solutions with increasing step counts:
   - **Single Solution Mode**: Stops at first valid solution found  
   - **Optimal Solutions Mode**: Finds minimum steps required, then ALL solutions using that minimum

4. **Solution Extraction**: Converts Z3 model back into human-readable transportation plans with detailed summaries

## Supported Constraint Types

- **Capacity Constraints**: `shuttle with capacity N`
- **Population Constraints**: `X: N individual(s)`
- **Safety Constraints**: `if X are present, they must not be outnumbered by Y`
- **Separation Constraints**: `X must not be with Y` (when farmer not present)

## Advanced Usage

### Generate Z3 Code Template
```bash
python solve_transport.py --example 1 --show-code > generated_z3.py
python generated_z3.py
```

### Interactive Problem Solving
```bash
python solve_transport.py --interactive
# Enter problem description
# Type 'help' for examples
# Type 'exit' to quit
```

### Custom Constraint Types
The solver can be extended to handle additional constraint types by modifying the parsing logic in the `parse_problem()` method.

## Limitations

- Currently supports "not outnumbered" and basic separation constraints
- Maximum of 5 steps (configurable)
- Species names must be alphanumeric with underscores
- Constraint descriptions must follow specific patterns

## Contributing

Feel free to extend the constraint types, improve the natural language parsing, or add new solution visualization features!

## License

This project is provided as-is for educational and research purposes.