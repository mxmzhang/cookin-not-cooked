import tkinter as tk
from tkinter import ttk, messagebox
import json
import requests
import os
from functools import partial
import subprocess

class RecipeFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Recipe Finder")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        self.API_KEY = 'c85a5e59b51d495392a990aee126e526'
        self.BASE_URL = 'https://api.spoonacular.com'
        
        # Variables
        self.ingredients = []  # List of dictionaries with name and amount
        self.disliked_ingredients = []  # List of strings
        self.calorie_cap = tk.StringVar(value="0")
        self.num_recipes = tk.StringVar(value="5")
        
        # Nutrition checkboxes variables
        self.nutrition_vars = {
            "Protein": tk.BooleanVar(value=False),
            "Fat": tk.BooleanVar(value=False),
            "Carbs": tk.BooleanVar(value=False),
            "Fiber": tk.BooleanVar(value=False),
            "Vitamin A": tk.BooleanVar(value=False),
            "Vitamin C": tk.BooleanVar(value=False),
            "Vitamin D": tk.BooleanVar(value=False),
            "Calcium": tk.BooleanVar(value=False),
            "Iron": tk.BooleanVar(value=False),
        }
        
        # Create interface
        self.create_widgets()
        
    def create_widgets(self):
        # Create a notebook (tabbed interface)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab 1: Ingredient Entry
        tab1 = ttk.Frame(notebook)
        notebook.add(tab1, text="Ingredients")
        
        # Tab 2: Preferences
        tab2 = ttk.Frame(notebook)
        notebook.add(tab2, text="Preferences")
        
        # Tab 3: Results
        tab3 = ttk.Frame(notebook)
        notebook.add(tab3, text="Results")
        
        # Setup each tab
        self.setup_ingredients_tab(tab1)
        self.setup_preferences_tab(tab2)
        self.setup_results_tab(tab3)
        
        # Bottom buttons (common to all tabs)
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="Find Recipes", command=self.find_recipes).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Save Settings", command=self.save_settings).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Load Settings", command=self.load_settings).pack(side="right", padx=5)
        
    def setup_ingredients_tab(self, parent):
        # Left side - Add ingredients
        left_frame = ttk.LabelFrame(parent, text="Add Ingredients")
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Ingredient name entry
        ttk.Label(left_frame, text="Ingredient Name:").pack(anchor="w", padx=5, pady=5)
        self.ingredient_name = ttk.Entry(left_frame)
        self.ingredient_name.pack(fill="x", padx=5, pady=5)
        
        # Ingredient amount entry
        ttk.Label(left_frame, text="Amount:").pack(anchor="w", padx=5, pady=5)
        self.ingredient_amount = ttk.Entry(left_frame)
        self.ingredient_amount.pack(fill="x", padx=5, pady=5)
        
        # Add button
        ttk.Button(left_frame, text="Add Ingredient", command=self.add_ingredient).pack(padx=5, pady=10)
        
        # Ingredients list
        ttk.Label(left_frame, text="Your Ingredients:").pack(anchor="w", padx=5, pady=5)
        self.ingredients_listbox = tk.Listbox(left_frame, height=10)
        self.ingredients_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Remove button
        ttk.Button(left_frame, text="Remove Selected", command=self.remove_ingredient).pack(padx=5, pady=5)
        
        # Right side - Disliked ingredients
        right_frame = ttk.LabelFrame(parent, text="Disliked Ingredients")
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # Disliked ingredient entry
        ttk.Label(right_frame, text="Ingredient to Avoid:").pack(anchor="w", padx=5, pady=5)
        self.disliked_entry = ttk.Entry(right_frame)
        self.disliked_entry.pack(fill="x", padx=5, pady=5)
        
        # Add button
        ttk.Button(right_frame, text="Add to Disliked", command=self.add_disliked).pack(padx=5, pady=10)
        
        # Disliked list
        ttk.Label(right_frame, text="Your Disliked Ingredients:").pack(anchor="w", padx=5, pady=5)
        self.disliked_listbox = tk.Listbox(right_frame, height=10)
        self.disliked_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Remove button
        ttk.Button(right_frame, text="Remove Selected", command=self.remove_disliked).pack(padx=5, pady=5)
    
    def setup_preferences_tab(self, parent):
        # Left side - General preferences
        left_frame = ttk.LabelFrame(parent, text="General Preferences")
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Calorie cap
        ttk.Label(left_frame, text="Maximum Calories per Meal (0 for no limit):").pack(anchor="w", padx=5, pady=5)
        ttk.Entry(left_frame, textvariable=self.calorie_cap).pack(fill="x", padx=5, pady=5)
        
        # Number of recipes
        ttk.Label(left_frame, text="Number of Recipes to Find (1-20):").pack(anchor="w", padx=5, pady=5)
        ttk.Entry(left_frame, textvariable=self.num_recipes).pack(fill="x", padx=5, pady=5)
        
        # Right side - Nutritional goals
        right_frame = ttk.LabelFrame(parent, text="Nutritional Goals")
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(right_frame, text="Select nutrients you want to prioritize:").pack(anchor="w", padx=5, pady=5)
        
        # Create checkboxes for each nutrient
        for nutrient, var in self.nutrition_vars.items():
            ttk.Checkbutton(right_frame, text=nutrient, variable=var).pack(anchor="w", padx=20, pady=2)
    
    def setup_results_tab(self, parent):
        # Results area
        self.results_text = tk.Text(parent, wrap="word", height=25)
        self.results_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(self.results_text, command=self.results_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.results_text.config(yscrollcommand=scrollbar.set)
        
        # Read-only
        self.results_text.config(state="disabled")
    
    def add_ingredient(self):
        name = self.ingredient_name.get().strip()
        amount = self.ingredient_amount.get().strip()
        
        if not name:
            messagebox.showwarning("Input Error", "Please enter an ingredient name.")
            return
        
        self.ingredients.append({"name": name, "amount": amount if amount else "as needed"})
        self.ingredients_listbox.insert(tk.END, f"{name}: {amount if amount else 'as needed'}")
        
        # Clear entries for next input
        self.ingredient_name.delete(0, tk.END)
        self.ingredient_amount.delete(0, tk.END)
        self.ingredient_name.focus()
    
    def remove_ingredient(self):
        try:
            idx = self.ingredients_listbox.curselection()[0]
            self.ingredients_listbox.delete(idx)
            self.ingredients.pop(idx)
        except IndexError:
            messagebox.showwarning("Selection Error", "Please select an ingredient to remove.")
    
    def add_disliked(self):
        item = self.disliked_entry.get().strip()
        
        if not item:
            messagebox.showwarning("Input Error", "Please enter an ingredient name.")
            return
        
        self.disliked_ingredients.append(item)
        self.disliked_listbox.insert(tk.END, item)
        
        # Clear entry for next input
        self.disliked_entry.delete(0, tk.END)
        self.disliked_entry.focus()
    
    def remove_disliked(self):
        try:
            idx = self.disliked_listbox.curselection()[0]
            self.disliked_listbox.delete(idx)
            self.disliked_ingredients.pop(idx)
        except IndexError:
            messagebox.showwarning("Selection Error", "Please select an ingredient to remove.")

    def run_recipe_processing_pipeline(self):
        try:
            self.results_text.config(state="normal")
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, "Running recipe processing pipeline...\n\n")
            self.results_text.config(state="disabled")
            self.root.update()
            
            # Run each script in sequence
            steps = [
                "preprocessing/get_recipes.py",
                "preprocessing/format_recipe_data2.py",
                "preprocessing/kroger2.py",
                "preprocessing/gemini2.py",
                "preprocessing/final_data.py"
            ]
            
            for step in steps:
                self.results_text.config(state="normal")
                self.results_text.insert(tk.END, f"Running {step}...\n")
                self.results_text.config(state="disabled")
                self.root.update()
                
                subprocess.run(["python", step], check=True)
                
                self.results_text.config(state="normal")
                self.results_text.insert(tk.END, f"Completed {step}!\n\n")
                self.results_text.config(state="disabled")
                self.root.update()
            
                
            messagebox.showinfo("Success", "Recipe processing completed successfully!")
            
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Processing Error", f"Error during recipe processing: {str(e)}")
            self.results_text.config(state="normal")
            self.results_text.insert(tk.END, f"Error: {str(e)}\n")
            self.results_text.config(state="disabled")

    def save_settings(self):
        try:
            # Save current ingredients
            with open("preprocessing/inventory.txt", 'w') as f:
                for item in self.ingredients:
                    f.write(f"{item['name']}: {item['amount']}\n")
            
            # Save disliked ingredients
            with open("preprocessing/disliked.txt", 'w') as f:
                for item in self.disliked_ingredients:
                    f.write(f"{item}\n")
            
            # Save preferences
            preferences = {
                "calorie_cap": self.calorie_cap.get(),
                "num_recipes": self.num_recipes.get(),
                "nutritional_goals": {k: v.get() for k, v in self.nutrition_vars.items()}
            }
            
            with open("preprocessing/preferences.json", 'w') as f:
                json.dump(preferences, f, indent=2)
                
            messagebox.showinfo("Success", "Settings saved successfully!")
            if messagebox.askyesno("Process Recipes", "Would you like to process recipes now?"):
                self.run_recipe_processing_pipeline()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def load_settings(self):
        try:
            # Load ingredients
            try:
                self.ingredients = []
                self.ingredients_listbox.delete(0, tk.END)
                
                with open("inventory.txt", 'r') as f:
                    for line in f:
                        if ":" in line:
                            name, amount = line.strip().split(":", 1)
                            name = name.strip()
                            amount = amount.strip()
                            self.ingredients.append({"name": name, "amount": amount})
                            self.ingredients_listbox.insert(tk.END, f"{name}: {amount}")
            except FileNotFoundError:
                pass  # Ingredient file doesn't exist yet
            
            # Load disliked ingredients
            try:
                self.disliked_ingredients = []
                self.disliked_listbox.delete(0, tk.END)
                
                with open("disliked.txt", 'r') as f:
                    for line in f:
                        item = line.strip()
                        if item:
                            self.disliked_ingredients.append(item)
                            self.disliked_listbox.insert(tk.END, item)
            except FileNotFoundError:
                pass  # Disliked file doesn't exist yet
            
            # Load preferences
            try:
                with open("preferences.json", 'r') as f:
                    preferences = json.load(f)
                    
                    self.calorie_cap.set(preferences.get("calorie_cap", "0"))
                    self.num_recipes.set(preferences.get("num_recipes", "5"))
                    
                    for nutrient, value in preferences.get("nutritional_goals", {}).items():
                        if nutrient in self.nutrition_vars:
                            self.nutrition_vars[nutrient].set(value)
            except FileNotFoundError:
                pass  # Preferences file doesn't exist yet
                
            messagebox.showinfo("Success", "Settings loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {str(e)}")
    
    def find_recipes(self):
        try:
            # Validate inputs
            try:
                cal_cap = int(self.calorie_cap.get())
                if cal_cap < 0:
                    raise ValueError("Calorie cap must be positive or zero")
            except ValueError:
                messagebox.showwarning("Input Error", "Please enter a valid number for calorie cap.")
                return
                
            try:
                n_recipes = int(self.num_recipes.get())
                if n_recipes < 1 or n_recipes > 20:
                    raise ValueError("Number of recipes must be between 1 and 20")
            except ValueError:
                messagebox.showwarning("Input Error", "Please enter a valid number between 1 and 20 for recipes.")
                return
            
            # Check if we have ingredients
            if not self.ingredients:
                messagebox.showwarning("Input Error", "Please add at least one ingredient.")
                return
            
            # Get nutritional goals
            priority_nutrients = [nutrient for nutrient, var in self.nutrition_vars.items() if var.get()]
            
            self.results_text.config(state="normal")
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, "Searching for recipes...\n\n")
            self.results_text.config(state="disabled")
            self.root.update()
            
            # Search for recipes
            recipes = self.fetch_enriched_recipes(self.ingredients, max_results=n_recipes)
            
            # Filter by calorie cap if specified
            if cal_cap > 0:
                recipes = [r for r in recipes if self.get_calories(r) <= cal_cap]
            
            # Sort by nutritional goals if specified
            if priority_nutrients:
                recipes = sorted(recipes, key=lambda r: self.nutrition_score(r, priority_nutrients), reverse=True)
            
            # Display results
            self.display_results(recipes, priority_nutrients, cal_cap)
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            # Re-enable for error messages
            self.results_text.config(state="normal")
            self.results_text.insert(tk.END, f"\nError details: {str(e)}")
            self.results_text.config(state="disabled")
    
    def search_recipes_by_ingredients(self, ingredients, number=5, min_used=1):
        params = {
            'apiKey': self.API_KEY,
            'ingredients': ",".join([ing["name"] for ing in ingredients]),
            'number': number,
            'ranking': 1,
            'ignorePantry': True
        }
        response = requests.get(f"{self.BASE_URL}/recipes/findByIngredients", params=params)
        results = response.json()

        # Filter results that use at least min_used ingredients
        filtered = [
            recipe for recipe in results
            if recipe['usedIngredientCount'] >= min_used
        ]
        
        return filtered

    def get_recipe_info_bulk(self, recipe_ids):
        if not recipe_ids:
            return []

        params = {
            'apiKey': self.API_KEY,
            'ids': ",".join(map(str, recipe_ids)),
            'includeNutrition': True
        }
        response = requests.get(f"{self.BASE_URL}/recipes/informationBulk", params=params)
        return response.json()

    def fetch_enriched_recipes(self, user_ingredients, max_results=5):
        basic_results = self.search_recipes_by_ingredients(user_ingredients, number=max_results)
        recipe_ids = [r['id'] for r in basic_results]
        detailed_info = self.get_recipe_info_bulk(recipe_ids)

        # Index detailed info by ID for quick lookup
        detailed_lookup = {r['id']: r for r in detailed_info}
        enriched_results = []

        for entry in basic_results:
            recipe_id = entry['id']
            details = detailed_lookup.get(recipe_id, {})

            if not details:
                continue  # skip if no detailed info

            # Check for disliked ingredients
            skip = False
            for disliked in self.disliked_ingredients:
                disliked_lower = disliked.lower()
                # Check in title
                if disliked_lower in details.get('title', '').lower():
                    skip = True
                    break
                # Check in ingredients
                for ing in details.get('extendedIngredients', []):
                    if disliked_lower in ing.get('name', '').lower():
                        skip = True
                        break
            
            if skip:
                continue

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
    
    def get_calories(self, recipe):
        for nutrient in recipe.get('nutrition', {}).get('nutrients', []):
            if nutrient.get('name', '').lower() == 'calories':
                return nutrient.get('amount', 0)
        return 0
    
    def nutrition_score(self, recipe, priority_nutrients):
        score = 0
        for nutrient in recipe.get('nutrition', {}).get('nutrients', []):
            if nutrient.get('name', '') in priority_nutrients:
                score += nutrient.get('percentOfDailyNeeds', 0)
        return score
    
# Main application
if __name__ == "__main__":
    root = tk.Tk()
    app = RecipeFinderApp(root)
    root.mainloop()