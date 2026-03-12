#!/bin/bash

# Configuration
INPUT_FILE=$1
OUTPUT_FILE=$2
TEMP_FILE="results.tmp"
# usage: ./ip-slice.sh ips.txt
# Check if input file exists
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: $INPUT_FILE not found."
    exit 1
fi

# Clear or create the output file
> "$OUTPUT_FILE"
> "$TEMP_FILE"
echo "Processing quoted, comma-separated IPs..."

# 1. Read the file
# 2. Use tr to replace commas with newlines
# 3. Use tr -d to delete double quotes
# 4. Loop through the cleaned list
cat "$INPUT_FILE" | tr ',' '\n' | tr -d '"' | while read -r ip; do
    
    # Trim leading/trailing whitespace just in case
    ip=$(echo "$ip" | xargs)

    # Skip if the resulting string is empty
    [[ -z "$ip" ]] && continue

    # --- THE COMMAND SECTION ---
    # Replace the 'ipcalc' example with your specific command
    echo "ipcalc $ip/31..."
    
    result=$(ipcalc "$ip"/31 2>/dev/null | grep -E 'HostMin|HostMax' | awk -F ' ' '{print $2}')

    if [[ -z "$result" ]]; then
        echo "$ip: FAILED" >> "$TEMP_FILE"
    else
        echo "$result" >> "$TEMP_FILE"
    fi
    # ---------------------------

done

# ---- The Duplicate removal step ----
# sort the temp file and output only unique lines to the final file
sort -u "$TEMP_FILE" > "$OUTPUT_FILE"

# Clean up the temp file
rm "$TEMP_FILE"

echo "Done! Results saved to $OUTPUT_FILE."
