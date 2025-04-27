import json

def combine_schemas(spoonacular_file="spoonacular_structured_data.json", 
                   kroger_file="kroger_prices.json", 
                   gemini_file="gemini_query_results.json",
                   output_file="combined_recipe_data.json"): 
    try:
        with open(spoonacular_file, 'r') as f:
            spoonacular_data = json.load(f)
    except Exception as e:
        print(f"Error loading Spoonacular data: {e}")
        return False
    
    try:
        with open(kroger_file, 'r') as f:
            kroger_data = json.load(f)
    except Exception as e:
        print(f"Error loading Kroger data: {e}")
        return False
    
    try:
        with open(gemini_file, 'r') as f:
            gemini_data = json.load(f)
    except Exception as e:
        print(f"Error loading Gemini data: {e}")
        return False
    
    # create price lookup dictionary
    price_lookup = {}
    for ingredient in kroger_data["kroger_query"]["ingredients"]:
        i_id = ingredient["i_id"]
        unit_price = ingredient.get("unit_price", 400)
        unit_quantity = ingredient.get("unit_quantity", 1)
        measurement = ingredient.get("measurement", "ct")
        price_lookup[i_id] = {
        "unit_price": unit_price,
        "unit_quantity": unit_quantity,
        "measurement": measurement
    }
    
    # create proportion lookup dictionary
    proportion_lookup = {}
    for recipe in gemini_data["gemini_query"]["recipes"]:
        r_id = recipe["r_id"]
        proportion_lookup[r_id] = {}
        for ingredient in recipe["ingredients"]:
            ri_id = ingredient["ri_id"]
            proportion_lookup[r_id][ri_id] = {
                "proportion": ingredient.get("proportion"),
                "package_cost": ingredient.get("package_cost")
            }
    
    # create ingredient-recipe mapping
    ingredient_recipes = defaultdict(list)
    for recipe_ingredients in spoonacular_data["recipe_ingredients"]:
        r_id = recipe_ingredients["r_id"]
        for ingredient in recipe_ingredients["ingredients"]:
            i_id = ingredient["i_id"]
            ri_id = ingredient["ri_id"]
            ingredient_recipes[i_id].append({
                "r_id": r_id,
                "ri_id": ri_id
            })
    
    # combined data structure
    combined_data = {
        "recipes": [],
        "all_ingredients": []
    }
    
    # process recipes
    for recipe in spoonacular_data["recipes"]:
        r_id = recipe["r_id"]
        recipe_data = {
            "r_id": r_id,
            "name": recipe["name"],
            "nutrients": recipe.get("nutrients", {"protein": 0, "calories": 0}),
            "ingredients": []
        }
        
        # find recipe ingredients
        for recipe_ingredients in spoonacular_data["recipe_ingredients"]:
            if recipe_ingredients["r_id"] == r_id:
                for ingredient in recipe_ingredients["ingredients"]:
                    ri_id = ingredient["ri_id"]
                    i_id = ingredient["i_id"]
                    
                    # find ingredient name
                    ingredient_name = ""
                    for ing in spoonacular_data["all_ingredients"]:
                        if ing["i_id"] == i_id:
                            ingredient_name = ing["name"]
                            break
                    
                    proportion_data = proportion_lookup.get(r_id, {}).get(ri_id, {})
                    price_data = price_lookup.get(i_id, {"unit_price": None})

                    # process missing info
                    proportion = proportion_data.get("proportion")
                    if proportion is None:
                        proportion = 1

                    unit_price = price_data.get("unit_price")
                    if unit_price is None:
                        unit_price = 400

                    recipe_data["ingredients"].append({
                        "ri_id": ri_id,
                        "name": ingredient_name,
                        "proportion": proportion,
                        "unit_price": unit_price,  
                        "i_id": i_id
                    })
                
                break
        
        combined_data["recipes"].append(recipe_data)
    
    # process all ingredients
    for ingredient in spoonacular_data["all_ingredients"]:
        i_id = ingredient["i_id"]
        unit_price = price_lookup.get(i_id, {}).get("unit_price")
        if unit_price is None:
            unit_price = 400
        ingredient_data = {
            "i_id": i_id,
            "name": ingredient["name"],
            "recipe_ingredients": [],
            "unit_price": unit_price
        }
        
        # add recipe ingredients using this ingredient
        for recipe_ref in ingredient_recipes.get(i_id, []):
            ingredient_data["recipe_ingredients"].append(recipe_ref["r_id"])
        
        combined_data["all_ingredients"].append(ingredient_data)
    
    # save everything
    try:
        with open(output_file, 'w') as f:
            json.dump(combined_data, f, indent=2)
        print(f"Combined data saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error saving combined data: {e}")
        return False

if __name__ == "__main__":
    from collections import defaultdict
    import argparse
    
    parser = argparse.ArgumentParser(description='Combine JSON data from multiple sources')
    parser.add_argument('--spoonacular', default="spoonacular_structured_data.json", 
                        help='Input JSON file with Spoonacular recipe data')
    parser.add_argument('--kroger', default="kroger_prices.json", 
                        help='Input JSON file with Kroger ingredient prices')
    parser.add_argument('--gemini', default="gemini_query_results.json", 
                        help='Input JSON file with Gemini proportion data')
    parser.add_argument('--output', default="combined_recipe_data.json", 
                        help='Output file for combined data')
    
    args = parser.parse_args()
        
    success = combine_schemas(
        args.spoonacular,
        args.kroger,
        args.gemini,
        args.output
    )
    
    if success:
        print("Data combination successful!")
    else:
        print("Data combination failed.")