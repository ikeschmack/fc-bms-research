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

merged.to_json('json/merged_jobs.json', indent=4)
print(merged.columns)

## Next create the graph using the merged data
'''
agg = merged.groupby('as_name').agg({
    'summary.max_download_speed': 'sum',
    'as_name': 'count'
}).rename(columns={'as_name': 'provider_count'}).reset_index()

# Rename the columns for clarity


# Remove rows where max_download_speed is 0.0
agg = agg[agg['summary.max_download_speed'] > 0.0]
'''

agg = merged.groupby('as_name').agg({
    'summary.max_download_speed': 'median',
    'as_name': 'count'
}).rename(columns={'as_name': 'provider_count'}).reset_index()

agg = agg[agg['summary.max_download_speed'] > 0.0]

# Print the amount of jobs per provider
print("Number of jobs per provider:")
print(agg[['as_name', 'provider_count']])




max = agg['summary.max_download_speed'].max()
min = agg['summary.max_download_speed'].min()


# Create bar chart
plt.figure(figsize=(10, 12))

agg = agg.sort_values(by='summary.max_download_speed', ascending=False)
bars = plt.bar(agg['as_name'], agg['summary.max_download_speed'], color='skyblue')

plt.bar(agg['as_name'], agg['summary.max_download_speed'], color='skyblue')
plt.axhline(y=100, color='darkred', linestyle='--', label='100 Mbps')
plt.axhline(y=max, color='blue', linestyle='--', label=f'{max/1000} Gbps')

for bar in bars:
    if bar.get_height() == max:
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 50, f"{max / 1000:.1f} Gbps", 
                 color='blue', fontsize=10, ha='center')
    if bar.get_height() == min:
        plt.text(bar.get_x() + bar.get_width() / 2, - 10, f"{min} Mbps", 
                 color='red', fontsize=10, ha='center', va='top', rotation=35)

plt.xlabel('Provider Name')
plt.ylabel('Median Available Bandwdith (Gbps)')
plt.title('Median Bandwidth Contribution by Provider')
plt.xticks(rotation=35, ha='right')

plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x / 1000:.1f} Gbps"))

plt.grid(axis='y', alpha=0.7)

plt.tight_layout()
# Save the plot
plt.savefig('provider_contribution_bar.png')
# Show the plot
plt.show()




