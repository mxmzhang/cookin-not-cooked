import json
import requests
import time
import os.path

CLIENT_ID = "cooking-not-cooked-24326124303424687244626a75306c42416450477234325569686948756d4177696f31417650326846325232722e396f634d694c4f697130506d464f1737821748017711695"
CLIENT_SECRET = "7AIkjQ9JbQFWhrFx9QMlCeqbLMMPGsXwmFk0wbeS"
LOCATION_ID = "01100002"

def get_kroger_token():
    """Get an authentication token from the Kroger API"""
    url = "https://api.kroger.com/v1/connect/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "scope": "product.compact"
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            print("[!] No token returned from Kroger API")
            return None
        return token
    except Exception as e:
        print(f"[x] Error getting Kroger token: {e}")
        return None

def search_kroger_product(name, token):
    """Search for a product in the Kroger API by name"""
    if not token:
        print(f"[!] No valid token for searching {name}")
        return {"data": []}
        
    url = "https://api.kroger.com/v1/products"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "filter.term": name,
        "filter.locationId": LOCATION_ID,
        "filter.limit": 1
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[x] Error searching for {name}: {e}")
        return {"data": []}

def extract_price_info(product_data):
    """Extract pricing information from Kroger API response"""
    items = product_data.get("data", [])
    if not items:
        return None

    product = items[0]
    item_list = product.get("items", [])
    
    if not item_list:
        return None

    item = item_list[0]
    price = item.get("price")
    
    if not price or "regular" not in price:
        return None
    
    unit_price_cents = int(price["regular"] * 100)
    price_unit = item.get("size", "unit")

    return {
        "unit_price": unit_price_cents,
        "price_unit": price_unit,
    }

def create_price_database(ingredients_file, output_file="ingredient_prices.json"):
    """
    Create a standalone price database file for all ingredients
    
    Args:
        ingredients_file: JSON file with ingredient data
        output_file: Where to save the price data
    """
    # Load ingredients
    try:
        with open(ingredients_file, 'r') as f:
            data = json.load(f)
            if "ingredients" not in data:
                print("[!] No ingredients found in file")
                return False
            ingredients = data["ingredients"]
    except Exception as e:
        print(f"[!] Error loading ingredients: {e}")
        return False
    
    # Fetch prices from Kroger API
    token = get_kroger_token()
    if not token:
        print("[x] Failed to get Kroger API token. Prices will not be updated.")
        return False
        
    prices = {}
    count = 0
    total = len(ingredients)

    print(f"[*] Getting prices for {total} ingredients...")
    for ingredient_id, info in ingredients.items():
        count += 1
        name = info["name"]
        try:
            print(f"[{count}/{total}] Searching for price of: {name}")
            product_data = search_kroger_product(name, token)
            price_info = extract_price_info(product_data)
            
            if price_info:
                prices[ingredient_id] = {
                    "name": name,
                    **price_info
                }
                print(f"[✓] Found price for: {name} - {price_info['unit_price']/100} per {price_info['price_unit']}")
            else:
                prices[ingredient_id] = {
                    "name": name,
                    "unit_price": None,
                    "price_unit": "unit",
                }
                print(f"[!] No price found for: {name}")

            time.sleep(0.2)  # Avoid rate limits

        except Exception as e:
            print(f"[x] Error for {name}: {e}")
            prices[ingredient_id] = {
                "name": name,
                "unit_price": None,
                "price_unit": "unit",
            }

    # Save prices to file for future use
    with open(output_file, "w") as f:
        json.dump(prices, f, indent=2)
    print(f"\n[✓] Saved ingredient prices to {output_file}")
    
    # Print sample of price data
    print("\nSample of ingredient price data:")
    sample_count = 0
    for ingredient_id, price_info in list(prices.items())[:5]:
        print(f"ID: {ingredient_id}, Name: {price_info.get('name')}, " +
              f"Price: {price_info.get('unit_price')}, Unit: {price_info.get('price_unit')}")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate ingredient price database from Kroger API')
    parser.add_argument('--input', default="structured_recipe_data_pre_pricing.json", 
                        help='Input JSON file with ingredient data')
    parser.add_argument('--output', default="ingredient_prices.json", 
                        help='Output file for ingredient prices')
    
    args = parser.parse_args()
    
    print(f"[*] Creating price database from {args.input} to {args.output}")
    create_price_database(args.input, args.output)