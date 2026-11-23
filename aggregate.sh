#!/bin/bash

INPUT_FILE=$1
OUTPUT_FILE="consolidated_supernets.txt"

# clear or create the output file
>"$OUTPUT_FILE"
# 1. Clean the input: Replace commas with newlines, remove quotes/spaces
# 2. Sort the list (required for most aggregation tools)
# 3. Use 'aggregate' to find the supernets
# 4. Save unique results to the output file

cat "$INPUT_FILE" | tr ',' '\n' | tr -d '"' | xargs -n1 | sort -u | aggregate -q > "$OUTPUT_FILE"

echo "Consolidation complete. Results saved to $OUTPUT_FILE."
echo "Original count: $( wc -l "$INPUT_FILE")"
echo "Consolidated count: $(wc -l < "$OUTPUT_FILE")"
