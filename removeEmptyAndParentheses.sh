#!/bin/bash

# Script to remove empty lines and content within parentheses (including parentheses)
# Usage: ./removeEmptyAndParentheses.sh <input_file> [output_file]

if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_file> [output_file]"
    echo "If no output file is specified, the input file will be modified in place"
    exit 1
fi

inputFile="$1"
outputFile="$2"

if [ ! -f "$inputFile" ]; then
    echo "Error: Input file '$inputFile' not found"
    exit 1
fi

if [ -z "$outputFile" ]; then
    # Modify in place
    # First remove empty lines, then remove content within parentheses
    sed -i '/^[[:space:]]*$/d' "$inputFile"
    sed -i 's/([^)]*)//g' "$inputFile"
    echo "Removed empty lines and parentheses content from '$inputFile' (modified in place)"
else
    # Output to new file
    # First remove empty lines, then remove content within parentheses
    sed '/^[[:space:]]*$/d' "$inputFile" | sed 's/([^)]*)//g' > "$outputFile"
    echo "Removed empty lines and parentheses content from '$inputFile' and saved to '$outputFile'"
fi 