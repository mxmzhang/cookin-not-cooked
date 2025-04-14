import json
import csv
import argparse

def convert_proportions_to_csv(recipe_data_file, proportions_file, output_csv):
    """
    Convert the proportions data into a human-readable CSV file
    
    Args:
        recipe_data_file: File containing structured recipe data
        proportions_file: File containing ingredient proportions
        output_csv: Where to save the CSV report
    """
    # Load recipe data
    try:
        with open(recipe_data_file, 'r') as f:
            data = json.load(f)
            if not all(key in data for key in ["recipes", "ingredients"]):
                print("[!] Missing required data in recipe file")
                return False
    except Exception as e:
        print(f"[!] Error loading recipe data: {e}")
        return False
        
    # Load proportions data
    try:
        with open(proportions_file, 'r') as f:
            proportions = json.load(f)
    except Exception as e:
        print(f"[!] Error loading proportions data: {e}")
        return False
    
    # Prepare CSV data
    csv_rows = []
    
    for key, proportion in proportions.items():
        recipe_id, ingredient_id = key.split('|')
        
        recipe_name = data["recipes"].get(recipe_id, {}).get("name", "Unknown Recipe")
        ingredient_name = data["ingredients"].get(ingredient_id, {}).get("name", "Unknown Ingredient")
        package_unit = data["ingredients"].get(ingredient_id, {}).get("price_unit", "Unknown Unit")
        
        csv_rows.append({
            "Recipe": recipe_name,
            "Ingredient": ingredient_name,
            "Package Size": package_unit,
            "Proportion Used": f"{proportion:.4f}",
            "Percentage": f"{proportion * 100:.1f}%"
        })
    
    # Sort by recipe name and then ingredient name
    csv_rows.sort(key=lambda x: (x["Recipe"], x["Ingredient"]))
    
    # Write to CSV
    try:
        with open(output_csv, 'w', newline='') as f:
            if csv_rows:
                writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
                writer.writeheader()
                writer.writerows(csv_rows)
                print(f"[✓] Successfully wrote {len(csv_rows)} rows to {output_csv}")
            else:
                print("[!] No data to write to CSV")
    except Exception as e:
        print(f"[!] Error writing CSV: {e}")
        return False
        
    return True

def analyze_proportions(recipe_data_file, proportions_file):
    """
    Print a simple analysis of the proportions data
    """
    # Load recipe data
    try:
        with open(recipe_data_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Error loading recipe data: {e}")
        return
        
    # Load proportions data
    try:
        with open(proportions_file, 'r') as f:
            proportions = json.load(f)
    except Exception as e:
        print(f"[!] Error loading proportions data: {e}")
        return
    
    # Count recipes and ingredients
    recipe_ids = set()
    ingredient_ids = set()
    
    for key in proportions.keys():
        recipe_id, ingredient_id = key.split('|')
        recipe_ids.add(recipe_id)
        ingredient_ids.add(ingredient_id)
    
    # Calculate statistics
    total_proportions = len(proportions)
    avg_proportion = sum(proportions.values()) / total_proportions if total_proportions > 0 else 0
    
    # Find top ingredients used in smallest proportions
    ingredient_props = {}
    for key, prop in proportions.items():
        _, ingredient_id = key.split('|')
        if ingredient_id not in ingredient_props:
            ingredient_props[ingredient_id] = []
        ingredient_props[ingredient_id].append(prop)
    
    avg_by_ingredient = {ing_id: sum(props)/len(props) for ing_id, props in ingredient_props.items()}
    lowest_usage = sorted(avg_by_ingredient.items(), key=lambda x: x[1])[:5]
    
    # Print analysis
    print("\n=== PROPORTION ANALYSIS ===")
    print(f"Total recipes analyzed: {len(recipe_ids)}")
    print(f"Total unique ingredients: {len(ingredient_ids)}")
    print(f"Total recipe-ingredient combinations: {total_proportions}")
    print(f"Average package proportion used: {avg_proportion:.4f} ({avg_proportion*100:.1f}%)")
    
    print("\nIngredients with lowest average usage (potential waste):")
    for ing_id, avg_prop in lowest_usage:
        name = data["ingredients"].get(ing_id, {}).get("name", "Unknown")
        unit = data["ingredients"].get(ing_id, {}).get("price_unit", "Unknown")
        print(f"- {name} ({unit}): {avg_prop:.4f} ({avg_prop*100:.1f}%)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert ingredient proportions to CSV')
    parser.add_argument('--recipe-data', default="structured_recipe_data_pre_pricing.json", 
                        help='Input JSON file with recipe data')
    parser.add_argument('--proportions', default="ingredient_proportions.json", 
                        help='Input JSON file with proportions data')
    parser.add_argument('--output', default="recipe_proportions.csv", 
                        help='Output CSV file')
    parser.add_argument('--analyze', action='store_true',
                        help='Print analysis of proportions')
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_proportions(args.recipe_data, args.proportions)
        
    print(f"[*] Converting proportions from {args.proportions} to CSV format")
    convert_proportions_to_csv(args.recipe_data, args.proportions, args.output)