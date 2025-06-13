#!/usr/bin/env python3
import re
import sys

def removeNumbering(filename):
    """Remove number, dot/parenthesis, and space from the beginning of each line."""
    with open(filename, 'r') as file:
        lines = file.readlines()
    
    # Remove the pattern "number." or "number)" followed by spaces from the beginning of each line
    cleanedLines = []
    for line in lines:
        # Use regex to match and remove "number." or "number)" followed by spaces at the start of line
        cleanedLine = re.sub(r'^\d+[.)]\s+', '', line)
        cleanedLines.append(cleanedLine)
    
    # Write back to the file
    with open(filename, 'w') as file:
        file.writelines(cleanedLines)
    
    print(f"Successfully removed numbering from {len(cleanedLines)} lines in {filename}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python removeNumbering.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    try:
        removeNumbering(filename)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 