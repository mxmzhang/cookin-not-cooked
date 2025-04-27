import json
import difflib
import re
from collections import defaultdict


def load_recipes_from_file(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File '{filename}' not found")
        return []

def normalize_ingredient_name(name):
    name = name.lower()
    name = re.sub(r'\b(shredded|grated|chopped|minced|sliced|fresh|ground|extra|sharp|low fat|reduced fat|lean|skinless|boneless|cooked|dried|unsalted|salted|large|small|medium|thin|thick|whole|plain|raw|organic|crushed)\b', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()

def create_structured_data(recipes_from_api):
    result = {
        "recipes": [],
        "all_ingredients": [],
        "recipe_ingredients": []
    }
    
    # track temporary ingredient data before deduplication
    temp_ingredients = {}
    recipe_to_ingredients = {}
    
    # extract all ingredients with their names
    for recipe in recipes_from_api:
        recipe_id = str(recipe['id'])
        
        # create recipe entry
        recipe_entry = {
            "r_id": recipe_id,
            "name": recipe['title']
        }
        
        # extract nutrients 
        if 'nutrition' in recipe and 'nutrients' in recipe['nutrition']:
            nutrients = {}
            for nutrient in recipe['nutrition']['nutrients']:
                nutrient_name = nutrient.get('name', '').lower()
                if nutrient_name in ['protein', 'cholesterol', 'fiber', 'calories']:
                    nutrients[nutrient_name] = nutrient.get('amount', 0)
            
            recipe_entry["nutrients"] = nutrients
        else:
            recipe_entry["nutrients"] = {"protein": 0, "cholesterol": 0, "fiber": 0, "calories": 0}
        
        result["recipes"].append(recipe_entry)
        
        # process ingredients
        all_ingredients = recipe.get('usedIngredients', []) + recipe.get('missedIngredients', [])
        recipe_to_ingredients[recipe_id] = []
        
        for ingredient in all_ingredients:
            ing_id = str(ingredient.get('id'))
            if not ing_id:
                continue
            
            # store this ingredient temporarily
            if ing_id not in temp_ingredients:
                temp_ingredients[ing_id] = {
                    "name": ingredient.get('name', '').lower(),
                    "normalized_name": normalize_ingredient_name(ingredient.get('name', ''))
                }
            
            # add to this recipe's ingredients
            recipe_to_ingredients[recipe_id].append({
                "ori_ing_id": ing_id,
                "quantity": ingredient.get('amount', 0),
                "unit": ingredient.get('unit', '')
            })
    
    # deduplicate ingredients based on normalized names
    normalized_to_id = {}
    id_mapping = {}  # maps original ids to deduplicated ids
    next_i_id = 0
    
    for ori_id, ing_data in temp_ingredients.items():
        norm_name = ing_data["normalized_name"]
        
        # check for similar existing ingredients
        match = None
        for existing_norm in normalized_to_id:
            similarity = difflib.SequenceMatcher(None, norm_name, existing_norm).ratio()
            if similarity > 0.5: 
                match = existing_norm
                break
        
        if match:
            # map this ingredient to existing one
            id_mapping[ori_id] = normalized_to_id[match]
        else:
            # create new deduplicated ingredient
            normalized_to_id[norm_name] = next_i_id
            id_mapping[ori_id] = next_i_id
            
            # add to final ingredients list
            result["all_ingredients"].append({
                "i_id": next_i_id,
                "name": ing_data["name"]
            })
            next_i_id += 1
    
    #build recipe_ingredients with deduplicated ingredient IDs
    for recipe_id, ingredients in recipe_to_ingredients.items():
        recipe_ingredients_entry = {
            "r_id": recipe_id,
            "ingredients": []
        }
        
        for ing in ingredients:
            ori_ing_id = ing["ori_ing_id"]
            deduplicated_i_id = id_mapping.get(ori_ing_id)
            ingredient_name = ""
            for all_ing in result["all_ingredients"]:
                if all_ing["i_id"] == deduplicated_i_id:
                    ingredient_name = all_ing["name"]
                    break
            if deduplicated_i_id is not None:
                
                recipe_ingredients_entry["ingredients"].append({
                    "name": ingredient_name,
                    "ri_id": ori_ing_id,  
                    "i_id": deduplicated_i_id, 
                    "quantity": ing["quantity"],
                    "unit": ing["unit"]
                })
        
        result["recipe_ingredients"].append(recipe_ingredients_entry)
    
    print(f"deduplication: {len(temp_ingredients)} original ingredients reduced to {len(result['all_ingredients'])} unique ingredients")
    return result

if __name__ == "__main__":
    filename = "recipe_results.json"
    recipes = load_recipes_from_file(filename)
    
    if recipes:
        print(f"loaded {len(recipes)} recipes from {filename}")
        
        # Create the new structured data format
        structured_data = create_structured_data(recipes)
        print(f"{len(structured_data['recipes'])} recipes, {len(structured_data['all_ingredients'])} unique ingredients")
        
        # Save data
        with open("spoonacular_structured_data.json", "w") as f:
            json.dump(structured_data, f, indent=2)
        print(f"\ndata saved to spoonacular_structured_data.json")
        
    else:
        print("no recipes loaded")