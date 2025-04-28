from ortools.sat.python import cp_model
from typing import Optional, Tuple
from typing import List
import numpy as np
import json
import time
import math as math

def preprocess_inventory(filename, data):
    ingredients = data["all_ingredients"]
    inventory = dict()
    for ingrli in ingredients:
        inventory[ingrli["i_id"]] = {"name": ingrli["name"], "amount":0}
    with open(filename, "r") as file:
        for line in file:
            ingr = line.strip().split(": ")
            for ingrli in ingredients:
                if ingr[0] == ingrli["name"]:
                    inventory[ingrli["i_id"]]["amount"] = float(ingr[1])
    return inventory

def preprocess_disliked(filename, data):
    ingredients = data["all_ingredients"]
    disliked = dict()
    with open(filename, 'r') as file:
        for line in file:
            ingr = line.strip()
            for ingrli in ingredients:
                if ingr == ingrli["name"]:
                    disliked[ingrli["name"]] = ingrli["i_id"]
    return disliked

def preprocess_allergies(filename, data):
    ingredients = data["all_ingredients"]
    allergies = set()
    with open(filename, 'r') as file:
        for line in file:
            allergen = line.strip()
            allergies.add(allergen)
    return allergies

def cp(data, budget, calorie_cap, inventory, disliked_ct, allergies, chosen_meals = 5):
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
    for i in range(ilen):
        inv_i = inventory[i]["amount"]
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

        model.Add(sum(usage_expr) <= int(inv_i*100) + b[i])
        # model.Add(sum(usage_expr) <= b[i])

    # sum of cost of purchased ingredients <= budget
    cost_expr = []
    for i in range(ilen):
        cost_per_unit = ingredients[i]["unit_price"]
        cost_expr.append(cost_per_unit * b[i])
    model.Add(sum(cost_expr) <= budget*100*100)

    for rid in range(rlen):
        model.Add(round(recipes[rid].get("nutrients",{})["calories"]) * x[rid] <= calorie_cap)


    # allergy constraint
    for rid in range(rlen):
        recipe = recipes[rid]
        for ingr in recipe["ingredients"]:
            if ingr["name"] in allergies:
                model.Add(x[rid] == 0)
                break


    # objective function
    # soft constraint calculations
    dislike_expr = []
    for rid in range(rlen):
        dislike_expr.append(disliked_ct[rid] * x[rid])

    dislike_sum = sum(dislike_expr)

    # protein/calorie variables
    total_protein = model.NewIntVar(0, 10000000, "total_protein")
    model.Add(total_protein == sum(round(recipes[rid].get("nutrients", {})["protein"]) * x[rid] for rid in range(rlen)))

    total_calories = model.NewIntVar(0, 10000000, "total_calories")
    model.Add(total_calories == sum(round(recipes[rid].get("nutrients", {})["calories"]) * x[rid] for rid in range(rlen)))

    total_chol = model.NewIntVar(0, 10000000, "total_cholesterol")
    model.Add(total_chol == sum(round(recipes[rid].get("nutrients", {})["cholesterol"]) * x[rid] for rid in range(rlen)))

    obj_expr = model.NewIntVar(-100000000, 100000000, "obj_expr")

    # make sure units of things in objective function are scaled the same
    model.Add(obj_expr == (4*total_protein - 1*total_chol - 50 * dislike_sum)) # test/experiment with objective functions
    # model.Add(obj_expr == (40*total_protein - total_calories - 5*total_chol - 1000 * dislike_sum)) # test/experiment with objective functions
    # model.Add(obj_expr == (80*total_protein - total_calories - 10*total_chol - 1000 * dislike_sum)) # test/experiment with objective functions
    # model.Add(obj_expr == (50*total_protein - total_calories - 15*total_chol - 1000 * dislike_sum))
    # model.Add(obj_expr == (70*total_protein - total_calories - 20*total_chol - 1000 * dislike_sum)) # test/experiment with objective functions
    # model.Add(obj_expr == (80*total_protein - total_calories - 20*total_chol - 1000 * dislike_sum))
    # model.Add(obj_expr == (63*total_protein - total_calories - 15*total_chol - 1000 * dislike_sum))
    # model.Add(obj_expr == (80*total_protein - total_calories - 20*total_chol - 1000 * dislike_sum))
    # model.Add(obj_expr == (55*total_protein - total_calories - 20*total_chol - 1000 * dislike_sum))
    # model.Add(obj_expr == (100*total_protein - total_calories - 30*total_chol - 1000 * dislike_sum))
    # obj_expr = 145*total_protein - total_calories - 49*total_calories - 1000*dislike_sum

    # for p in range(40,150,5):
    #     for c in range(10,50,5):
    #         obj_expr = p*total_protein - total_calories - c*total_calories - 1000*dislike_sum
    #         model.Maximize(obj_expr)

    #         solver = cp_model.CpSolver()
    #         status = solver.Solve(model)

    #         mindist = math.inf
    #         minp = -1
    #         minc = -1
    #         if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    #             dist = math.sqrt((10- solver.Value(total_calories) / solver.Value(total_protein))**2+ 
    #                 (10-solver.Value(total_calories) / solver.Value(total_chol))**2)
    #             if dist < mindist:
    #                 mindist = dist
    #                 minp = p
    #                 minc = c
    #             if p == 100 and c == 25:
    #                 print("hello")
    #                 print(dist)
    # print(minp)
    # print(minc)
    # print(mindist)
    # return

            

    
    # obj_expr = (int(223.3 - 0.7868*calorie_cap + 0.0009171*calorie_cap*calorie_cap))*total_protein - total_calories - (int(129.1 - 0.4538*calorie_cap + 0.0004523*calorie_cap*calorie_cap))*total_chol - 1000 * dislike_sum
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
        print("Total Cholestrol:", solver.Value(total_chol))

        print("Calories to Protein Ratio:", solver.Value(total_calories) / solver.Value(total_protein) )
        print("Calories to Cholesterol Ratio:", solver.Value(total_calories) / solver.Value(total_chol))

    else:
        print("No feasible solution found.")


def main(mainfile = "preprocessing/combined_recipe_data.json", 
        inventoryfile = "preprocessing/inventory.txt",
        dislikedfile = "preprocessing/disliked.txt",
        capfile = "preprocessing/cap.txt",
        allergyfile = "preprocessing/allergies.txt"):
    '''
    mainfile = "preprocessing/combined_recipe_data.json"
    inventoryfile = "preprocessing/inventory.txt"
    dislikedfile = "preprocessing/disliked.txt"
    capfile = "preprocessing/cap.txt"
    allergyfile = "preprocessing/allergies.txt"
    '''
    try:
        with open(mainfile, 'r') as file:
            data = json.load(file)
        inventory = preprocess_inventory(inventoryfile, data)
        disliked = preprocess_disliked(dislikedfile, data)
        allergies = preprocess_allergies(allergyfile, data)
        recipes = data.get("recipes", [])
        disliked_ct = []
        for recipe in recipes:
            count = 0
            for ing in recipe["ingredients"]:
                if ing["name"] in disliked:
                    count += 1
            disliked_ct.append(count)
        with open(capfile, 'r') as file2:
            for line in file2:
                line = line.strip()
                info = line.split(",")
                break
        calorie_cap = int(info[0])
        recipe_num = int(info[1])
        budget = int(info[2])
        # print(calorie_cap, recipe_num, budget)

    except FileNotFoundError:
        print(f"Error: File not found")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return
    start = time.time()
    cp(data, budget, calorie_cap, inventory, disliked_ct, allergies, recipe_num)
    end = time.time()
    execution_time = end - start
    print(f"\nexecution time: {execution_time:.4f} seconds")

if __name__ == '__main__':
    main("preprocessing/combined_recipe_data.json", 
         "preprocessing/inventory.txt",
        "preprocessing/disliked.txt",
        "preprocessing/cap.txt",
        "preprocessing/allergies.txt")

