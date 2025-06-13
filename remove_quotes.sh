#!/bin/bash

# Script to remove quotes (backticks) from around each line in a file
# Usage: ./remove_quotes.sh <input_file> [output_file]

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
    sed -i 's/^`//; s/`$//' "$inputFile"
    echo "Removed quotes from '$inputFile' (modified in place)"
else
    # Output to new file
    sed 's/^`//; s/`$//' "$inputFile" > "$outputFile"
    echo "Removed quotes from '$inputFile' and saved to '$outputFile'"
fi 