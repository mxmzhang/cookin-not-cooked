import subprocess

subprocess.run(["python", "get_recipes.py"], check=True)
subprocess.run(["python", "format_recipe_data2.py"], check=True)
subprocess.run(["python", "kroger2.py"], check=True)
subprocess.run(["python", "gemini2.py"], check=True)
subprocess.run(["python", "final_data.py"], check=True)

