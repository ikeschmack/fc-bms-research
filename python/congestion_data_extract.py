import requests
import json

BASE_URL = "https://bms.allocator.tech/jobs"
HEADERS = {"accept": "application/json"}

response = requests.get(BASE_URL, headers=HEADERS)
jobs = response.json()

print(f"Number of jobs returned: {len(jobs)}")
print(json.dumps(jobs[0], indent=2))  # show first job to inspect structure
