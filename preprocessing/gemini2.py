import json
import requests
import time
import re
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored terminal output
init()

def print_info(message):
    print(f"{Fore.BLUE}[*]{Style.RESET_ALL} {message}")

def print_success(message):
    print(f"{Fore.GREEN}[✓]{Style.RESET_ALL} {message}")

def print_warning(message):
    print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {message}")

def print_error(message):
    print(f"{Fore.RED}[✗]{Style.RESET_ALL} {message}")

def print_debug(message):
    print(f"{Fore.CYAN}[D]{Style.RESET_ALL} {message}")

def call_gemini_for_proportions(api_key, ingredients_batch, retry_count=2):
    if not ingredients_batch:
        print_warning("No ingredients to process")
        return {}
    
    # Create a table for the prompt - using a format that works well in prompts
    table_rows = ["| Index | Ingredient | Recipe Amount | Recipe Unit | Package Size |"]
    table_rows.append("| ----- | ---------- | ------------ | ----------- | ------------ |")
    
    for i, item in enumerate(ingredients_batch):
        table_rows.append(f"| {i+1} | {item['ingredient_name']} | {item['recipe_amount']} | {item['recipe_unit']} | {item['kroger_unit']} |")
    
    table = "\n".join(table_rows)
    
    prompt = (
        f"Below is a table of ingredients with their recipe quantities and package sizes.\n\n"
        f"{table}\n\n"
        f"For each ingredient, convert the recipe amount to the same unit as the package size, "
        f"then calculate what proportion of one package is used in the recipe.\n\n"
        f"for example, if i want 8 olives, you need to guesstimate how much of 1 package it would be\n\n"
        f"Return ONLY a list of numbers representing the proportion for each ingredient in order. "
        f"Each proportion should be a decimal between 0 and 1. "
        f"If you cannot convert a particular item, use 'null' but really try your best and make an educated guess.\n\n"
        f"Example response format: [0.25, 0.5, null, 0.75]\n"
        f"DO NOT include any explanations or show your work. Just return the array of numbers."
    )

    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    print_info(f"Sending batch request to Gemini with {len(ingredients_batch)} items")
    
    for attempt in range(retry_count + 1):
        try:
            response = requests.post(url, headers=headers, params={"key": api_key}, json=data)
            
            if response.status_code != 200:
                print_error(f"Gemini API error: {response.status_code} - {response.text}")
                if attempt < retry_count:
                    print_info(f"Retrying in 5 seconds (attempt {attempt+1}/{retry_count})")
                    time.sleep(5)
                    continue
                return {}
                
            result = response.json()
            if "candidates" not in result or not result["candidates"]:
                print_error(f"No candidates in Gemini response: {json.dumps(result, indent=2)}")
                if attempt < retry_count:
                    print_info(f"Retrying in 5 seconds (attempt {attempt+1}/{retry_count})")
                    time.sleep(5)
                    continue
                return {}
                
            answer_text = result["candidates"][0]["content"]["parts"][0]["text"]
            print_info(f"Received response from Gemini")
            
            # Try to parse the list of proportions
            try:
                # Clean up the response text
                cleaned_text = answer_text.strip()
                if cleaned_text.startswith("```") and cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[3:-3].strip()
                
                # Try to extract just the array portion with more robust regex
                array_match = re.search(r'\[(?:\s*(?:null|\d+(?:\.\d+)?)\s*,?\s*)+\]', cleaned_text, re.DOTALL)
                if array_match:
                    cleaned_text = array_match.group(0)
                
                # Parse the JSON array
                proportions_array = json.loads(cleaned_text)
                
                # Convert to dictionary by index
                proportions = {}
                for i, value in enumerate(proportions_array):
                    if value is not None:  # Skip null values
                        proportions[i] = float(value)
                        print_debug(f"Item {i+1}: Proportion = {proportions[i]:.4f}")
                
                return proportions
                
            except Exception as e:
                print_error(f"Error parsing Gemini response: {str(e)}")
                print_debug(f"Raw response: {answer_text}")
                if attempt < retry_count:
                    print_info(f"Retrying in 5 seconds (attempt {attempt+1}/{retry_count})")
                    time.sleep(5)
                    continue
                return {}
                    
        except Exception as e:
            print_error(f"Gemini API request error: {str(e)}")
            if attempt < retry_count:
                print_info(f"Retrying in 5 seconds (attempt {attempt+1}/{retry_count})")
                time.sleep(5)
            else:
                return {}
    
    return {}

def create_gemini_query_format(spoonacular_data_file, kroger_data_file, api_key, output_file="gemini_query_results.json"):
    print_info(f"Starting process with files:")
    print_info(f"  - Spoonacular data: {spoonacular_data_file}")
    print_info(f"  - Kroger data: {kroger_data_file}")
    print_info(f"  - Output file: {output_file}")
    
    # Load Spoonacular data
    try:
        with open(spoonacular_data_file, 'r') as f:
            spoonacular_data = json.load(f)
            if not all(key in spoonacular_data for key in ["recipes", "all_ingredients", "recipe_ingredients"]):
                print_error("Missing required data in Spoonacular file")
                return False
    except Exception as e:
        print_error(f"Error loading Spoonacular data: {str(e)}")
        return False
        
    # Load Kroger price data
    try:
        with open(kroger_data_file, 'r') as f:
            kroger_data = json.load(f)
            if "kroger_query" not in kroger_data or "ingredients" not in kroger_data["kroger_query"]:
                print_error("Missing required data in Kroger file")
                return False
            # Create a lookup dictionary for ingredients by i_id
            price_lookup = {}
            for ingredient in kroger_data["kroger_query"]["ingredients"]:
                i_id = ingredient["i_id"]
                price_lookup[i_id] = {
                    "unit_price": ingredient.get("unit_price"),
                    "unit_quantity": ingredient.get("unit_quantity", 1),
                    "measurement": ingredient.get("measurement", "unit")
                }
    except Exception as e:
        print_error(f"Error loading Kroger price data: {str(e)}")
        return False
    
    # Initialize the output structure for Gemini Query
    gemini_results = {
        "gemini_query": {
            "recipes": []
        }
    }
    
    # Process each recipe
    total_recipes = len(spoonacular_data["recipes"])
    processed_recipes = 0
    
    # Create a lookup dictionary for ingredients by ri_id
    ingredient_lookup = {}
    for ingredient in spoonacular_data["all_ingredients"]:
        i_id = ingredient["i_id"]
        ri_id = ingredient.get("ri_id")
        ingredient_lookup[ri_id] = i_id
    
    print_info(f"Processing {total_recipes} recipes")
    print("-" * 60)
    
    for recipe in spoonacular_data["recipes"]:
        processed_recipes += 1
        recipe_id = recipe["r_id"]
        recipe_name = recipe["name"]
        print_info(f"Recipe {processed_recipes}/{total_recipes}: {recipe_name} (ID: {recipe_id})")
        
        # Find recipe ingredients
        recipe_ingredients_data = None
        for ri_entry in spoonacular_data["recipe_ingredients"]:
            if ri_entry["r_id"] == recipe_id:
                recipe_ingredients_data = ri_entry["ingredients"]
                break
        
        if not recipe_ingredients_data:
            print_warning(f"No ingredients found for recipe {recipe_id}")
            print("-" * 60)
            continue
        
        # Prepare ingredients batch for Gemini
        conversion_batch = []
        
        for ingredient in recipe_ingredients_data:
            ri_id = ingredient["ri_id"]
            i_id = ingredient["i_id"]
            quantity = ingredient["quantity"]
            unit = ingredient["unit"]
            
            # Find ingredient name from all_ingredients
            ingredient_name = None
            for ing in spoonacular_data["all_ingredients"]:
                if ing["i_id"] == i_id:
                    ingredient_name = ing["name"]
                    break
            
            if not ingredient_name:
                print_warning(f"Ingredient name not found for i_id {i_id}")
                continue
            
            # Get packaging info from Kroger data
            kroger_unit = "unit"
            if i_id in price_lookup:
                kroger_unit = f"{price_lookup[i_id]['unit_quantity']} {price_lookup[i_id]['measurement']}"
            
            conversion_batch.append({
                "ri_id": ri_id,
                "i_id": i_id,
                "ingredient_name": ingredient_name,
                "recipe_amount": quantity,
                "recipe_unit": unit,
                "kroger_unit": kroger_unit
            })
        
        if not conversion_batch:
            print_warning(f"No valid ingredients for recipe {recipe_id}")
            print("-" * 60)
            continue
        
        # Process ingredients in batches of 30 max
        MAX_BATCH_SIZE = 30
        all_proportions = {}
        
        for i in range(0, len(conversion_batch), MAX_BATCH_SIZE):
            batch_slice = conversion_batch[i:i + MAX_BATCH_SIZE]
            
            print_info(f"Processing batch of {len(batch_slice)} ingredients (batch {i//MAX_BATCH_SIZE + 1})")
            batch_proportions = call_gemini_for_proportions(api_key, batch_slice)
            
            # Merge results
            for idx, proportion in batch_proportions.items():
                batch_idx = i + idx
                if batch_idx < len(conversion_batch):
                    batch_item = conversion_batch[batch_idx]
                    all_proportions[batch_item["ri_id"]] = proportion
            
            # Wait before next batch
            if i + MAX_BATCH_SIZE < len(conversion_batch):
                time.sleep(2)
        
        # Create recipe structure for output (following your format)
        recipe_result = {
            "r_id": recipe_id,
            "ingredients": []
        }
        
        # Add ingredients with proportions and costs
        for item in conversion_batch:
            ri_id = item["ri_id"]
            i_id = item["i_id"]
            proportion = all_proportions.get(ri_id)
            
            # Get cost from prices, default to $4 (400 cents) if not available
            cost = 400  # Default cost of $4
            if i_id in price_lookup and price_lookup[i_id]["unit_price"] is not None:
                cost = price_lookup[i_id]["unit_price"]
            
            recipe_result["ingredients"].append({
                "ri_id": ri_id,
                "name": item["ingredient_name"],
                "proportion": proportion,
                "package_cost": cost
            })
        
        gemini_results["gemini_query"]["recipes"].append(recipe_result)
        print_success(f"Completed recipe: {recipe_name}")
        print("-" * 60)
        
        # Wait a bit before next recipe
        if processed_recipes < total_recipes:
            time.sleep(1)
    
    # Save the results
    try:
        with open(output_file, 'w') as f:
            json.dump(gemini_results, f, indent=2)
        print_success(f"Saved Gemini query results to {output_file}")
    except Exception as e:
        print_error(f"Failed to save output file: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Gemini query formatted data')
    parser.add_argument('--spoonacular-data', default="spoonacular_structured_data.json", 
                        help='Input JSON file with Spoonacular recipe data')
    parser.add_argument('--kroger-data', default="kroger_prices.json", 
                        help='Input JSON file with Kroger ingredient prices')
    parser.add_argument('--output', default="gemini_query_results.json", 
                        help='Output file for Gemini query results')
    parser.add_argument('--api-key', default="AIzaSyAy2D2jxTMLUpow2jsf6IIjC2XR6sENRDs", 
                        help='Gemini API key')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print_info("GEMINI RECIPE PROPORTION CALCULATOR")
    print("=" * 80 + "\n")
    
    success = create_gemini_query_format(args.spoonacular_data, args.kroger_data, args.api_key, args.output)
    
    if success:
        print_success("Process completed successfully!")
    else:
        print_error("Process failed. Please check the errors above.")