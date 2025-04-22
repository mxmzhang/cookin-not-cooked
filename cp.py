from ortools.sat.python import cp_model
from typing import Optional, Tuple
from typing import List
import numpy as np
import json

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
    ilen = len(data["all_ingredients"])

    recipes = data.get("recipes", [])
    ingredients = data.get("all_ingredients", [])

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

    # inventory = data.get("inventory", {})
    for i in range(ilen):
        # inv_i = inventory.get(i, 0)
        # print("ing id:", i)
        usage_expr = []
        for rid in range(rlen):
            needed = 0
            for ing_r in recipes[rid]["ingredients"]:
                # print(ing_r)
                if ing_r.get("i_id") == i:
                    needed = ing_r.get("proportion")
            #         print('needed')
            # print(int(needed * 100) )
            usage_expr.append(int(needed * 100) * x[rid])


            # if rid in data["recipe_ingredients"]:
            #     for (ing_id, amt) in data["recipe_ingredients"][rid]:
            #         if ing_id == i:
            #             needed = amt
            #             break
            # usage_expr.append(needed * x[rid])

        # model.Add(sum(usage_expr) <= inv_i + b[i])
        model.Add(sum(usage_expr) <= b[i])

    # sum of cost of purchased ingredients <= budget
    cost_expr = []
    for i in range(ilen):
        cost_per_unit = ingredients[i]["unit_price"]
        cost_expr.append(cost_per_unit * b[i])
    model.Add(sum(cost_expr) <= budget*100*100)

    for rid in range(rlen):
        model.Add(round(recipes[rid].get("nutrients",{})["calories"]) * x[rid] <= calorie_cap)

    # objective function
    total_protein = model.NewIntVar(0, 10000000, "total_protein")
    model.Add(total_protein == sum(round(recipes[rid].get("nutrients", {})["protein"]) * x[rid] for rid in range(rlen)))

    total_calories = model.NewIntVar(0, 10000000, "total_calories")
    model.Add(total_calories == sum(round(recipes[rid].get("nutrients", {})["calories"]) * x[rid] for rid in range(rlen)))

    obj_expr = model.NewIntVar(-100000000, 100000000, "obj_expr")

    # make sure units of things in objective function are scaled the same
    model.Add(obj_expr == (6*total_protein - total_calories)) # test/experiment with objective functions
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
                print(f"Ingredient {i} ({ingredients[i]['name']}): {amt/100.0}")

        # for i in range(ilen):
        #     print(solver.Value(b[i]))
        print(f"Total cost used: {sum(ingredients[i].get("unit_price")*purchased[i]/(100.0*100.0) for i in range(ilen))} (Budget = {budget})")
        print("Total Protein:", solver.Value(total_protein))
        print("Total Calories:", solver.Value(total_calories))

    else:
        print("No feasible solution found.")

def main():
    file = "preprocessing/combined_recipe_data.json"
    try:
        with open(file, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: File not found at '{file}'")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{file}'")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return
    
    cp(data, 200, 460)

if __name__ == '__main__':
    main()

