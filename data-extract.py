#Provided by Loqman, this script fetches job data from a specified API endpoint

import requests
from datetime import datetime
import matplotlib.pyplot as plt
import csv
import json


BASE_URL = "https://bms.allocator.tech/jobs"
HEADERS = {
    "accept": "application/json"
}
PAGE_SIZE = 1000
page = 0
all_jobs = []
times_in_dataset = []

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

print(json.dumps(data, indent=4))

# transform data to a list
'''
all_jobs.extend(data)
print(f"Fetched {len(data)} jobs from page {page}")
page += 1

print(f"Total jobs retrieved: {len(all_jobs)}")


deadline_datetimes = [datetime.strptime(ts, '%Y-%m-%d %H:%M:%S') for ts in times_in_dataset]

# Plot histogram of time
plt.figure(figsize=(12, 6))
plt.hist(deadline_datetimes, bins=50, edgecolor='black')
plt.title("Distribution of Deadline Times")
plt.xlabel("Deadline Timestamp")
plt.ylabel("Number of Subjobs")
plt.xticks(rotation=45)
plt.tight_layout()
plt.grid(True)
plt.show()'''