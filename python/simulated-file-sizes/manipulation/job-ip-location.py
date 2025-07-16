import pandas as pd
import re

# === File paths ===
input_csv_path = "csv/worker_data.csv"
output_csv_path = "csv/job_ip_location.csv"

# === IP to location + AS name mapping ===
ip_metadata = {
    "47.236.144.226": {"location": "Singapore", "as_name": "Alibaba (US) Technology Co., Ltd."},
    "222.214.219.199": {"location": "China", "as_name": "CHINANET-BACKBONE"},
    "47.254.47.133": {"location": "United States", "as_name": "Alibaba (US) Technology Co., Ltd."},
    "203.160.91.76": {"location": "Hong Kong", "as_name": "China Unicom Global"},
    "103.1.65.126": {"location": "Hong Kong", "as_name": "China Unicom Global"},
    "103.1.65.125": {"location": "Hong Kong", "as_name": "China Unicom Global"},
    "162.219.87.217": {"location": "Hong Kong", "as_name": "China Unicom Global"},
    "162.219.87.220": {"location": "Hong Kong", "as_name": "China Unicom Global"},
    "157.148.101.187": {"location": "China", "as_name": "China Unicom Guangdong IP network"},
    "203.160.91.78": {"location": "Hong Kong", "as_name": "China Unicom Global"},
    "52.217.202.58": {"location": "United States", "as_name": "Amazon.com, Inc."},
    "125.67.244.19": {"location": "China", "as_name": "CHINANET-BACKBONE"},
    "122.114.2.214": {"location": "China", "as_name": "CHINA UNICOM China169 Backbone"},
    "222.74.153.82": {"location": "China", "as_name": "CHINANET-BACKBONE"},
    "76.219.232.45": {"location": "United States", "as_name": "AT&T Enterprises, LLC"},
    "212.106.124.229": {"location": "France", "as_name": "CELESTE SAS"},
    "54.209.183.46": {"location": "United States", "as_name": "Amazon.com, Inc."},
    "54.158.66.216": {"location": "United States", "as_name": "Amazon.com, Inc."},
    "43.229.79.68": {"location": "Thailand", "as_name": "Siamdata Communication Co.,Ltd."},
    "188.227.57.12": {"location": "United States", "as_name": "ITGLOBAL.COM NL B.V."},
    "8.211.145.187": {"location": "Japan", "as_name": "Alibaba (US) Technology Co., Ltd."},
    "93.183.72.2": {"location": "Russia", "as_name": "ITGLOBALCOM RUS LLC"},
    "207.189.117.196": {"location": "United States", "as_name": "Flexential Colorado Corp."},
    "120.236.8.226": {"location": "China", "as_name": "China Mobile communications corporation"},
    "129.236.226.20": {"location": "United States", "as_name": "Columbia University"}
}

# === Domain to IP mapping ===
domain_to_ip = {
    "ahnawee8-xupio2pi-production.s3.us-east-1.amazonaws.com": "52.217.202.58",
    "cesginc.com": "76.219.232.45",
    "f010479.twinquasar.io": "212.106.124.229",
    "yablufc.ddns.net": "129.236.226.20"
}

# === Load the input CSV ===
df = pd.read_csv(input_csv_path)

# === Function to extract IP or map domain ===
def extract_ip(url):
    ip_match = re.search(r'//([\d\.]+):', url)
    if ip_match:
        return ip_match.group(1)
    domain_match = re.search(r'//([^:/]+)', url)
    if domain_match:
        domain = domain_match.group(1)
        return domain_to_ip.get(domain)
    return None

# === Process each row ===
output_rows = []
unmapped_urls = []

for _, row in df.iterrows():
    url = row.get('url', '')
    job_id = row.get('job_id', '')
    
    ip = extract_ip(url)
    if not ip:
        unmapped_urls.append(url)
        continue

    metadata = ip_metadata.get(ip, {"location": "Unknown", "as_name": "Unknown"})
    location = metadata["location"]
    as_name = metadata["as_name"]

    if job_id:
        output_rows.append({
            "job_id": job_id,
            "ip": ip,
            "location": location,
            "as_name": as_name
        })

# === Create DataFrame and remove duplicates ===
output_df = pd.DataFrame(output_rows)
output_df = output_df.drop_duplicates(subset=["job_id", "ip"])

# === Save result ===
output_df.to_csv(output_csv_path, index=False)
print(f"✅ Output saved to: {output_csv_path}")

# === Print any unmapped domains for debugging ===
if unmapped_urls:
    print("\n⚠️ Unmapped URLs or domains found:")
    for url in unmapped_urls:
        print(f" - {url}")
else:
    print("🎉 All URLs were successfully mapped.")
