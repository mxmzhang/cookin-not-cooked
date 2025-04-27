import subprocess

subprocess.run(["python", "preprocessing/get_recipes.py"], check=True)
subprocess.run(["python", "preprocessing/format_recipe_data2.py"], check=True)
subprocess.run(["python", "preprocessing/kroger2.py"], check=True)
subprocess.run(["python", "preprocessing/gemini2.py"], check=True)
subprocess.run(["python", "preprocessing/final_data.py"], check=True)

