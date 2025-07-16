#Provided by Loqman, this script fetches job data from a specified API endpoint

import requests
import json


BASE_URL = "https://bms.allocator.tech/jobs"
HEADERS = {
    "accept": "application/json"
}
PAGE_SIZE = 1000
page = 0

params = {
    "page": page,
    "limit": PAGE_SIZE
}

response = requests.get(BASE_URL, headers=HEADERS, params=params)
# transform the start_r
if response.status_code != 200:
    print(f"Request failed (status {response.status_code}): {response.text}")


data = response.json()
if not data:
    print("No more jobs to fetch.")


with open('json/jobs_data.json', 'w') as f:
    json.dump(data, f, indent=4)
f.close()