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
    
    # Get unit price in cents
    unit_price_cents = int(price["regular"] * 100)
    
    # Parse the size string to extract quantity and measurement
    size_str = item.get("size", "1 unit")
    
    # Try to extract quantity and unit from size string
    try:
        parts = size_str.split()
        if len(parts) >= 2:
            quantity = float(parts[0])
            unit = " ".join(parts[1:])
        else:
            quantity = 1
            unit = "unit"
    except:
        quantity = 1
        unit = size_str

    return {
        "unit_price": unit_price_cents,
        "unit_quantity": quantity,
        "measurement": unit
    }

def create_price_database(ingredients_file, output_file="kroger_prices.json"):
    """
    Create a price database for all ingredients in the new format
    
    Args:
        ingredients_file: JSON file with ingredient data
        output_file: Where to save the price data
    """
    # Load ingredients
    try:
        with open(ingredients_file, 'r') as f:
            data = json.load(f)
            all_ingredients = data.get("all_ingredients", [])
            if not all_ingredients:
                print("[!] No ingredients found in file")
                return False
    except Exception as e:
        print(f"[!] Error loading ingredients: {e}")
        return False
    
    # Fetch prices from Kroger API
    token = get_kroger_token()
    if not token:
        print("[x] Failed to get Kroger API token. Prices will not be updated.")
        return False
        
    result = {
        "kroger_query": {
            "ingredients": []
        }
    }
    
    count = 0
    total = len(all_ingredients)

    print(f"[*] Getting prices for {total} ingredients...")
    for ingredient in all_ingredients:
        count += 1
        i_id = ingredient["i_id"]
        name = ingredient["name"]
        
        try:
            print(f"[{count}/{total}] Searching for price of: {name}")
            product_data = search_kroger_product(name, token)
            price_info = extract_price_info(product_data)
            
            # Create the ingredient entry with the new structure
            ingredient_entry = {
                "i_id": i_id,
                "name": name
            }
            
            if price_info:
                ingredient_entry.update({
                    "unit_price": price_info["unit_price"],
                    "unit_quantity": price_info["unit_quantity"],
                    "measurement": price_info["measurement"]
                })
                print(f"[✓] Found price for: {name} - {price_info['unit_price']/100} per {price_info['unit_quantity']} {price_info['measurement']}")
            else:
                ingredient_entry.update({
                    "unit_price": None,
                    "unit_quantity": 1,
                    "measurement": "unit"
                })
                print(f"[!] No price found for: {name}")

            result["kroger_query"]["ingredients"].append(ingredient_entry)
            time.sleep(0.2)  # Avoid rate limits

        except Exception as e:
            print(f"[x] Error for {name}: {e}")
            result["kroger_query"]["ingredients"].append({
                "i_id": i_id,
                "name": name,
                "unit_price": None,
                "unit_quantity": 1,
                "measurement": "unit"
            })

    # Save prices to file
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n[✓] Saved ingredient prices to {output_file}")
    
    # Print sample of price data
    print("\nSample of ingredient price data:")
    for ingredient in result["kroger_query"]["ingredients"][:5]:
        print(f"ID: {ingredient['i_id']}, Name: {ingredient['name']}, " +
              f"Price: {ingredient.get('unit_price')}, Quantity: {ingredient.get('unit_quantity')} {ingredient.get('measurement')}")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate ingredient price database from Kroger API')
    parser.add_argument('--input', default="spoonacular_structured_data.json", 
                        help='Input JSON file with ingredient data')
    parser.add_argument('--output', default="kroger_prices.json", 
                        help='Output file for ingredient prices')
    
    args = parser.parse_args()
    
    print(f"[*] Creating price database from {args.input} to {args.output}")
    create_price_database(args.input, args.output)