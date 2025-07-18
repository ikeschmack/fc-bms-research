# This script reads a JSON file (job_with_subjobs.json) and creates another JSON file (job_domain.json) that contains only the URLs domain name
# Tenative, might be deleted later since there is an IP field coming in the new data
import pandas as pd
import matplotlib.pyplot as plt
import json
import subprocess

# Load jobs into a DataFrame
with open("json/jobs_with_subjobs.json", "r") as f:
    data = json.load(f)
if not data:
    print("No jobs to process.")
    exit()
df = pd.json_normalize(data)
# Extract the domain from the URL
df['domain'] = df['url'].str.extract(r'https?://([^/:]+)')



# Create json file with only the domain names
df = df[['domain', 'routing_key']].drop_duplicates()

df_non_ip = df[~df['domain'].str.match(r'^((?:\d{1,3}\.){3}\d{1,3})$')]
df_ip = df[df['domain'].str.match(r'^((?:\d{1,3}\.){3}\d{1,3})$')]



# Create an iterable list of df_non_ip
if df_non_ip.empty:
    print("No non-IP domains found.")



# Use nslookup to resolve the domains
# Appens the resolved IP addresses in a json format
resolved_domains = []
for _, row in df_non_ip.iterrows():
    try:
        domain = row['domain']
        routing_key = row['routing_key']
        result = subprocess.run(['nslookup', domain] , capture_output=True, text=True)
        if result.returncode == 0:
            # Extract the IP address from the nslookup output
            ip_address = result.stdout.split('Address: ')[-1].strip()
            json_data = {
                "domain": domain,
                "ip_address": ip_address,
                "routing_key": routing_key
            }
            resolved_domains.append((json_data))
            # Debugging output
            print(f"Resolved {domain} to {ip_address}")
        else:
            print(f"Failed to resolve {domain}: {result.stderr.strip()}")
    except Exception as e:
        print(f"Error resolving {row['domain']}: {e}") 


# Append IP to resolved domain list
for _, row in df_ip.iterrows():
    try:
        domain = row['domain']
        routing_key = row['routing_key']
        json_data = {
            "domain": domain,
            "ip_address": ip_address,
            "routing_key": routing_key
        }
        resolved_domains.append((json_data)) # Keep the original domain as IP
    except Exception as e:
        print(f"Error processing {row['domain']}: {e}")

# Convert the list of resolved domains to a DataFrame
resolved_domains = pd.DataFrame(resolved_domains)

json_data = resolved_domains.to_json(orient='index', indent=4)
# Write the resolved domains to a JSON file
with open("json/job_domain.json", "w") as f:
    f.write(json_data)

