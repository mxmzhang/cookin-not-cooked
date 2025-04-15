import json
import difflib
import re
from collections import defaultdict


def load_recipes_from_file(filename):
    """Load recipes from a JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File '{filename}' not found")
        return []

def create_initial_data_structures(recipes_from_api):
    """Create the initial data structure from the recipes"""
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
    """Deduplicate ingredients by similarity of name"""
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

if __name__ == "__main__":
    filename = "recipe_results.json"
    recipes = load_recipes_from_file(filename)
    
    if recipes:
        print(f"Loaded {len(recipes)} recipes from {filename}")
        
        data = create_initial_data_structures(recipes)
        print(f"Initial data structures created with {len(data['ingredients'])} ingredients")
        
        data = deduplicate_ingredients_auto(data)
        print(f"After deduplication: {len(data['ingredients'])} unique ingredients")
        
        print(f"Processed {len(data['recipes'])} recipes")
        
        # Save data
        with open("recipe_data_cleaned.json", "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nStructured data before pricing saved to recipe_data_cleaned.json")
        
    else:
        print("No recipes loaded. Please check the filename and file format.")