# Get IP from the resolved_ip field skeleton code
import pandas as pd
import json

with open("csv/worker_data.csv", "r") as f:
    data = pd.read_csv(f)
if data.empty:
    print("No worker data found.")
    exit()

# Extract the resolved_ip field
data['resolved_ip'] = data['resolved_ip'].fillna('Unknown')

# Create a DataFrame with the resolved IPs
ip_data = data[['resolved_ip', 'routing_key']].drop_duplicates()
# Save to a json file
ip_data.to_json("json/resolved_ips.json", orient='index', lines=True)

