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

        for ingredient in recipe.get("extendedIngredients", []):
            name = ingredient.get("nameClean")
            if name and name not in ingredient_dict:
                ingredient_dict[name] = ingredient_index
                ingredient_index += 1

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

def cp(data, budget, calorie_cap, chosen_meals = 5):
    model = cp_model.CpModel()
    rlen = len(data["recipes"])
    ilen = len(data["ingredients"])

    recipes = data.get("recipes", {})
    ingredients = data.get("ingredients", {})

    # x_r: 0/1 if we choose recipe r
    x = {}
    for rid in range(rlen):
        x[rid] = model.NewBoolVar(f"x_r{rid}")

    # b_i: integer variable for how many extra units of ingredient i to buy
    b = {}
    k = {}
    for i in range(ilen):
        # can only buy in units of 100, since we will be scaling all units by 100
        k[i] = model.NewIntVar(0, 1000, f"k_i{i}") 
        b[i] = model.NewIntVar(0, 100000, f"b_i{i}")
        model.Add(b[i] == 100 * k[i])

    model.Add(sum(x[rid] for rid in range(rlen)) == chosen_meals)

    # sum of usage for each ingredient i across chosen recipes <= inventory + b[i]
    inventory = data.get("inventory", {})
    for i in range(ilen):
        inv_i = inventory.get(i, 0)
        usage_expr = []
        for rid in range(rlen):
            needed = 0

            for ing_r in recipes.get("ingredients", {}):
                if ing_r.get("i_id") == i:
                    needed = ing_r.get("proportion")
            usage_expr.append(needed * x[rid])


            # if rid in data["recipe_ingredients"]:
            #     for (ing_id, amt) in data["recipe_ingredients"][rid]:
            #         if ing_id == i:
            #             needed = amt
            #             break
            # usage_expr.append(needed * x[rid])

        model.Add(sum(usage_expr) <= inv_i + b[i])

    # sum of cost of purchased ingredients <= budget
    cost_expr = []
    for i in range(ilen):
        cost_per_unit = ingredients[i]
        cost_expr.append(cost_per_unit * b[i])
    model.Add(sum(cost_expr) <= budget)

    for rid in range(rlen):
        model.Add(recipes[rid].get("nutrition",{})["calories"] * x[rid] <= calorie_cap)

    # objective function
    total_protein = model.NewIntVar(0, 10000000, "total_protein")
    model.Add(total_protein == sum(recipes[rid].get("nutrition", {})["protein"] * x[rid] for rid in len(rlen)))

    total_calories = model.NewIntVar(0, 10000000, "total_calories")
    model.Add(total_calories == sum(recipes[rid].get("nutrition", {})["calories"] * x[rid] for rid in len(rlen)))

    obj_expr = model.NewIntVar(-100000000, 100000000, "obj_expr")

    # make sure units of things in objective function are scaled the same
    model.Add(obj_expr == (3*total_protein - total_calories)) # test/experiment with objective functions
    model.Maximize(obj_expr)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("Solution status:", solver.StatusName())
        chosen = []
        for rid in range(rlen):
            if solver.Value(x[rid]) == 1:
                chosen.append(rid)

        purchased = {}
        for i in range(ilen):
            purchased[i] = solver.Value(b[i])

        print(f"Chosen recipe IDs: {chosen}")
        for rid in chosen:
            print(f"  -> {data['recipes'][rid]['name']}")

        print("Extra purchased amounts:")
        for i in range(ilen):
            amt = purchased[i]
            if amt > 0:
                print(f"   Ingredient {i} ({data['ingredients'][i]['name']}): {amt}")

        print(f"Total cost used: {sum(ingredients[i].get("price")*purchased[i] for i in range(ilen))} (Budget = {budget})")
        print("Total Protein:", solver.Value(total_protein))
        print("Total Calories:", solver.Value(total_calories))

    else:
        print("No feasible solution found.")