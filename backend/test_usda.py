import requests
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("USDA_API_KEY")

query = "boiled egg"      # <-- Add this line

url = "https://api.nal.usda.gov/fdc/v1/foods/search"

params = {
    "query": query,
    "pageSize": 5,
    "dataType": [
        "Foundation",
        "SR Legacy",
        "Survey (FNDDS)"
    ],
    "api_key": API_KEY
}

response = requests.get(url, params=params)

print("Status:", response.status_code)

if response.status_code == 200:
    data = response.json()

    for food in data["foods"]:
        print("-" * 40)
        print(food["description"])
else:
    print(response.text)