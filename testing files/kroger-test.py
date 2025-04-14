import requests

CLIENT_ID = "cooking-not-cooked-24326124303424687244626a75306c42416450477234325569686948756d4177696f31417650326846325232722e396f634d694c4f697130506d464f1737821748017711695"
CLIENT_SECRET = "7AIkjQ9JbQFWhrFx9QMlCeqbLMMPGsXwmFk0wbeS"
LOCATION_ID = "01100002"
def get_kroger_token():
    url = "https://api.kroger.com/v1/connect/oauth2/token"
    
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "scope": "product.compact"
    }

    response = requests.post(url, headers=headers, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
    response.raise_for_status()  # Raise an error if the request was unsuccessful
    return response.json()["access_token"]

def search_products(term):
    try:
        # Get access token
        token = get_kroger_token()

        # API endpoint for searching products
        url = "https://api.kroger.com/v1/products"
        params = {
            "filter.term": term,
            "filter.locationId": LOCATION_ID  # Include locationId as filter
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        # Send the GET request
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()


        # Print product search results
        products = response.json().get("data", [])
        if products:
            print(f"Products found for '{term}':")
            for product in products:
                print(f"Product ID: {product['productId']}")
                print(f"Description: {product['description']}")
                print(f"Size: {product['items'][0]['size']}")

                # Check if 'price' key exists and print it
                if 'price' in product['items'][0]:
                    print(f"Price: ${product['items'][0]['price']['regular']}")
                else:
                    print("Price: Not available")
                
                print("-----")
        else:
            print(f"No products found for '{term}'")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching products: {e}")

def get_philly_location_id():
    try:
        token = get_kroger_token()
        url = "https://api.kroger.com/v1/locations"
        params = {"filter.city": "Troy", "filter.state": "MI"}
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        locations = response.json().get("data", [])
        if locations:
            location_id = locations[0]["locationId"]
            print(f"Found location ID: {location_id}")
            return location_id
        else:
            print("No Kroger locations found in Philadelphia.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching location ID: {e}")
        return None

# Example usage
#get_philly_location_id()

# Example usage: Search for 'milk'
search_products("milk")
