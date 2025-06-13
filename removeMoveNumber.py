#!/usr/bin/env python3

import re
import sys
import os

def transformLine(line):
    """
    Transform a line from format:
    'move [number1] [species] [number2] [location] -> [location]'
    to:
    'move [species] [number2] [location] -> [location]'
    """
    # Pattern to match: move <number> <rest of line>
    pattern = r'move\s+\d+\s+(.*)'
    
    match = re.match(pattern, line.strip())
    if match:
        restOfLine = match.group(1)  # Everything after the move number
        return f"move {restOfLine}"
    
    # If pattern doesn't match, return original line
    return line.strip()

def main():
    if len(sys.argv) != 2:
        print("Usage: python removeMoveNumber.py <input_filename>")
        sys.exit(1)
    
    inputFile = sys.argv[1]
    # Generate output filename by adding '_transformed' before the extension
    base, ext = os.path.splitext(inputFile)
    outputFile = f"{base}_transformed{ext}"
    
    try:
        with open(inputFile, 'r') as infile, open(outputFile, 'w') as outfile:
            for line in infile:
                transformedLine = transformLine(line)
                outfile.write(transformedLine + '\n')
        
        print(f"Transformation complete! Output saved to {outputFile}")
        print(f"Original format: move 1 flogor 2 start -> target")
        print(f"New format:      move flogor 2 start -> target")
        
    except FileNotFoundError:
        print(f"Error: {inputFile} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 