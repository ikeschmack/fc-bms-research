#Create jobs_with_subjobs.json file by pulling job details from the BMS API
import requests
import json

BASE_URL = "https://bms.allocator.tech/jobs"
HEADERS = {
    "accept": "application/json"
}
all_jobs = []

with open("json/jobs_data.json", "r") as f:
    data = json.load(f)
f.close()
if not data:
    print("No jobs to process.")
    exit()

for job in data:
    job_id = job.get("id")
    if not job_id:
        print("Job ID not found, skipping job.")
        continue

    response = requests.get(f"{BASE_URL}/{job_id}?extended=true", headers=HEADERS)
    
    if response.status_code != 200:
        print(f"Request failed for job {job_id} (status {response.status_code}): {response.text}")
        continue

    job_details = response.json()
    all_jobs.append(job_details)

with open("json/jobs_with_subjobs.json", "w") as f:
    json.dump(all_jobs, f, indent=4)
f.close()
