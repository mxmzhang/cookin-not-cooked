import json
import pandas as pd
import os

def load_recipes(filename="recipe_results.json"):
    """Load recipes from the saved JSON file"""
    with open(filename, 'r') as f:
        return json.load(f)

def clean_recipes_to_dataframes(recipes):
    """
    Extract essential information from recipes and organize into dataframes
    Returns a tuple of dataframes: (recipes_df, ingredients_df, nutrition_df)
    """
    # Extract core recipe information
    recipe_data = []
    for recipe in recipes:
        recipe_info = {
            'id': recipe.get('id'),
            'title': recipe.get('title', ''),
            'readyInMinutes': recipe.get('readyInMinutes', 0),
            'servings': recipe.get('servings', 0),
            'sourceUrl': recipe.get('sourceUrl', ''),
            'image': recipe.get('image', ''),
        }
        recipe_data.append(recipe_info)
    
    recipes_df = pd.DataFrame(recipe_data)

    # Extract ingredient information
    ingredient_data = []
    for recipe in recipes:
        recipe_id = recipe.get('id')
        recipe_title = recipe.get('title', '')

        for category, missing_flag in [
            ('usedIngredients', 0),
            ('missedIngredients', 1),
        ]:
            for ingredient in recipe.get(category, []):
                ingredient_info = {
                    'recipe_id': recipe_id,
                    'recipe_title': recipe_title,
                    'ingredient_id': ingredient.get('id'),
                    'name': ingredient.get('name', ''),
                    'amount': ingredient.get('amount', 0),
                    'unit': ingredient.get('unit', ''),
                    'missing': missing_flag,
                    'original': ingredient.get('original', '')
                }
                ingredient_data.append(ingredient_info)

        # Handle unusedIngredients separately (no id, amount, etc.)
        for ingredient in recipe.get('unusedIngredients', []):
            ingredient_info = {
                'recipe_id': recipe_id,
                'recipe_title': recipe_title,
                'ingredient_id': None,
                'name': ingredient.get('name', ''),
                'amount': None,
                'unit': '',
                'missing': 2,  # Custom value to mark unused
                'original': ''
            }
            ingredient_data.append(ingredient_info)

    ingredients_df = pd.DataFrame(ingredient_data)

    # Extract nutrition information
    nutrition_data = []
    for recipe in recipes:
        recipe_id = recipe.get('id')
        recipe_title = recipe.get('title', '')

        nutrients = recipe.get('nutrition', {}).get('nutrients', [])
        for nutrient in nutrients:
            nutrient_info = {
                'recipe_id': recipe_id,
                'recipe_title': recipe_title,
                'nutrient': nutrient.get('name', ''),
                'amount': nutrient.get('amount', 0),
                'unit': nutrient.get('unit', ''),
                'percentOfDailyNeeds': nutrient.get('percentOfDailyNeeds', 0)
            }
            nutrition_data.append(nutrient_info)

    nutrition_df = pd.DataFrame(nutrition_data)

    return recipes_df, ingredients_df, nutrition_df

def save_dataframes_to_csv(recipes_df, ingredients_df, nutrition_df, output_dir="cleaned_data"):
    """Save dataframes to CSV files"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    recipes_df.to_csv(f"{output_dir}/recipes.csv", index=False)
    ingredients_df.to_csv(f"{output_dir}/ingredients.csv", index=False)
    nutrition_df.to_csv(f"{output_dir}/nutrition.csv", index=False)

def main():
    # Load recipes
    recipes = load_recipes()
    print(f"Loaded {len(recipes)} recipes")

    # Clean recipes and create dataframes
    recipes_df, ingredients_df, nutrition_df = clean_recipes_to_dataframes(recipes)

    print(f"Created dataframes:")
    print(f"  - Recipes: {recipes_df.shape[0]} rows, {recipes_df.shape[1]} columns")
    print(f"  - Ingredients: {ingredients_df.shape[0]} rows, {ingredients_df.shape[1]} columns")
    print(f"  - Nutrition: {nutrition_df.shape[0]} rows, {nutrition_df.shape[1]} columns")

    # Save to CSV
    save_dataframes_to_csv(recipes_df, ingredients_df, nutrition_df)
    print("Saved dataframes to CSV files in the 'cleaned_data' directory")

    # Preview
    print("\nRecipes DataFrame Preview:")
    print(recipes_df[['id', 'title', 'readyInMinutes', 'servings']].head())

    print("\nIngredients DataFrame Preview:")
    print(ingredients_df.head())

if __name__ == "__main__":
    main()
