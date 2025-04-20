import json
import requests
import time

def call_gemini_for_proportions(api_key, ingredients_batch, retry_count=2):
    if not ingredients_batch:
        print("[!] No ingredients to process")
        return {}
    
    # Create a table for the prompt
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
        f"Return ONLY a list of numbers representing the proportion for each ingredient in order. "
        f"Each proportion should be a decimal between 0 and 1. "
        f"If you cannot convert a particular item, use 'null'.\n\n"
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

    print(f"[*] Sending batch request to Gemini with {len(ingredients_batch)} items")
    
    for attempt in range(retry_count + 1):
        try:
            response = requests.post(url, headers=headers, params={"key": api_key}, json=data)
            
            if response.status_code != 200:
                print(f"[x] Gemini API error: {response.status_code} - {response.text}")
                if attempt < retry_count:
                    print(f"[*] Retrying in 5 seconds (attempt {attempt+1}/{retry_count})")
                    time.sleep(5)
                    continue
                return {}
                
            result = response.json()
            if "candidates" not in result or not result["candidates"]:
                print(f"[x] No candidates in Gemini response: {result}")
                if attempt < retry_count:
                    print(f"[*] Retrying in 5 seconds (attempt {attempt+1}/{retry_count})")
                    time.sleep(5)
                    continue
                return {}
                
            answer_text = result["candidates"][0]["content"]["parts"][0]["text"]
            print(f"[*] Received response from Gemini")
            
            # Try to parse the list of proportions
            try:
                # Clean up the response text
                cleaned_text = answer_text.strip()
                if cleaned_text.startswith("```") and cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[3:-3].strip()
                
                # Try to extract just the array portion
                import re
                array_match = re.search(r'\[(.*?)\]', cleaned_text, re.DOTALL)
                if array_match:
                    cleaned_text = array_match.group(0)
                
                # Parse the JSON array
                proportions_array = json.loads(cleaned_text)
                
                # Convert to dictionary by index
                proportions = {}
                for i, value in enumerate(proportions_array):
                    if value is not None:  # Skip null values
                        proportions[i] = float(value)
                        print(f"  [{i+1}] Proportion: {proportions[i]:.4f}")
                
                return proportions
                
            except Exception as e:
                print(f"[x] Error parsing Gemini response: {e}")
                print(f"Raw response: {answer_text}")
                if attempt < retry_count:
                    print(f"[*] Retrying in 5 seconds (attempt {attempt+1}/{retry_count})")
                    time.sleep(5)
                    continue
                return {}
                    
        except Exception as e:
            print(f"[x] Gemini API error: {e}")
            if attempt < retry_count:
                print(f"[*] Retrying in 5 seconds (attempt {attempt+1}/{retry_count})")
                time.sleep(5)
            else:
                return {}
    
    return {}

def create_gemini_query_format(recipe_data_file, prices_file, api_key, output_file="gemini_query_results.json"):
    # Load recipe data
    try:
        with open(recipe_data_file, 'r') as f:
            data = json.load(f)
            if not all(key in data for key in ["recipes", "ingredients", "recipe_ingredients"]):
                print("[!] Missing required data in recipe file")
                return False
    except Exception as e:
        print(f"[!] Error loading recipe data: {e}")
        return False
        
    # Load price data
    try:
        with open(prices_file, 'r') as f:
            prices = json.load(f)
    except Exception as e:
        print(f"[!] Error loading price data: {e}")
        return False
    
    # Initialize the output structure for GEMINI QUERY
    gemini_results = {
        "recipes": []
    }
    
    # Process each recipe
    total_recipes = len(data["recipes"])
    processed_recipes = 0
    
    for recipe_id, recipe_info in data["recipes"].items():
        processed_recipes += 1
        recipe_name = recipe_info["name"]
        print(f"\n[*] Processing recipe {processed_recipes}/{total_recipes}: {recipe_name}")
        
        recipe_ingredients = data["recipe_ingredients"].get(recipe_id, [])
        
        if not recipe_ingredients:
            print(f"[!] No ingredients found for recipe {recipe_id}")
            continue
        
        # Prepare ingredients batch for Gemini
        conversion_batch = []
        
        for ingredient_tuple in recipe_ingredients:
            ingredient_id, amount, unit = ingredient_tuple
            
            if ingredient_id not in data["ingredients"]:
                print(f"[!] Ingredient ID {ingredient_id} not found in ingredients data")
                continue
                
            ing_info = data["ingredients"][ingredient_id]
            name = ing_info.get("name", "unknown ingredient")

            if ingredient_id in prices and prices[ingredient_id].get("price_unit"):
                kroger_unit = prices[ingredient_id]["price_unit"]
            else:
                print(f"[!] Missing unit for {name}")
                continue
            
            conversion_batch.append({
                "ingredient_id": ingredient_id,
                "ingredient_name": name,
                "recipe_amount": amount,
                "recipe_unit": unit,
                "kroger_unit": kroger_unit
            })
        
        if not conversion_batch:
            print(f"[!] No valid ingredients for recipe {recipe_id}")
            continue
        
        # Process ingredients in batches of 30 max
        MAX_BATCH_SIZE = 30
        all_proportions = {}
        
        for i in range(0, len(conversion_batch), MAX_BATCH_SIZE):
            batch_slice = conversion_batch[i:i + MAX_BATCH_SIZE]
            
            print(f"[*] Processing batch of {len(batch_slice)} ingredients (batch {i//MAX_BATCH_SIZE + 1})")
            batch_proportions = call_gemini_for_proportions(api_key, batch_slice)
            
            # Merge results
            for idx, proportion in batch_proportions.items():
                batch_idx = i + idx
                if batch_idx < len(conversion_batch):
                    ingredient_id = conversion_batch[batch_idx]["ingredient_id"]
                    all_proportions[ingredient_id] = proportion
            
            # Wait before next batch
            if i + MAX_BATCH_SIZE < len(conversion_batch):
                time.sleep(2)
        
        # Create recipe structure for output
        recipe_result = {
            "id": recipe_id,
            "name": recipe_name,
            "ingredients": []
        }
        
        # Add ingredients with proportions and costs
        for item in conversion_batch:
            ingredient_id = item["ingredient_id"]
            proportion = all_proportions.get(ingredient_id)
            
            # Get cost from prices
            cost = None
            if ingredient_id in prices:
                cost = prices[ingredient_id].get("unit_price")
            
            recipe_result["ingredients"].append({
                "id": ingredient_id,
                "name": item["ingredient_name"],
                "proportion": proportion,
                "cost": cost
            })
        
        gemini_results["recipes"].append(recipe_result)
        
        # Wait a bit before next recipe
        if processed_recipes < total_recipes:
            time.sleep(1)
    
    # Save the results
    with open(output_file, 'w') as f:
        json.dump(gemini_results, f, indent=2)
    print(f"[✓] Saved Gemini query results to {output_file}")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate GEMINI QUERY formatted data')
    parser.add_argument('--recipe-data', default="recipe_data_cleaned.json", 
                        help='Input JSON file with recipe data')
    parser.add_argument('--prices', default="ingredient_prices.json", 
                        help='Input JSON file with ingredient prices')
    parser.add_argument('--output', default="ingredient_usage.json", 
                        help='Output file for Gemini query results')
    parser.add_argument('--api-key', default="AIzaSyAy2D2jxTMLUpow2jsf6IIjC2XR6sENRDs", 
                        help='Gemini API key')
    
    args = parser.parse_args()
    
    print(f"[*] Creating Gemini query format from {args.recipe_data} using prices from {args.prices}")
    create_gemini_query_format(args.recipe_data, args.prices, args.api_key, args.output)