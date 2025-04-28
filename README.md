# Cookin' Not Cooked
This project is a diet optimizer tool that helps users discover new recipes while staying within their budget and health goals using constraint programming.

## File structure
C:.
│   cp.py                             -> constraint solver file
│   cp_testing.ipynb                  -> hard-coded small test cases
│   graph.py
│   README.md                                        
│
├───preprocessing
│       allergies.txt                     -> editable user-input of allergies
│       cap.txt                           -> editable user-input file of parameters (calories/meal, # meals, budget)
|       disliked.txt                      -> editable user-input file of disliked foods
│       inventory.txt                     -> editable user-input file of currently owned ingredients with amounts
|
│       pipeline.py                       -> executable to run all preprocessing steps at once with user input
│       get_recipes.py                    -> query Spoonacular for relevant recipes
│       recipe_results.json               -> results from Spoonacular API recipes queries
│       format_recipe_data2.py            -> clean recipe data from Spoonacular
│       spoonacular_structured_data.json  -> results from cleaning Spoonacular recipe data
│       kroger2.py                        -> query Kroger API for ingredient prices
│       kroger_prices.json                -> results from Kroger pricing queries
│       gemini2.py                        -> query Gemini to get ingredient proportions / recipe
│       gemini_query_results.json         -> results from Gemini proportions queries
│       final_data.py                     -> executable to consolidate and format recipe data
│       combined_recipe_data.json         -> final recipe data schema
│
└───__pycache__
        cp.cpython-312.pyc
## Try it out!
Pre-Processing Data
The recipe data files are currently loaded with a big dataset containing 100 (the maximum amount) recipes pre-set on an inventory list of pasta, 
broccoli, eggs, tomato, onion, potato and chicken breast. This is just because it takes ~10 minutes to process 100 recipes. 
The recipes can also be changed by running 'python .\pipeline.py' in the preprocessing folder (cd .\preprocessing\) and following the prompts in the terminal for 
calories per meal, budget and number of meals as well as inventory ingredients, disliked ingredients and allergies. 
The final JSON data scheme is held in spoonacular_structured_data.json and serves as the recipes that the CP solve will use.

If you feel that the recipes generated are good, and you only want to change the constraints passed to the CP solver, then you can edit 'inventory.txt', 'disliked.txt', 'allergies.txt', and 'cap.txt' as you want. They are structured as follows, or see the original files for inspiration:
    inventory.txt contains lines of the form 'ingredient: amount' where the amount is per unit as sold by Kroger, for example 6 eggs should be inputted as 'eggs: 0.5'
    disliked.txt contains a list of disliked foods each on a new line
    allergies.txt contains a list of foods the user is allergic to each on a new line
    cap.txt is of the form '{calories per meal cap}, {number of recipes}, {budget}'

Constriant Solver
Once you are happy with the recipes list and constraints, run 'python .\cp.py' in the main project folder to see the constrain solver's output which will be of the form
Solution status: OPTIMAL/FEASIBLE
Chosen recipe IDs: [r_id1, r_id2...]
  -> recipe 1
  -> recipe 2
  -> ...
Extra purchased amounts:
Total cost used: 0.0 (Budget = )
Total Protein: 
Total Calories:
Total Cholestrol:
Calories to Protein Ratio: 
Calories to Cholesterol Ratio:

## Our Tests
The hard-coded test cases are located in 'cp_testing.ipynb' and can be run just by clicking through the cells.