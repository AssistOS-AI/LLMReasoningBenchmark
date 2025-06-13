#!/usr/bin/env python3

import re
import sys
import os

def transformLine(line):
    """
    Transform a line from format:
    'move [number] [species1] [count1] [species2] [count2] ... [location] -> [location]'
    to:
    'move [count1] [species1] [count2] [species2] ... [location] -> [location]'
    
    Also handles 'empty' moves:
    'move [number] empty [location] -> [location]' -> 'move empty [location] -> [location]'
    """
    line = line.strip()
    if not line:
        return line
    
    # Pattern to match: move <number> <rest of line>
    pattern = r'^move\s+(\d+)\s+(.*)'
    
    match = re.match(pattern, line)
    if match:
        moveNumber = match.group(1)  # This will be removed
        restOfLine = match.group(2)  # Everything after the move number
        
        # Check if it's an empty move
        if 'empty' in restOfLine:
            return f"move {restOfLine}"
        
        # Split the rest of line to separate species info from direction
        # Look for patterns like "start -> target" or "target -> start"
        directionPattern = r'(.*?)\s+((?:start|target)\s*->\s*(?:target|start).*)'
        directionMatch = re.match(directionPattern, restOfLine)
        
        if directionMatch:
            speciesPart = directionMatch.group(1).strip()
            directionPart = directionMatch.group(2).strip()
            
            # Transform species part: "species1 count1 species2 count2" -> "count1 species1 count2 species2"
            transformedSpecies = transformSpeciesPart(speciesPart)
            
            return f"move {transformedSpecies} {directionPart}"
        else:
            # Fallback: just remove move number if direction pattern not found
            return f"move {restOfLine}"
    
    # If pattern doesn't match, return original line
    return line

def transformSpeciesPart(speciesPart):
    """
    Transform species part from "species1 count1 species2 count2" to "count1 species1 count2 species2"
    """
    # Find all patterns of word followed by number
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s+(\d+)'
    
    def replaceFunc(match):
        species = match.group(1)
        count = match.group(2)
        return f"{count} {species}"
    
    # Replace all species count patterns
    transformed = re.sub(pattern, replaceFunc, speciesPart)
    
    return transformed

def main():
    if len(sys.argv) != 2:
        print("Usage: python transformMovesEnhanced.py <input_filename>")
        print("")
        print("This script transforms move lines by removing the move number and")
        print("reordering species counts to come before species names.")
        print("Examples:")
        print("  Input:  'move 37 morelwex 1 jamerorn 1 cynorkin 2 flothy 1 start -> target'")
        print("  Output: 'move 1 morelwex 1 jamerorn 2 cynorkin 1 flothy start -> target'")
        print("")
        print("  Input:  'move 38 empty target -> start'")
        print("  Output: 'move empty target -> start'")
        sys.exit(1)
    
    inputFile = sys.argv[1]
    
    # Check if input file exists
    if not os.path.exists(inputFile):
        print(f"Error: Input file '{inputFile}' not found")
        sys.exit(1)
    
    # Generate output filename by adding '_transformed' before the extension
    base, ext = os.path.splitext(inputFile)
    outputFile = f"{base}_transformed{ext}"
    
    try:
        transformedLines = []
        with open(inputFile, 'r') as infile:
            for lineNum, line in enumerate(infile, 1):
                transformedLine = transformLine(line)
                transformedLines.append(transformedLine)
        
        # Write to output file
        with open(outputFile, 'w') as outfile:
            for line in transformedLines:
                outfile.write(line + '\n')
        
        print(f"Transformation complete!")
        print(f"Input file:  {inputFile}")
        print(f"Output file: {outputFile}")
        print(f"Processed {len(transformedLines)} lines")
        
        # Show a few example transformations
        print("\nExample transformations:")
        with open(inputFile, 'r') as infile:
            originalLines = [line.strip() for line in infile.readlines()]
        
        for i in range(min(5, len(originalLines))):
            if originalLines[i] and transformedLines[i] != originalLines[i]:
                print(f"  Before: {originalLines[i]}")
                print(f"  After:  {transformedLines[i]}")
                print()
        
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 