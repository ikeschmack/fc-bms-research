import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from matplotlib.backends.backend_pdf import PdfPages
from urllib.parse import urlparse

# Hardcoded IP to country mapping
ip_country_data = [
    {"ip": "47.236.144.226", "country": "Singapore"},
    {"ip": "222.214.219.199", "country": "China"},
    {"ip": "47.254.47.133", "country": "United States"},
    {"ip": "203.160.91.76", "country": "Hong Kong"},
    {"ip": "103.1.65.126", "country": "Hong Kong"},
    {"ip": "103.1.65.125", "country": "Hong Kong"},
    {"ip": "162.219.87.217", "country": "Hong Kong"},
    {"ip": "162.219.87.220", "country": "Hong Kong"},
    {"ip": "157.148.101.187", "country": "China"},
    {"ip": "203.160.91.78", "country": "Hong Kong"},
    {"ip": "52.217.202.58", "country": "United States"},
    {"ip": "125.67.244.19", "country": "China"},
    {"ip": "122.114.2.214", "country": "China"},
    {"ip": "222.74.153.82", "country": "China"},
    {"ip": "76.219.232.45", "country": "United States"},
    {"ip": "212.106.124.229", "country": "France"},
    {"ip": "54.209.183.46", "country": "United States"},
    {"ip": "54.158.66.216", "country": "United States"},
    {"ip": "43.229.79.68", "country": "Thailand"},
    {"ip": "188.227.57.12", "country": "United States"},
    {"ip": "8.211.145.187", "country": "Japan"},
    {"ip": "93.183.72.2", "country": "Russia"},
    {"ip": "207.189.117.196", "country": "United States"},
    {"ip": "120.236.8.226", "country": "China"},
    {"ip": "129.236.226.20", "country": "United States"},
]

def get_country_for_ip(ip):
    for entry in ip_country_data:
        if entry["ip"] == ip:
            return entry["country"]
    return "Unknown"

def extract_ip(url):
    try:
        return urlparse(url).hostname
    except:
        return None

def generate_graphs_per_ip(json_file_path="json/job_with_subjobs.json", output_dir="latency_with_routingKeys"):
    os.makedirs(output_dir, exist_ok=True)

    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON from '{json_file_path}'.")
        return

    extracted_data = []

    for job in data:
        routing_key = job.get('routing_key')
        if routing_key == 'all':  # Exclude 'all' routing key
            continue
        url = job.get('url')
        status = job.get('status')
        ip = extract_ip(url)

        sub_jobs = job.get('sub_jobs', [])
        if not sub_jobs:
            continue

        for sub_job in sub_jobs:
            worker_data_list = sub_job.get('worker_data', [])
            if isinstance(worker_data_list, dict):
                worker_data_list = [worker_data_list]
            elif not isinstance(worker_data_list, list):
                continue

            for worker in worker_data_list:
                if not isinstance(worker, dict):
                    continue

                download = worker.get('download', {})
                ping = worker.get('ping', {})
                head = worker.get('head', {})

                extracted_data.append({
                    'ip': ip,
                    'routing_key': routing_key,
                    'url': url,
                    'status': status,
                    'worker_id': worker.get('id'),
                    'worker_name': worker.get('worker_name'),
                    'is_success': worker.get('is_success', False),
                    'download_speed_mbps': download.get('download_speed', 0.0) * 8,  # MB/s to Mbps
                    'time_to_first_byte_ms': download.get('time_to_first_byte_ms'),
                    'ping_error': ping.get('error'),
                    'head_avg_ms': head.get('avg'),
                    'head_max_ms': head.get('max'),
                    'head_min_ms': head.get('min'),
                })

    df = pd.DataFrame(extracted_data)
    successful_df = df[df['is_success'] == True].copy()

    if successful_df.empty:
        print("No successful jobs found.")
        return

    # Filter IPs with >= 2 unique routing keys (excluding 'all' already filtered above)
    ip_routing_counts = successful_df.groupby('ip')['routing_key'].nunique()
    ips_to_include = ip_routing_counts[ip_routing_counts >= 2].index.tolist()

    filtered_df = successful_df[successful_df['ip'].isin(ips_to_include)]

    if filtered_df.empty:
        print("No IPs with 2 or more routing keys found after filtering.")
        return

    print(f"\nFound {len(filtered_df)} successful sub-jobs across {len(ips_to_include)} IPs with >= 2 routing keys (excluding 'all').")

    # Create a consistent color palette keyed by routing_key
    routing_keys = sorted(filtered_df['routing_key'].unique())
    palette = sns.color_palette("tab10", n_colors=len(routing_keys))
    color_map = dict(zip(routing_keys, palette))

    pdf_path = os.path.join(output_dir, f"all_ips_latency_report_filtered.pdf")
    with PdfPages(pdf_path) as pdf:
        for ip, ip_df in filtered_df.groupby('ip'):
            country = get_country_for_ip(ip)
            title_prefix = f"IP: {ip} ({country})"

            fig, axs = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle(title_prefix, fontsize=16)

            # Plot 1: Download Speed vs Average Head Latency (top-left)
            if not ip_df['head_avg_ms'].isnull().all():
                sns.scatterplot(data=ip_df, x='head_avg_ms', y='download_speed_mbps', hue='routing_key',
                                palette=color_map, s=60, alpha=0.7, ax=axs[0, 0])
                axs[0, 0].set_title("Download Speed vs Avg Head Latency")
                axs[0, 0].set_xlabel("Average Head Latency (ms)")
                axs[0, 0].set_ylabel("Download Speed (Mbps)")
                axs[0, 0].grid(True, linestyle='--', alpha=0.5)
                axs[0, 0].legend(title="Routing Key")

            # Plot 2: Download Speed vs Time to First Byte (top-right)
            if not ip_df['time_to_first_byte_ms'].isnull().all():
                sns.scatterplot(data=ip_df, x='time_to_first_byte_ms', y='download_speed_mbps', hue='routing_key',
                                palette=color_map, s=60, alpha=0.7, ax=axs[0, 1])
                axs[0, 1].set_title("Download Speed vs Time to First Byte")
                axs[0, 1].set_xlabel("Time to First Byte (ms)")
                axs[0, 1].set_ylabel("Download Speed (Mbps)")
                axs[0, 1].grid(True, linestyle='--', alpha=0.5)
                axs[0, 1].legend(title="Routing Key")

            # Plot 3: Head Latency Box Plot (bottom-left)
            if not ip_df['head_avg_ms'].isnull().all():
                sns.boxplot(data=ip_df, x='routing_key', y='head_avg_ms', palette=color_map, ax=axs[1, 0])
                axs[1, 0].set_title("Head Latency Distribution by Routing Key")
                axs[1, 0].set_xlabel("Routing Key")
                axs[1, 0].set_ylabel("Average Head Latency (ms)")
                axs[1, 0].set_yscale('log')
                axs[1, 0].grid(True, axis='y', linestyle='--', alpha=0.4)

            # Plot 4: Time to First Byte Box Plot (bottom-right)
            if not ip_df['time_to_first_byte_ms'].isnull().all():
                sns.boxplot(data=ip_df, x='routing_key', y='time_to_first_byte_ms', palette=color_map, ax=axs[1, 1])
                axs[1, 1].set_title("Time to First Byte Distribution by Routing Key")
                axs[1, 1].set_xlabel("Routing Key")
                axs[1, 1].set_ylabel("Time to First Byte (ms)")
                axs[1, 1].grid(True, axis='y', linestyle='--', alpha=0.4)

            plt.tight_layout(rect=[0, 0.03, 1, 0.95])  # leave space for main title
            pdf.savefig(fig)
            plt.close(fig)

    print(f"✅ Filtered plots saved into one PDF: {pdf_path}")

if __name__ == "__main__":
    generate_graphs_per_ip()
