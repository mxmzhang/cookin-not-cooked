import requests
import json
import os 

API_KEY = 'c85a5e59b51d495392a990aee126e526'
BASE_URL = 'https://api.spoonacular.com'

my_ingredients = ['broccoli', 'shrimp', 'rice', 'egg']

def search_recipes_by_ingredients(ingredients, number = 1, min_used=2):
    params = {
        'apiKey': API_KEY,
        'ingredients': ",".join(ingredients),
        'number': number,
        'ranking': 1,
        'offset': 3,
        'ignorePantry': True
    }
    response = requests.get(f"{BASE_URL}/recipes/findByIngredients", params=params)
    results = response.json()

    filtered = [
        recipe for recipe in results
        if recipe['usedIngredientCount'] >= min_used
    ]
    
    return filtered


def get_recipe_info_bulk(recipe_ids):

    if not recipe_ids:
        return []

    params = {
        'apiKey': API_KEY,
        'ids': ",".join(map(str, recipe_ids)),
        'includeNutrition': True
    }
    response = requests.get(f"{BASE_URL}/recipes/informationBulk", params=params)
    return response.json()

def fetch_enriched_recipes(user_ingredients, max_results=15):
    basic_results = search_recipes_by_ingredients(user_ingredients, number=max_results)
    recipe_ids = [r['id'] for r in basic_results]
    detailed_info = get_recipe_info_bulk(recipe_ids)

    # Index detailed info by ID for quick lookup
    detailed_lookup = {r['id']: r for r in detailed_info}
    enriched_results = []

    for entry in basic_results:
        recipe_id = entry['id']
        details = detailed_lookup.get(recipe_id, {})

        if not details:
            continue  # skip if no detailed info

        enriched = {
            'id': recipe_id,
            'title': details.get('title', entry.get('title', '')),
            'readyInMinutes': details.get('readyInMinutes', 0),
            'servings': details.get('servings', 0),
            'sourceUrl': details.get('sourceUrl', ''),
            'image': details.get('image', ''),
            
            'usedIngredients': [
                {
                    'id': ing.get('id'),
                    'name': ing.get('name', ''),
                    'amount': ing.get('amount', 0),
                    'unit': ing.get('unit', ''),
                    'original': ing.get('original', '')
                }
                for ing in entry.get('usedIngredients', [])
            ],
            'missedIngredients': [
                {
                    'id': ing.get('id'),
                    'name': ing.get('name', ''),
                    'amount': ing.get('amount', 0),
                    'unit': ing.get('unit', ''),
                    'original': ing.get('original', '')
                }
                for ing in entry.get('missedIngredients', [])
            ],
            'unusedIngredients': [
                {
                    'name': ing.get('name', '')
                }
                for ing in entry.get('unusedIngredients', [])
            ],
            'nutrition': {
                'nutrients': [
                    {
                        'name': n.get('name', ''),
                        'amount': n.get('amount', 0),
                        'unit': n.get('unit', ''),
                        'percentOfDailyNeeds': n.get('percentOfDailyNeeds', 0)
                    }
                    for n in details.get('nutrition', {}).get('nutrients', [])
                ]
            }
        }

        enriched_results.append(enriched)

    return enriched_results

def save_results_to_file(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Results saved to {filename}")

def load_results_from_file(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File {filename} not found")
        return None
    
if __name__ == "__main__":
    output_file = "recipe_results.json"
    
    recipes = fetch_enriched_recipes(my_ingredients)
    
    print(f"Found {len(recipes)} recipes")
    for i, recipe in enumerate(recipes[:3], 1): 
        print(f"{i}. {recipe['title']}")
    
    save_results_to_file(recipes, output_file)
    
    print(f"\nResults have been saved to {os.path.abspath(output_file)}")
