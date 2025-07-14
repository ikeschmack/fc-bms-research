# This script reads a JSON file (job_with_subjobs.json) and creates another JSON file (job_domain.json) that contains only the URLs domain name

import pandas as pd
import matplotlib.pyplot as plt
import json

# Load jobs into a DataFrame
with open("json/job_with_subjobs.json", "r") as f:
    data = json.load(f)
if not data:
    print("No jobs to process.")
    exit()
df = pd.json_normalize(data)
# Extract the domain from the URL
df['domain'] = df['url'].str.extract(r'https?://([^/:]+)')



# Create json file with only the domain names
# df_domain = df[['domain', 'routing_key']].drop_duplicates()


# Hardcoded domain replacements
if (df['domain'] == "yablufc.ddns.net").any():
    print("Domain yablufc.ddns.net found, changing it to 129.236.226.20.")
    df['domain'] = df['domain'].replace("yablufc.ddns.net", "129.236.226.20")

if (df['domain'] == "f010479.twinquasar.io").any():
    print("Domain f010479.twinquasar.io found, changing it to 212.106.124.229.")
    df['domain'] = df['domain'].replace("f010479.twinquasar.io", "212.106.124.229")

if (df['domain'] == "cesginc.com").any():
    print("Domain cesginc.com found, changing it to 76.219.232.45.")
    df['domain'] = df['domain'].replace("cesginc.com", "76.219.232.45")

if (df['domain'] == "ahnawee8-xupio2pi-production.s3.us-east-1.amazonaws.com").any():
    print("Domain ahnawee8-xupio2pi-production.s3.us-east-1.amazonaws.com found, changing it to 52.217.202.58.")
    df['domain'] = df['domain'].replace("ahnawee8-xupio2pi-production.s3.us-east-1.amazonaws.com", "52.217.202.58")

#Temporary remove non-IP address domains
# df_domain = df_domain[df_domain['domain'].str.match(r'^((?:\d{1,3}\.){3}\d{1,3})$')]
# End temporary


df_domain = df[['domain']].drop_duplicates()
df_domain.to_json("json/job_domain.json", orient="records", lines=True)