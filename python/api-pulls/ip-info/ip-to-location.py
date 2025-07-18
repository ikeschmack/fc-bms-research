# Convert given IP address to country of origin using ipinfo.io API
# Tenative, might be deleted later since there is an IP field coming in the new data
import requests
import json
import pandas as pd

BASE_URL = "https://api.ipinfo.io/lite/"
TOKEN = "?token=a4be2d0d13524d"
HEADERS = {
    "accept": "application/json"
}

with open("json/job_domain.json", "r") as f:
    data = json.load(f)
if not data:
    print("No IPs to fetch.")
    exit()
df = pd.DataFrame(data)
retrieved = []
for entry in data:
    ip = entry['ip_address']
    if not ip:
        print("IP address not found, skipping entry.")
        continue

    response = requests.get(f'{BASE_URL}{ip}{TOKEN}', headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Request failed (status {response.status_code}): {response.text}")
        continue
    retrieved.append(response.json())

# Save the retrieved data to a JSON file
with open("json/geo-location.json", "w") as f:
    json.dump(retrieved, f, indent=4)





