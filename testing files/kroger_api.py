import requests
import json
import time

# Kroger API Credentials (from your Kroger Developer account)
CLIENT_ID = "cooking-not-cooked-24326124303424687244626a75306c42416450477234325569686948756d4177696f31417650326846325232722e396f634d694c4f697130506d464f1737821748017711695"
CLIENT_SECRET = "7AIkjQ9JbQFWhrFx9QMlCeqbLMMPGsXwmFk0wbeS"

def get_kroger_token():
    url = "https://api.kroger.com/v1/connect/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "scope": "product.compact"
    }
    response = requests.post(url, headers=headers, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
    response.raise_for_status()
    return response.json()["access_token"]

def search_kroger_product(name, token):
    url = "https://api.kroger.com/v1/products"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "filter.term": name,
        "filter.limit": 1
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def extract_price_info(product_data):
    items = product_data.get("data", [])
    if not items:
        return None
    
    item = items[0]
    price = item["items"][0]["price"]
    
    return {
        "unit_price": int(price["regular"] * 100),  # in cents
        "price_unit": item["items"][0].get("size", "unit"),
        "package_size": item["items"][0].get("quantity", None)
    }

def update_price_database(data, output_file="ingredient_prices.json"):
    token = get_kroger_token()
    prices = {}

    for ingredient_id, info in data["ingredients"].items():
        name = info["name"]
        try:
            product_data = search_kroger_product(name, token)
            price_info = extract_price_info(product_data)
            
            if price_info:
                prices[ingredient_id] = {
                    "name": name,
                    **price_info
                }
                print(f"[✓] Found price for: {name}")
            else:
                prices[ingredient_id] = {
                    "name": name,
                    "unit_price": None,
                    "price_unit": "unit",
                    "package_size": None
                }
                print(f"[!] No price found for: {name}")

            time.sleep(0.5)  # Avoid rate limits

        except Exception as e:
            print(f"[x] Error for {name}: {e}")
            prices[ingredient_id] = {
                "name": name,
                "unit_price": None,
                "price_unit": "unit",
                "package_size": None
            }

    # Save to file
    with open(output_file, "w") as f:
        json.dump(prices, f, indent=2)
    print(f"\nSaved ingredient prices to {output_file}")
