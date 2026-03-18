import json
import os
import sys

# Add project root to path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
KG_PATH = os.path.join(os.path.dirname(_THIS_DIR), "data", "knowledge_graph.json")

def merge_nodes(master_path: str, new_nodes_path: str):
    """
    Merge new enriched nodes into the master Knowledge Graph.
    """
    if not os.path.exists(master_path):
        print(f"Error: Master KG not found at {master_path}")
        return

    if not os.path.exists(new_nodes_path):
        print(f"Error: New nodes file not found at {new_nodes_path}")
        return

    # 1. Load Master KG
    with open(master_path, "r", encoding="utf-8") as f:
        master_kg = json.load(f)

    # 2. Load New Nodes
    with open(new_nodes_path, "r", encoding="utf-8") as f:
        new_nodes = json.load(f)

    # 3. Perform Merge
    existing_ids = {node["id"] for node in master_kg.get("nodes", [])}
    added_count = 0
    updated_count = 0

    for new_node in new_nodes:
        if new_node["id"] in existing_ids:
            # Update existing node (optional strategy)
            for i, master_node in enumerate(master_kg["nodes"]):
                if master_node["id"] == new_node["id"]:
                    master_kg["nodes"][i] = new_node
                    updated_count += 1
                    break
        else:
            # Append new node
            master_kg["nodes"].append(new_node)
            added_count += 1

    # 4. Save Updated KG
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master_kg, f, indent=2)

    print(f"--- KG Merge Complete ---")
    print(f"  Added: {added_count} new nodes")
    print(f"  Updated: {updated_count} existing nodes")
    print(f"  Total Nodes now: {len(master_kg['nodes'])}")

if __name__ == "__main__":
    enriched_file = "enriched_sample.json"
    merge_nodes(KG_PATH, enriched_file)
