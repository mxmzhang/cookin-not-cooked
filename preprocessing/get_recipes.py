import requests
import json
import os 

API_KEY = '2add8db43662436abe6dc85a5ae84a30'
BASE_URL = 'https://api.spoonacular.com'

def get_ingredients_with_amounts():
    print("Enter the ingredients you have (name and amount). Type 'done' to finish:")
    ingredients = []
    while True:
        name = input("Ingredient name: ").strip()
        if name.lower() == 'done':
            break
        amount = input(f"Amount of {name}: ").strip()
        ingredients.append({"name": name, "amount": amount})
    return ingredients

def get_disliked_ingredients():
    print("\nEnter ingredients you don't like (one at a time). Type 'done' to finish:")
    dislikes = []
    while True:
        item = input("Disliked ingredient: ").strip()
        if item.lower() == 'done':
            break
        dislikes.append(item)
    return dislikes
def get_user_preferences(filename = "cap.txt"):
    print("\n=== Welcome to Recipe Finder ===")
    print("This program will help you find recipes using ingredients you already have!")
    
    # Get calorie preference
    while True:
        try:
            calorie_cap = input("\nWhat's your maximum calorie limit per meal? (Enter a number, or 0 for no limit): ")
            calorie_cap = int(calorie_cap)
            if calorie_cap < 0:
                print("Please enter a positive number or 0 for no limit.")
                continue
            break
        except ValueError:
            print("Please enter a valid number.")
    
    # Get number of recipes
    while True:
        try:
            num_recipes = input("\nHow many recipe suggestions would you like to see? (1-20): ")
            num_recipes = int(num_recipes)
            if num_recipes < 1 or num_recipes > 20:
                print("Please enter a number between 1 and 20.")
                continue
            break
        except ValueError:
            print("Please enter a valid number.")
    with open(filename, 'w') as f:
        f.write(f"{calorie_cap}\n{num_recipes}\n")
    return calorie_cap, num_recipes

# Example usage
preferences = get_user_preferences()
my_ingredients = get_ingredients_with_amounts()
disliked_ingredients = get_disliked_ingredients()

print("\nIngredients you have:")
for ing in my_ingredients:
    print(f"- {ing['name']}: {ing['amount']}")

print("\nIngredients you don't like:")
for item in disliked_ingredients:
    print(f"- {item}")

def save_current_ingredients_to_file(my_ingredients, filename="inventory.txt"):
    with open(filename, 'w') as f:
        for item in my_ingredients:
            f.write(f"{item['name']}: {item['amount']}\n")
    print(f"Pantry ingredients saved to {filename}")


def save_disliked_ingredients_to_file(disliked_ingredients, filename="disliked.txt"):
    with open(filename, 'w') as f:
        for item in disliked_ingredients:
            f.write(f"{item}\n")
    print(f"Disliked ingredients saved to {filename}")



#my_ingredients = ['broccoli', 'pasta', 'potato', 'egg', 'tomato', 'onion', 'chicken breast']
my_ingredients = []
def search_recipes_by_ingredients(ingredients, number = 1, min_used=2):
    params = {
        'apiKey': API_KEY,
        #'ingredients': ",".join([ing["name"] for ing in ingredients]),
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

my_ingredients = ['broccoli', 'pasta', 'potato', 'egg', 'tomato', 'onion', 'chicken breast']
 
if __name__ == "__main__":
    output_file = "recipe_results.json"
    #get_user_preferences()
    #save_disliked_ingredients_to_file(disliked_ingredients, filename="disliked.txt")
    #save_current_ingredients_to_file(my_ingredients, filename="inventory.txt")
    recipes = fetch_enriched_recipes(my_ingredients)
    print(f"Found {len(recipes)} recipes")
    for i, recipe in enumerate(recipes[:3], 1): 
        print(f"{i}. {recipe['title']}")
    save_results_to_file(recipes, output_file)
    
    print(f"\nResults have been saved to {os.path.abspath(output_file)}")
