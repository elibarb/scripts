import ipaddress
import json
import sys

# Configuration
INPUT_FILE = "ip"
OUTPUT_FILE = "consolidated.json"

def process_networks():
    try:
        with open(INPUT_FILE, "r") as f:
            # Clean quotes, replace commas with spaces, and split into a list
            raw_data = f.read().replace('"', '').replace(',', ' ').split()
        
        # Convert strings to IP objects (handles both single IPs and CIDRs)
        # We use set() to remove exact duplicates immediately
        networks = []
        for item in set(raw_data):
            item = item.strip()
            if item:
                # ip_network(strict=False) allows host bits to be set
                networks.append(ipaddress.ip_network(item, strict=False))

        # Collapse the list into supernets
        consolidated = list(ipaddress.collapse_addresses(networks))

        # Build the JSON structure
        output_data = {
            "metadata": {
                "total_original": len(raw_data),
                "total_consolidated": len(consolidated)
            },
            "supernets": [str(net) for net in consolidated]
        }

        # Write to file
        with open(OUTPUT_FILE, "w") as jf:
            json.dump(output_data, jf, indent=4)

        print(f"Success! {len(consolidated)} supernets written to {OUTPUT_FILE}")

    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    process_networks()
