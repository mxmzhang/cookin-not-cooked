import requests

CLIENT_ID = "cooking-not-cooked-24326124303424687244626a75306c42416450477234325569686948756d4177696f31417650326846325232722e396f634d694c4f697130506d464f1737821748017711695"
CLIENT_SECRET = "7AIkjQ9JbQFWhrFx9QMlCeqbLMMPGsXwmFk0wbeS"

def get_kroger_token():
    url = "https://api.kroger.com/v1/connect/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "scope": "location.read",
    }
    response = requests.post(url, headers=headers, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
    response.raise_for_status()
    return response.json()["access_token"]

def get_philly_location_id():
    try:
        token = get_kroger_token()
        url = "https://api.kroger.com/v1/locations"
        params = {"filter.city": "Philadelphia", "filter.state": "PA"}
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
get_philly_location_id()
