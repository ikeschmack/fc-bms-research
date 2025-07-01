# This script will create a box and whisker plot comparing the same download speed data from provider-contribution-bar.py

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

merged['summary.max_download_speed'] = pd.to_numeric(merged['summary.max_download_speed'], errors='coerce')
merged.dropna(subset=['summary.max_download_speed'], inplace=True)
grouped = merged.groupby('as_name')['summary.max_download_speed'].apply(list)

# Remove Amazon's Outlier Max Download Speed
grouped = grouped[grouped.index != 'Amazon Technologies Inc.']


# Create a box and whisker plot for download speeds by provider
plt.figure(figsize=(8, 12))
plt.boxplot(grouped, labels=grouped.index, vert=True, patch_artist=True)
plt.suptitle('')
plt.xlabel('Provider AS Name')
plt.ylabel('Max Download Speed (Mbps)')
plt.title('Box and Whisker Plot of Download Speeds by Provider')
plt.xticks(rotation=45, ha='right')
plt.grid(axis='y')
plt.tight_layout()
plt.show()
