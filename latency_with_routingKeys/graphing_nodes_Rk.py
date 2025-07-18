import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from matplotlib.backends.backend_pdf import PdfPages
from urllib.parse import urlparse

domain_to_ip = [
    {"cesginc.com": "76.219.232.45"},
    {"f010479.twinquasar.io/piece/baga6ea4seaqfhg3glmn7wfousy3tyemhferh3qr6p4yynuyjdnkl3ytyuerhynq": "212.106.124.229"},
    {"ahnawee8-xupio2pi-production.s3.us-east-1.amazonaws.com": "3.5.8.96"},
]

def get_ip_from_url(url):
    parsed = urlparse(url)
    hostname = parsed.hostname
    # If hostname is a domain in the mapping, return mapped IP
    for mapping in domain_to_ip:
        for domain, ip in mapping.items():
            if hostname == domain:
                return ip
    return hostname  # If already an IP or not in mapping

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
    {"ip": "76.219.232.45", "country":"United States"}, #http://cesginc.com domain 
    {"ip": "3.5.8.96", "country": "United States"},  # ahnawee8-xupio2pi-production.s3.us-east-1.amazonaws.com
]

distance_miles = {
    "Singapore":     {"US_east": 9000, "Hong_kong": 1600, "Singapore": 0},
    "China":         {"US_east": 7000, "Hong_kong": 900, "Singapore": 1600},
    "United States": {"US_east": 0, "Hong_kong": 8000, "Singapore": 9000},
    "Hong Kong":     {"US_east": 8000, "Hong_kong": 0, "Singapore": 900},
    "France":        {"US_east": 4000, "Hong_kong": 6000, "Singapore": 7000},
    "Thailand":      {"US_east": 8800, "Hong_kong": 1500, "Singapore": 900},
    "Japan":         {"US_east": 6800, "Hong_kong": 1300, "Singapore": 2300},
    "Russia":        {"US_east": 5200, "Hong_kong": 3600, "Singapore": 4300},
}

def get_country_for_ip(ip):
    for entry in ip_country_data:
        if entry["ip"] == ip:
            return entry["country"]
    return "Unknown"

def extract_ip(url):
    try:
        return get_ip_from_url(url)
    except:
        return None

def load_and_prepare_data(json_file_path="json/jobs_with_subjobs.json"):
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{json_file_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON from '{json_file_path}'.")
        return None

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
                    'ping_avg_ms': ping.get('avg'),
                    'ping_max_ms': ping.get('max'),
                    'ping_min_ms': ping.get('min'),
                })

    df = pd.DataFrame(extracted_data)
    return df

def calculate_score(order_ref, order_test, max_points_top1, max_points_top2, max_points_top3):
    """
    Calculate a score comparing two orders.
    - Perfect match gets max points.
    - Mismatches penalized by difference in position.
    - Missing items penalized by maximum penalty.
    - Returns score, max possible score, and details.
    """
    score = 0
    details = []
    max_score = 0

    # Calculate max score assuming perfect match
    for i in range(len(order_ref)):
        if i == 0:
            max_score += max_points_top1
        elif i == 1:
            max_score += max_points_top2
        elif i == 2:
            max_score += max_points_top3
        else:
            max_score += max_points_top3  # Positions > 2 treated same as 3rd

    for i, rk in enumerate(order_ref):
        if rk not in order_test:
            penalty = len(order_ref)  # max penalty for missing rk
            score -= penalty
            details.append(f"{rk} not in test order: -{penalty}")
            continue
        pos_in_test = order_test.index(rk)
        diff = abs(i - pos_in_test)
        if diff == 0:
            # Perfect match
            if i == 0:
                points = max_points_top1
            elif i == 1:
                points = max_points_top2
            elif i == 2:
                points = max_points_top3
            else:
                points = max_points_top3
            score += points
            details.append(f"{rk} matched position {i}, +{points}")
        else:
            penalty = diff
            score -= penalty
            details.append(f"{rk} position diff {diff}, -{penalty}")

    return score, max_score, details

def generate_graphs_per_ip(df, output_pdf_path="latency_with_routingKeys/all_ips_latency_report.pdf"):
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)

    successful_df = df[df['is_success'] == True].copy()

    ip_routing_counts = successful_df.groupby('ip')['routing_key'].nunique()
    ips_to_include = ip_routing_counts[ip_routing_counts >= 2].index.tolist()

    filtered_df = successful_df[successful_df['ip'].isin(ips_to_include)]

    if filtered_df.empty:
        print("No IPs with 2 or more routing keys found after filtering.")
        return

    routing_keys = sorted(filtered_df['routing_key'].unique())
    palette = sns.color_palette("tab10", n_colors=len(routing_keys))
    color_map = dict(zip(routing_keys, palette))

    with PdfPages(output_pdf_path) as pdf:
        for ip, ip_df in filtered_df.groupby('ip'):
            country = get_country_for_ip(ip)
            title_prefix = f"IP: {ip} ({country})"

            # Aggregate data for scoring
            agg = ip_df.groupby('routing_key').agg({
                'ping_min_ms': 'mean',
                'time_to_first_byte_ms': 'mean'
            }).reset_index()

            dist_map = distance_miles.get(country, {})
            present_rks = agg['routing_key'].tolist()

            # Order by distance in miles
            miles_order = sorted(present_rks, key=lambda rk: dist_map.get(rk, 99999))
            latency_order = agg.sort_values('ping_min_ms')['routing_key'].tolist()
            ttfb_order = agg.sort_values('time_to_first_byte_ms')['routing_key'].tolist()

            # Calculate scores and max scores
            latency_score, latency_max, latency_details = calculate_score(
                order_ref=miles_order,
                order_test=latency_order,
                max_points_top1=6,
                max_points_top2=5,
                max_points_top3=4,
            )

            ttfb_score, ttfb_max, ttfb_details = calculate_score(
                order_ref=miles_order,
                order_test=ttfb_order,
                max_points_top1=2,
                max_points_top2=1,
                max_points_top3=1,
            )

            # Normalize scores between -1 and 1
            latency_norm = latency_score / latency_max if latency_max else 0
            ttfb_norm = ttfb_score / ttfb_max if ttfb_max else 0

            final_score = 0.8 * latency_norm + 0.2 * ttfb_norm
            threshold = 0.7
            pass_fail = "above threshold" if final_score >= threshold else f"below threshold ({threshold})"

            # Page 1: Plots
            fig, axs = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle(title_prefix, fontsize=16)

            sns.scatterplot(data=ip_df, x='ping_min_ms', y='download_speed_mbps', hue='routing_key', palette=color_map, ax=axs[0, 0])
            axs[0, 0].set_title("Ping min vs Download Speed")
            axs[0, 0].set_xlabel("Ping Min (ms)")
            axs[0, 0].set_ylabel("Download Speed (Mbps)")
            if len(ip_df['routing_key'].unique()) > 1:
                axs[0, 0].legend(title="Routing Key")
            else:
                axs[0, 0].legend().remove()

            sns.scatterplot(data=ip_df, x='time_to_first_byte_ms', y='download_speed_mbps', hue='routing_key', palette=color_map, ax=axs[0, 1])
            axs[0, 1].set_title("TTFB vs Download Speed")
            axs[0, 1].set_xlabel("Time To First Byte (ms)")
            axs[0, 1].set_ylabel("Download Speed (Mbps)")
            if len(ip_df['routing_key'].unique()) > 1:
                axs[0, 1].legend(title="Routing Key")
            else:
                axs[0, 1].legend().remove()

            sns.boxplot(data=ip_df, x='routing_key', y='ping_min_ms', hue='routing_key', palette=color_map, ax=axs[1, 0], legend=False)
            axs[1, 0].set_title("Ping Min Distribution by Routing Key")
            axs[1, 0].set_xlabel("Routing Key")
            axs[1, 0].set_ylabel("Ping Min (ms)")

            sns.boxplot(data=ip_df, x='routing_key', y='time_to_first_byte_ms', hue='routing_key', palette=color_map, ax=axs[1, 1], legend=False)
            axs[1, 1].set_title("TTFB Distribution by Routing Key")
            axs[1, 1].set_xlabel("Routing Key")
            axs[1, 1].set_ylabel("Time To First Byte (ms)")

            plt.tight_layout(rect=[0, 0, 1, 0.95])
            pdf.savefig(fig)
            plt.close(fig)

            # Page 2: Text report
            fig_text = plt.figure(figsize=(8.5, 11))
            fig_text.clf()
            text = f"""
Latency report for IP {ip} ({country})

Distance order by routing key: {miles_order}
Latency order (ping_min_ms): {latency_order}
TTFB order (time_to_first_byte_ms): {ttfb_order}

Latency score: {latency_score} / {latency_max}
Latency details:
- {'; '.join(latency_details)}

TTFB score: {ttfb_score} / {ttfb_max}
TTFB details:
- {'; '.join(ttfb_details)}

Final weighted score: {final_score:.2f} -> {pass_fail}
"""
            plt.axis('off')
            plt.text(0.05, 0.95, text, fontsize=12, verticalalignment='top', wrap=True)
            pdf.savefig(fig_text)
            plt.close(fig_text)

            print(f"Added report for IP {ip} to combined PDF")

def main():
    print("Loading data...")
    df = load_and_prepare_data()
    if df is None or df.empty:
        print("No data loaded. Exiting.")
        return

    print("Generating combined PDF report for all IPs with scoring...")
    generate_graphs_per_ip(df)
    print("Done.")

if __name__ == "__main__":
    main()
