import pandas as pd
import json
import re
import os
import socket # Import the socket module for DNS lookups

# Define file paths
JOB_DETAILS_CSV = '/csv/job_details_with_bandwidth.csv'
GEO_LOCATION_JSON = '/json/geo-location.json'
JOB_WITH_SUBJOBS_JSON = '/json/jobs_with_subjobs.json'

# Output file path for the specific CSV requested
OUTPUT_JOB_COMPANY_CSV = 'job_company_summary.csv' 

# --- 1. Validate File Existence ---
for fpath in [JOB_DETAILS_CSV, GEO_LOCATION_JSON, JOB_WITH_SUBJOBS_JSON]:
    if not os.path.exists(fpath):
        print(f"Error: Required file '{fpath}' not found.")
        print("Please ensure all input files exist at the specified paths.")
        exit()

# --- 2. Load Geo-location Data (IP to Provider/Country Mapping - as fallback) ---
ip_to_provider_info_fallback = {}
try:
    with open(GEO_LOCATION_JSON, 'r', encoding='utf-8') as f:
        geo_data = json.load(f)
    for entry in geo_data:
        ip = entry.get('ip')
        as_name = entry.get('as_name', 'Unknown Provider')
        country = entry.get('country', 'Unknown Country (Fallback)')
        if ip:
            ip_to_provider_info_fallback[ip] = {'as_name': as_name, 'country': country}
    print(f"Successfully loaded geo-location fallback data from '{GEO_LOCATION_JSON}'.")
except json.JSONDecodeError as e:
    print(f"Error decoding JSON from {GEO_LOCATION_JSON}: {e}")
    print("Please check your geo-location.json file for syntax errors or hidden characters.")
    exit()
except Exception as e:
    print(f"An unexpected error occurred while reading {GEO_LOCATION_JSON}: {e}")
    exit()

# --- 3. Load Job Details CSV (Primary source for job_id, url, client country, max_bandwidth, provider company) ---
job_details_from_csv_map = {}
try:
    df_job_details_csv = pd.read_csv(JOB_DETAILS_CSV)
    # Validate core required columns (make 'company' optional here)
    core_required_cols_details_csv = ['job_id', 'url', 'country', 'max_bandwidth']
    if not all(col in df_job_details_csv.columns for col in core_required_cols_details_csv):
        print(f"Error: Missing one or more core required columns in '{JOB_DETAILS_CSV}'.")
        print(f"Expected at least: {core_required_cols_details_csv}, Found: {df_job_details_csv.columns.tolist()}")
        exit()
    
    # Check for 'company' column specifically and warn if missing
    has_company_column = 'company' in df_job_details_csv.columns
    if not has_company_column:
        print(f"Warning: 'company' column not found in '{JOB_DETAILS_CSV}'. Provider company will be derived from geo-location fallback.")

    # Ensure max_bandwidth is numeric
    df_job_details_csv['max_bandwidth'] = pd.to_numeric(df_job_details_csv['max_bandwidth'], errors='coerce')
    df_job_details_csv.dropna(subset=['max_bandwidth'], inplace=True) # Drop rows with invalid bandwidth

    for index, row in df_job_details_csv.iterrows():
        job_id = row.get('job_id')
        if job_id:
            job_details_from_csv_map[job_id] = {
                'url': row.get('url'),
                'client_country': row.get('country'), # This is the client's country
                'max_bandwidth': row.get('max_bandwidth'), # max_bandwidth directly from this CSV
                # Get provider_company from CSV if column exists, else default to 'Unknown Company'
                'provider_company': row.get('company') if has_company_column else 'Unknown Company' 
            }
    print(f"Successfully loaded job details from '{JOB_DETAILS_CSV}'.")
except FileNotFoundError:
    print(f"Error: {JOB_DETAILS_CSV} not found.")
    exit()
except Exception as e:
    print(f"An unexpected error occurred while reading {JOB_DETAILS_CSV}: {e}")
    exit()


# --- 4. Load Jobs with Subjobs JSON (Source for job_id and routing_key) ---
jobs_data_from_json = []
try:
    with open(JOB_WITH_SUBJOBS_JSON, 'r', encoding='utf-8') as f:
        jobs_data_from_json = json.load(f)
    print(f"Successfully loaded job and subjob data from '{JOB_WITH_SUBJOBS_JSON}'.")
except json.JSONDecodeError as e:
    print(f"Error decoding JSON from {JOB_WITH_SUBJOBS_JSON}: {e}")
    print("Please check your job_with_subjobs.json file for syntax errors.")
    exit()
except Exception as e:
    print(f"An unexpected error occurred while reading {JOB_WITH_SUBJOBS_JSON}: {e}")
    exit()


# --- 5. Function to Extract Host (IP/Domain) from URL and resolve to IP if possible ---
def extract_host_from_url(url):
    match = re.search(r'http://([^/:]+)', url)
    if match:
        host = match.group(1)
        # Check if it's already an IP address
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host):
            return host # It's already an IP
        else:
            # It's likely a domain name, try to resolve it to an IP
            try:
                ip_address = socket.gethostbyname(host)
                return ip_address
            except socket.gaierror:
                # If DNS resolution fails, return the original host (domain name)
                print(f"Warning: Could not resolve domain '{host}' to an IP address for fallback lookup.")
                return host # Return original host if resolution fails
    return None

# --- 6. Prepare Data for the new job_company_summary.csv ---
job_company_summary_csv_raw = [] 

for job_json_entry in jobs_data_from_json:
    job_id = job_json_entry.get('id')
    routing_key = job_json_entry.get('routing_key', 'Unknown Routing Key')

    # Get details primarily from job_details_from_csv_map
    csv_details = job_details_from_csv_map.get(job_id)

    if csv_details:
        url = csv_details.get('url', '')
        client_country = csv_details.get('client_country', 'Unknown Country (Client)')
        max_bandwidth = csv_details.get('max_bandwidth', 0)
        provider_company = csv_details.get('provider_company', 'Unknown Company') # Get from CSV or default

        # Fallback for provider company if it's 'Unknown Company' from CSV or default
        # This is where geo-location.json comes into play using the resolved IP from URL
        if provider_company == 'Unknown Company':
            host = extract_host_from_url(url)
            if host:
                fallback_info = ip_to_provider_info_fallback.get(host)
                if fallback_info:
                    provider_company = fallback_info['as_name']

        job_company_summary_csv_raw.append({
            'job_id': job_id,
            'url': url,
            'country': client_country, # This is the client's country
            'max_bandwidth': max_bandwidth, # From job_details_with_bandwidth.csv
            'company': provider_company, # From job_details_with_bandwidth.csv or geo-location fallback
            'routing_key': routing_key # From job_with_subjobs.json
        })
    else:
        print(f"Warning: Job ID '{job_id}' from '{JOB_WITH_SUBJOBS_JSON}' not found in '{JOB_DETAILS_CSV}'. Skipping for CSV output.")

# --- 7. Save the new job_company_summary.csv ---
if job_company_summary_csv_raw:
    df_job_company_summary = pd.DataFrame(job_company_summary_csv_raw)
    try:
        df_job_company_summary.to_csv(OUTPUT_JOB_COMPANY_CSV, index=False)
        print(f"\nJob details (job_id, url, client_country, max_bandwidth, provider_company, routing_key) saved to '{OUTPUT_JOB_COMPANY_CSV}'.")
    except Exception as e:
        print(f"Error saving job_company_summary CSV: {e}")
else:
    print("No valid data generated for job_company_summary.csv. Check your input files and data processing logic.")
