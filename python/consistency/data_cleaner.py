import pandas as pd
import numpy as np
import json
import re
from datetime import datetime, timezone
import warnings
import os

warnings.filterwarnings('ignore')

class NodeTimeConsistencyAnalyzer:
    """
    Cleans and reorganizes data for time consistency research.
    Each record represents one subjob measurement grouped by storage node (identified from URL).
    Download metrics from multiple workers are aggregated per subjob per node.
    Missing values default to 0 where necessary.
    """

    def __init__(self):
        self.jobs_data = []
        self.subjobs_data = []
        self.geo_data = {}

    def extract_node_key(self, url):
        match = re.search(r'//([^/]+)', url)
        return match.group(1) if match else None

    def parse_timestamp(self, ts):
        try:
            if ts and ts.endswith('Z'):
                return datetime.fromisoformat(ts[:-1] + '+00:00')
            elif ts:
                return datetime.fromisoformat(ts)
            return None
        except:
            return None

    def load_data(self, jobs_file, subjobs_file, geo_file):
        print("Loading data...")
        with open(jobs_file, 'r') as f:
            self.jobs_data = json.load(f)
        print(f"Loaded {len(self.jobs_data)} jobs")

        with open(subjobs_file, 'r') as f:
            self.subjobs_data = json.load(f)
        print(f"Loaded detailed subjob data for {len(self.subjobs_data)} job entries")

        with open(geo_file, 'r') as f:
            geo_list = json.load(f)
            self.geo_data = {entry['ip']: entry for entry in geo_list}
        print(f"Loaded {len(self.geo_data)} geo-location entries")

    def clean(self):
        print("Cleaning and organizing data by storage node...")
        cleaned = []
        subjob_map = {}
        for job in self.subjobs_data:
            for sub in job.get('sub_jobs', []):
                subjob_map[sub['id']] = sub

        for job in self.jobs_data:
            job_id = job['id']
            node_key = self.extract_node_key(job.get('url', ''))
            ip_match = re.match(r'(\d+\.\d+\.\d+\.\d+)', node_key)
            ip = ip_match.group(1) if ip_match else None
            geo = self.geo_data.get(ip, {})

            for sub in job.get('sub_jobs', []):
                full_sub = subjob_map.get(sub['id'], sub)
                worker_downloads = [w['download'] for w in full_sub.get('worker_data', []) if w.get('download')]

                # fallback to zero even if worker_downloads is empty
                speeds = [d.get('download_speed', 0) for d in worker_downloads]
                starts = [self.parse_timestamp(d.get('job_start_time')) for d in worker_downloads if d.get('job_start_time')]
                ends = [self.parse_timestamp(d.get('end_time')) for d in worker_downloads if d.get('end_time')]

                start_time = min(starts) if starts else None
                end_time = max(ends) if ends else None
                deadline = self.parse_timestamp(sub.get('deadline_at'))

                record = {
                    'node_key': node_key or '',
                    'server_ip': ip or '',
                    'job_id': job_id,
                    'subjob_id': sub['id'],
                    'routing_key': job.get('routing_key', ''),
                    'subjob_status': sub.get('status', ''),
                    'job_status': job.get('status', ''),
                    'worker_count': len(worker_downloads),
                    'download_speed_sum': float(np.sum(speeds)) if speeds else 0,
                    'avg_download_speed': float(np.mean(speeds)) if speeds else 0,
                    'download_speed_std': float(np.std(speeds)) if speeds else 0,
                    'earliest_start': start_time or '',
                    'latest_end': end_time or '',
                    'actual_duration_ms': (end_time - start_time).total_seconds() * 1000 if start_time and end_time else 0,
                    'deadline_variance_ms': (end_time - deadline).total_seconds() * 1000 if end_time and deadline else 0,
                    'met_deadline': int(end_time <= deadline) if deadline and end_time else 0,
                    'deadline_at': sub.get('deadline_at', ''),
                    'country': geo.get('country', ''),
                    'country_code': geo.get('country_code', ''),
                    'continent': geo.get('continent', ''),
                    'asn': geo.get('asn', ''),
                    'as_name': geo.get('as_name', '')
                }
                cleaned.append(record)

        df = pd.DataFrame(cleaned)
        print(f"Finished cleaning. Total aggregated subjob records: {len(df)}")
        return df

    def save_to_csv(self, df, out_path):
        # Ensure the directory exists
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        df.to_csv(out_path, index=False)
        print(f"Saved cleaned data to {out_path}")

def main():
    """Main function to run the data cleaning process"""
    analyzer = NodeTimeConsistencyAnalyzer()
    
    # Define paths
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to project root
    json_path = os.path.join(base_path, 'json')
    csv_path = os.path.join(base_path, 'csv')
    
    # Load and clean data
    analyzer.load_data(
        jobs_file=os.path.join(json_path, 'jobs_data.json'),
        subjobs_file=os.path.join(json_path, 'jobs_with_subjobs.json'),
        geo_file=os.path.join(json_path, 'geo-location.json')
    )
    
    df = analyzer.clean()
    
    # Save to CSV
    out_csv = os.path.join(csv_path, 'node_level_cleaned_data.csv')
    analyzer.save_to_csv(df, out_csv)

    print("\nSample cleaned data:")
    print(df.head())

if __name__ == '__main__':
    main()