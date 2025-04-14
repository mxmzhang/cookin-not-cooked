from ortools.sat.python import cp_model
from typing import Optional, Tuple
from typing import List
import numpy as np

# assume that we have a list of recipes from spoonacular called recipes, a 2D matrix
def process_recipes(recipes):
    ingredient_dict = {}
    protein_list = []
    calories_list = []
    ingredient_index = 0

    for recipe in recipes:

        # Track unique ingredients
        for ingredient in recipe.get("extendedIngredients", []):
            name = ingredient.get("nameClean")
            if name and name not in ingredient_dict:
                ingredient_dict[name] = ingredient_index
                ingredient_index += 1

        # Extract protein and calories
        protein = 0
        calories = 0
        for nutrient in recipe.get("nutrition", {}).get("nutrients", []):
            name = nutrient.get("name", "").lower()
            if name == "protein":
                protein += nutrient.get("amount", 0)
            elif name == "calories":
                calories += nutrient.get("amount", 0)

        protein_list.append(protein)
        calories_list.append(calories)

    num_recipes = len(recipes)
    num_ingredients = len(ingredient_dict)
    
    ingredient_matrix = np.zeros((num_recipes, num_ingredients))

    for i, recipe in enumerate(recipes):
        for ingredient in recipe.get("extendedIngredients", []):
            name = ingredient.get("nameClean")
            index = ingredient_dict.get(name)

            amount_in_grams = ingredient.get("measures", {}).get("metric", {}).get("amount", 0)
            if index is not None:
                ingredient_matrix[i, index] = amount_in_grams


    return ingredient_dict, protein_list, calories_list, ingredient_matrix