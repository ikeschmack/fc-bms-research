import pandas as pd
import matplotlib.pyplot as plt
import json
import numpy as np

# Load jobs into a DataFrame
with open("json/job_with_subjobs.json", "r") as f:
    data = json.load(f)
if not data:
    print("No jobs to process.")
    exit()

provider_data = []
with open("json/geo-location.json", "r") as p:
    provider_data = json.load(p)
if not provider_data:
    print("No provider data to process.")
    exit()


pf = pd.json_normalize(provider_data)


# Normalize dataframe from JSON
df = pd.json_normalize(
    data, 
    meta=['summary', 'sub_jobs', 'id', 'url'], 
    meta_prefix='parent_',
    errors='ignore'
)
df['domain'] = df['url'].str.extract(r'https?://([^/:]+)')


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


merged = pd.merge(df, pf, left_on='domain', right_on='ip', how='outer')
print(merged.columns)

## Next create the graph using the merged data