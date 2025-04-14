import json
import difflib
import re
import requests
import time
from collections import defaultdict

def load_recipes_from_file(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File '{filename}' not found")
        return []

def create_initial_data_structures(recipes_from_api):
    data = {
        "recipes": {},
        "ingredients": {},
        "recipe_ingredients": {}
    }

    for recipe in recipes_from_api:
        recipe_id = str(recipe['id'])  # Ensure recipe_id is a string

        data["recipes"][recipe_id] = {
            "name": recipe['title'],
            "prep_time": recipe.get('readyInMinutes', 30),
            "servings": recipe.get('servings', 4),
            "source": recipe.get('sourceUrl'),
            "image": recipe.get('image', '')
        }
        
        if 'nutrition' in recipe and 'nutrients' in recipe['nutrition']:
            nutrition_subset = {}
            target_nutrients = ['calories', 'protein', 'carbohydrates', 'fat', 'fiber', 'sodium', 'sugar', 'cholesterol']
            
            for nutrient in recipe['nutrition']['nutrients']:
                nutrient_name = nutrient.get('name', '').lower()
                if nutrient_name in target_nutrients:
                    nutrition_subset[nutrient_name] = {
                        'amount': nutrient.get('amount', 0),
                        'unit': nutrient.get('unit', '')
                    }
            
            data["recipes"][recipe_id]["nutrition"] = nutrition_subset
        else:
            data["recipes"][recipe_id]["nutrition"] = {}
        
        recipe_ingredients = []
        all_ingredients = []
        all_ingredients = recipe.get('usedIngredients', []) + recipe.get('missedIngredients', [])
        
        for ingredient in all_ingredients:
            ingredient_id = str(ingredient.get('id'))  # Ensure ingredient_id is a string
            
            if not ingredient_id:
                continue
                
            # Add ingredient to ingredient dictionary if not already there
            if ingredient_id not in data["ingredients"]:
                data["ingredients"][ingredient_id] = {
                    "name": ingredient.get('name', '').lower(),
                    "unit_price": None,
                    "price_unit": None
                }
            
            # Add ingredient to recipe_ingredients
            amount = ingredient.get('amount', 0)
            unit = ingredient.get('unit', '')
            
            recipe_ingredients.append((ingredient_id, amount, unit))
        
        data["recipe_ingredients"][recipe_id] = recipe_ingredients
    
    return data

def normalize_ingredient_name(name):
    """Remove common descriptors and lower the case for matching"""
    name = name.lower()
    name = re.sub(r'\b(shredded|grated|chopped|minced|sliced|fresh|ground|extra|sharp|low fat|reduced fat|lean|skinless|boneless|cooked|dried|unsalted|salted|large|small|medium|thin|thick|whole|plain|raw|organic|crushed)\b', '', name)
    name = re.sub(r'\s+', ' ', name) 
    return name.strip()

def deduplicate_ingredients_auto(data, similarity_threshold=0.5):
    name_to_id = {}
    id_to_name = {}
    normalized_to_id = {}
    
    for ing_id, ing_data in list(data["ingredients"].items()):
        name = ing_data["name"]
        norm = normalize_ingredient_name(name)
        id_to_name[ing_id] = norm

        match = difflib.get_close_matches(norm, normalized_to_id.keys(), n=1, cutoff=similarity_threshold)

        if match:
            canonical_id = normalized_to_id[match[0]]
            name_to_id[ing_id] = canonical_id
            del data["ingredients"][ing_id]
        else:
            normalized_to_id[norm] = ing_id
            name_to_id[ing_id] = ing_id

    for recipe_id, ingredients in data["recipe_ingredients"].items():
        new_ingredients = []
        for ing_id, amount, unit in ingredients:
            canonical_id = name_to_id.get(ing_id, ing_id)
            new_ingredients.append((canonical_id, amount, unit))
        data["recipe_ingredients"][recipe_id] = new_ingredients

    return data

CLIENT_ID = "cooking-not-cooked-24326124303424687244626a75306c42416450477234325569686948756d4177696f31417650326846325232722e396f634d694c4f697130506d464f1737821748017711695"
CLIENT_SECRET = "7AIkjQ9JbQFWhrFx9QMlCeqbLMMPGsXwmFk0wbeS"
LOCATION_ID = "01100002"

def get_kroger_token():
    url = "https://api.kroger.com/v1/connect/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "scope": "product.compact"
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            print("[!] No token returned from Kroger API")
            return None
        return token
    except Exception as e:
        print(f"[x] Error getting Kroger token: {e}")
        return None

def search_kroger_product(name, token):
    if not token:
        print(f"[!] No valid token for searching {name}")
        return {"data": []}
        
    url = "https://api.kroger.com/v1/products"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "filter.term": name,
        "filter.locationId": LOCATION_ID,
        "filter.limit": 1
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[x] Error searching for {name}: {e}")
        return {"data": []}

def extract_price_info(product_data):
    items = product_data.get("data", [])
    if not items:
        return None

    product = items[0]
    item_list = product.get("items", [])
    
    if not item_list:
        return None

    item = item_list[0]
    price = item.get("price")
    
    if not price or "regular" not in price:
        return None
    
    unit_price_cents = int(price["regular"] * 100)
    price_unit = item.get("size", "unit")

    return {
        "unit_price": unit_price_cents,
        "price_unit": price_unit,
    }

def update_price_database(data, output_file="ingredient_prices.json"):
    token = get_kroger_token()
    if not token:
        print("[x] Failed to get Kroger API token. Prices will not be updated.")
        return
        
    prices = {}
    count = 0
    total = len(data["ingredients"])

    print(f"[*] Getting prices for {total} ingredients...")
    for ingredient_id, info in data["ingredients"].items():
        count += 1
        name = info["name"]
        try:
            print(f"[{count}/{total}] Searching for price of: {name}")
            product_data = search_kroger_product(name, token)
            price_info = extract_price_info(product_data)
            
            if price_info:
                prices[ingredient_id] = {
                    "name": name,
                    **price_info
                }
                # Update the main data structure directly
                data["ingredients"][ingredient_id]["unit_price"] = price_info["unit_price"]
                data["ingredients"][ingredient_id]["price_unit"] = price_info["price_unit"]
                print(f"[✓] Found price for: {name} - {price_info['unit_price']/100} per {price_info['price_unit']}")
            else:
                prices[ingredient_id] = {
                    "name": name,
                    "unit_price": None,
                    "price_unit": "unit",
                }
                print(f"[!] No price found for: {name}")

            time.sleep(0.2)  # Avoid rate limits

        except Exception as e:
            print(f"[x] Error for {name}: {e}")
            prices[ingredient_id] = {
                "name": name,
                "unit_price": None,
                "price_unit": "unit",
            }

    with open(output_file, "w") as f:
        json.dump(prices, f, indent=2)
    print(f"\nSaved ingredient prices to {output_file}")
    
    print("\nSample of ingredient price data:")
    sample_count = 0
    for ingredient_id, info in data["ingredients"].items():
        print(f"ID: {ingredient_id}, Name: {info.get('name')}, Price: {info.get('unit_price')}, Unit: {info.get('price_unit')}")
        sample_count += 1
        if sample_count >= 5:
            break

def call_gemini_conversion(api_key, recipe_amount, recipe_unit, kroger_unit, ingredient_name):
    """
    Use Gemini to compute the proportion of a Kroger package used in the recipe.
    """
    if not recipe_amount or not recipe_unit or not kroger_unit:
        print(f"[!] Missing data for conversion: {recipe_amount} {recipe_unit} of {ingredient_name} (package: {kroger_unit})")
        return None
        
    prompt = (
        f"A recipe uses {recipe_amount} {recipe_unit} of {ingredient_name}. "
        f"The store sells it in packages of \"{kroger_unit}\".\n\n"
        f"Convert {recipe_amount} {recipe_unit} to the equivalent in \"{kroger_unit}\" units, "
        f"then divide to get the proportion of one package used.\n\n"
        f"Return only the final answer as a decimal number between 0 and 1. No explanation. Only the number."
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

    print(f"[*] Asking Gemini: {prompt}")
    try:
        response = requests.post(url, headers=headers, params={"key": api_key}, json=data)
        
        if response.status_code != 200:
            print(f"[x] Gemini API error: {response.status_code} - {response.text}")
            return None
            
        result = response.json()
        if "candidates" not in result or not result["candidates"]:
            print(f"[x] No candidates in Gemini response: {result}")
            return None
            
        answer_text = result["candidates"][0]["content"]["parts"][0]["text"]
        print(f"[*] Gemini response!")
        
        # Extract just the number from the result
        match = re.search(r"[\d.]+", answer_text)
        if not match:
            print(f"[x] Could not find a number in Gemini response")
            return None
            
        proportion = float(match.group())
        if proportion > 1:  
            if proportion <= 100:
                proportion = proportion / 100
            else:
                print(f"[x] Proportion {proportion} is too large, capping at 1.0")
                proportion = 1.0
                
        return proportion
    except Exception as e:
        print(f"[x] Gemini Error: {e}")
        return None

def compute_proportions_and_costs(data, api_key):
    if not api_key:
        print("[x] Missing API key. Using simple unit conversion instead.")
        
    proportions = {}  # (recipe_id, ingredient_id) -> proportion
    costs = {}        # (recipe_id, ingredient_id) -> cost in dollars

    processed = 0
    total_ingredients = sum(len(ingredients) for ingredients in data["recipe_ingredients"].values())
    
    print(f"[*] Computing costs for {total_ingredients} ingredients across {len(data['recipe_ingredients'])} recipes")

    for recipe_id, ingredients in data["recipe_ingredients"].items():
        recipe_name = data["recipes"][recipe_id]["name"]
        print(f"\n[*] Processing recipe: {recipe_name}")
        
        for ingredient_id, amount, unit in ingredients:
            processed += 1
            ingredient_id = str(ingredient_id)  
            
            if ingredient_id not in data["ingredients"]:
                print(f"[!] Ingredient ID {ingredient_id} not found in ingredients data")
                continue
                
            ing_info = data["ingredients"][ingredient_id]
            name = ing_info.get("name", "unknown ingredient")
            unit_price_cents = ing_info.get("unit_price")
            kroger_unit = ing_info.get("price_unit")

            print(f"[{processed}/{total_ingredients}] Processing {name}: {amount} {unit}")
            
            if not unit_price_cents or not kroger_unit:
                print(f"[!] Missing price ({unit_price_cents}) or unit ({kroger_unit}) for {name}")
                continue
    
            try:
                proportion = call_gemini_conversion(
                    api_key=api_key,
                    recipe_amount=amount,
                    recipe_unit=unit,
                    kroger_unit=kroger_unit,
                    ingredient_name=name
                    )
                    
                if proportion is None:
                    print(f"[!] Gemini API failed, using fallback for {name}")
                    
            except Exception as e:
                print(f"[!] Error calling Gemini API: {e}. Using fallback conversion.")
                

            key = (recipe_id, ingredient_id)
            proportions[key] = proportion
            cost_dollars = (proportion * unit_price_cents) / 100
            costs[key] = round(cost_dollars, 2)
            print(f"[✓] {name}: {proportion:.4f} of package = ${cost_dollars:.2f}")

    print(f"\n[*] Computed costs for {len(costs)} ingredients")
    return proportions, costs

def generate_recipe_cost_summary(data, proportions, costs, output_file="recipe_costs.json"):
    """
    Create a JSON object with per-recipe ingredient costs and total cost.
    Save the output to a file.
    """
    summary = {}

    for recipe_id, ingredients in data["recipe_ingredients"].items():
        recipe_name = data["recipes"][recipe_id]["name"]
        print(f"Generating cost summary for: {recipe_name}")
        
        total_cost = 0.0
        ingredient_costs = []

        for ing_tuple in ingredients:
            ingredient_id, amount, unit = ing_tuple
            ingredient_id = str(ingredient_id)  # Ensure consistent string IDs
            
            if ingredient_id not in data["ingredients"]:
                print(f"Warning: Ingredient ID {ingredient_id} not found in data dictionary")
                continue
                
            ingredient_data = data["ingredients"][ingredient_id]
            name = ingredient_data.get("name", "unknown")
            package_unit = ingredient_data.get("price_unit", "unit")

            key = (recipe_id, ingredient_id)
            proportion = proportions.get(key)
            cost = costs.get(key)

            if proportion is not None and cost is not None:
                total_cost += cost
                ingredient_costs.append({
                    "ingredient_id": ingredient_id,
                    "name": name,
                    "amount_used": amount,
                    "unit": unit,
                    "package_unit": package_unit,
                    "proportion_used": round(proportion, 4),
                    "estimated_cost": round(cost, 2)
                })
            else:
                print(f"No cost data for {name} in {recipe_name}")
                ingredient_costs.append({
                    "ingredient_id": ingredient_id,
                    "name": name,
                    "amount_used": amount,
                    "unit": unit,
                    "package_unit": package_unit,
                    "proportion_used": None,
                    "estimated_cost": None
                })

        summary[recipe_id] = {
            "recipe_name": recipe_name,
            "total_cost": round(total_cost, 2),
            "ingredients": ingredient_costs
        }

    # Save to file
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"[✓] Saved recipe cost summary to {output_file}")
    

def test_gemini_api(api_key):
    """Test the Gemini API connectivity"""
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": "Say hello"}]}]
    }
    
    try:
        response = requests.post(url, headers=headers, params={"key": api_key}, json=data)
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print("[✓] Gemini API test successful!")
            return True
        else:
            print(f"[x] Gemini API test failed: {response.text}")
            return False
    except Exception as e:
        print(f"[x] Gemini API test error: {e}")
        return False

if __name__ == "__main__":
    filename = "recipe_results.json"
    recipes = load_recipes_from_file(filename)
    API_KEY = "AIzaSyAy2D2jxTMLUpow2jsf6IIjC2XR6sENRDs" 

    print("[*] Testing Gemini API connection...")
    api_working = test_gemini_api(API_KEY)
    
    if recipes:
        print(f"Loaded {len(recipes)} recipes from {filename}")
        
        data = create_initial_data_structures(recipes)
        print(f"Initial data structures created with {len(data['ingredients'])} ingredients")
        
        data = deduplicate_ingredients_auto(data)
        print(f"After deduplication: {len(data['ingredients'])} unique ingredients")
        
        print(f"Processed {len(data['recipes'])} recipes")
        
        with open("structured_recipe_data_pre_pricing.json", "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nStructured data before pricing saved to structured_recipe_data_pre_pricing.json")
        
        update_price_database(data)
        with open("structured_recipe_data.json", "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nStructured data with pricing saved to structured_recipe_data.json")
        
        proportions, costs = compute_proportions_and_costs(data, API_KEY)
        generate_recipe_cost_summary(data, proportions, costs)
    else:
        print("No recipes loaded. Please check the filename and file format.")