# This script reads a JSON file (job_with_subjobs.json) and creates another JSON file (job_domain.json) that contains only the URLs domain name

import pandas as pd
import matplotlib.pyplot as plt
import json

# Load jobs into a DataFrame
with open("job_with_subjobs.json", "r") as f:
    data = json.load(f)
if not data:
    print("No jobs to process.")
    exit()
df = pd.json_normalize(data)
# Extract the domain from the URL
df['domain'] = df['url'].str.extract(r'https?://([^/]+)')
# Create json file with only the domain names
df_domain = df[['domain']].drop_duplicates()
df_domain.to_json("job_domain.json", orient="records", lines=True)

# Save the DataFrame to a Json file
df_domain.to_json("job_domain.json", orient="records", lines=True)