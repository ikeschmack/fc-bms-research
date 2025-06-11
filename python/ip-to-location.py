# Convert given IP address to country of origin using ipinfo.io API
import requests
import json
import pandas as pd

BASE_URL = "https://api.ipinfo.io/lite/"
TOKEN = "?token=a4be2d0d13524d"
HEADERS = {
    "accept": "application/json"
}
data = []
with open("json/job_domain.json", "r") as f:
    for l in f:
        data.append(json.loads(l))
if not data:
    print("No IPs to fetch.")
    exit()

for entry in data:
    ip = entry.get('domain')  # Assuming the domain field contains the IP address
    if not ip:
        print("IP address not found, skipping entry.")
        continue

    response = requests.get(f'{BASE_URL}{ip}{TOKEN}', headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Request failed (status {response.status_code}): {response.text}")
        continue
    retrieved = response.json()
    print(json.dumps(retrieved, indent=4))


