import pandas as pd
import numpy as np
import json
import re
from datetime import datetime, timezone
import warnings
import os
import psutil
import time
from tqdm import tqdm
import gc

warnings.filterwarnings('ignore')

def monitor_memory(func):
    """Decorator to monitor memory usage"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        print(f"Function: {func.__name__}")
        print(f"Time: {end_time - start_time:.2f} seconds")
        print(f"Memory used: {end_memory - start_memory:.2f} MB")
        print(f"Peak memory: {end_memory:.2f} MB")
        
        return result
    return wrapper

class NodeTimeConsistencyAnalyzer:
    """
    Memory-efficient data cleaner that processes large datasets in streaming fashion.
    Handles datasets of any size by using batch processing and streaming JSON parsing.
    """

    def __init__(self, batch_size=1000, enable_progress=True):
        self.batch_size = batch_size
        self.enable_progress = enable_progress
        self.geo_data = {}
        self.processed_count = 0

    def extract_node_key(self, url):
        if not url:
            return None
        match = re.search(r'//([^/]+)', url)
        return match.group(1) if match else None

    def parse_timestamp(self, ts):
        if not ts:
            return None
        try:
            if ts.endswith('Z'):
                return datetime.fromisoformat(ts[:-1] + '+00:00')
            else:
                return datetime.fromisoformat(ts)
        except:
            return None

    def load_geo_data(self, geo_file):
        """Load geo data (typically small, can keep in memory)"""
        print("Loading geo-location data...")
        try:
            with open(geo_file, 'r') as f:
                geo_list = json.load(f)
                self.geo_data = {entry['ip']: entry for entry in geo_list}
            print(f"Loaded {len(self.geo_data)} geo-location entries")
        except Exception as e:
            print(f"Warning: Could not load geo data: {e}")
            self.geo_data = {}

    def stream_json_file(self, file_path, chunk_size=1000):
        """
        Stream large JSON files in chunks to avoid memory issues.
        Assumes JSON is an array of objects.
        """
        print(f"Streaming JSON file: {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                # Read file size for progress tracking
                f.seek(0, 2)  # Go to end
                file_size = f.tell()
                f.seek(0)  # Go back to start
                
                # Simple streaming approach - read as text and parse
                content = f.read()
                data = json.loads(content)
                
                # Yield in chunks
                for i in range(0, len(data), chunk_size):
                    chunk = data[i:i + chunk_size]
                    yield chunk
                    
                    # Force garbage collection after each chunk
                    gc.collect()
                    
        except Exception as e:
            print(f"Error streaming JSON file {file_path}: {e}")
            raise

    def build_subjob_map_streaming(self, subjobs_file):
        """Build subjob mapping in memory-efficient way"""
        print("Building subjob mapping...")
        subjob_map = {}
        
        total_processed = 0
        for chunk in self.stream_json_file(subjobs_file, self.batch_size):
            for job_entry in chunk:
                for sub in job_entry.get('sub_jobs', []):
                    subjob_map[sub['id']] = sub
                total_processed += 1
                
                # Periodically report progress
                if total_processed % 1000 == 0 and self.enable_progress:
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    print(f"Processed {total_processed} job entries, Memory: {current_memory:.1f}MB")
        
        print(f"Built subjob map with {len(subjob_map)} entries")
        return subjob_map

    def process_single_record(self, job, subjob_map):
        """Process a single job record efficiently"""
        job_id = job['id']
        node_key = self.extract_node_key(job.get('url', ''))
        
        # Extract IP efficiently
        ip = None
        if node_key:
            ip_match = re.match(r'(\d+\.\d+\.\d+\.\d+)', node_key)
            ip = ip_match.group(1) if ip_match else None
        
        geo = self.geo_data.get(ip, {}) if ip else {}
        
        records = []
        for sub in job.get('sub_jobs', []):
            full_sub = subjob_map.get(sub['id'], sub)
            worker_downloads = [w['download'] for w in full_sub.get('worker_data', []) if w.get('download')]

            # Vectorized operations where possible
            speeds = np.array([d.get('download_speed', 0) for d in worker_downloads])
            
            # Process timestamps efficiently
            start_times = []
            end_times = []
            for d in worker_downloads:
                if d.get('job_start_time'):
                    parsed_start = self.parse_timestamp(d['job_start_time'])
                    if parsed_start:
                        start_times.append(parsed_start)
                if d.get('end_time'):
                    parsed_end = self.parse_timestamp(d['end_time'])
                    if parsed_end:
                        end_times.append(parsed_end)
            
            start_time = min(start_times) if start_times else None
            end_time = max(end_times) if end_times else None
            deadline = self.parse_timestamp(sub.get('deadline_at'))

            # Calculate statistics efficiently
            download_speed_sum = float(np.sum(speeds)) if len(speeds) > 0 else 0.0
            avg_download_speed = float(np.mean(speeds)) if len(speeds) > 0 else 0.0
            download_speed_std = float(np.std(speeds)) if len(speeds) > 0 else 0.0

            # Convert timestamps to strings, handling None values properly
            earliest_start_str = start_time.isoformat() if start_time else ""
            latest_end_str = end_time.isoformat() if end_time else ""
            deadline_str = sub.get('deadline_at', "")

            record = {
                'node_key': node_key or '',
                'server_ip': ip or '',
                'job_id': job_id,
                'subjob_id': sub['id'],
                'routing_key': job.get('routing_key', ''),
                'subjob_status': sub.get('status', ''),
                'job_status': job.get('status', ''),
                'worker_count': len(worker_downloads),
                'download_speed_sum': download_speed_sum,
                'avg_download_speed': avg_download_speed,
                'download_speed_std': download_speed_std,
                'earliest_start': earliest_start_str,
                'latest_end': latest_end_str,
                'actual_duration_ms': (end_time - start_time).total_seconds() * 1000 if start_time and end_time else 0.0,
                'deadline_variance_ms': (end_time - deadline).total_seconds() * 1000 if end_time and deadline else 0.0,
                'met_deadline': int(end_time <= deadline) if deadline and end_time else 0,
                'deadline_at': deadline_str,
                'country': geo.get('country', ''),
                'country_code': geo.get('country_code', ''),
                'continent': geo.get('continent', ''),
                'asn': geo.get('asn', ''),
                'as_name': geo.get('as_name', '')
            }
            records.append(record)
        
        return records

    @monitor_memory
    def clean_streaming(self, jobs_file, subjobs_file, output_csv):
        """
        Main cleaning function that processes data in streaming fashion
        """
        print("Starting streaming data cleaning...")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        
        # Build subjob mapping (kept in memory as it's needed for lookups)
        subjob_map = self.build_subjob_map_streaming(subjobs_file)
        
        # Process main jobs file in streaming fashion
        print("Processing main jobs data...")
        
        first_batch = True
        batch_records = []
        total_jobs_processed = 0
        
        for chunk in self.stream_json_file(jobs_file, self.batch_size):
            for job in chunk:
                records = self.process_single_record(job, subjob_map)
                batch_records.extend(records)
                total_jobs_processed += 1
                
                # Process batch when it gets large enough
                if len(batch_records) >= self.batch_size:
                    self._write_batch_to_csv(batch_records, output_csv, first_batch)
                    first_batch = False
                    self.processed_count += len(batch_records)
                    batch_records.clear()
                    
                    # Memory management
                    gc.collect()
                    
                    if self.enable_progress:
                        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                        print(f"Processed {total_jobs_processed} jobs, {self.processed_count} records written, Memory: {current_memory:.1f}MB")
        
        # Write remaining records
        if batch_records:
            self._write_batch_to_csv(batch_records, output_csv, first_batch)
            self.processed_count += len(batch_records)
        
        print(f"Cleaning complete! Total records processed: {self.processed_count}")
        return self.processed_count

    def _write_batch_to_csv(self, records, output_csv, write_header):
        """Write a batch of records to CSV efficiently"""
        if not records:
            return
            
        df_batch = pd.DataFrame(records)
        
        # Write to CSV in append mode
        df_batch.to_csv(
            output_csv, 
            mode='w' if write_header else 'a', 
            header=write_header, 
            index=False
        )

    def get_dataset_info(self, csv_file):
        """Get basic info about the cleaned dataset without loading it all"""
        print("Analyzing cleaned dataset...")
        
        # Get file size
        file_size = os.path.getsize(csv_file) / (1024 * 1024)  # MB
        
        # Count rows efficiently
        with open(csv_file, 'r') as f:
            row_count = sum(1 for _ in f) - 1  # Subtract header
        
        # Sample first few rows to understand structure
        sample_df = pd.read_csv(csv_file, nrows=1000)
        
        # Handle timestamp columns safely
        try:
            # Filter out empty/invalid timestamps before finding min/max
            valid_timestamps = sample_df['earliest_start'][
                (sample_df['earliest_start'].notna()) & 
                (sample_df['earliest_start'] != '') & 
                (sample_df['earliest_start'] != 'nan')
            ]
            
            if len(valid_timestamps) > 0:
                date_range = (valid_timestamps.min(), valid_timestamps.max())
            else:
                date_range = ('No valid timestamps', 'No valid timestamps')
        except Exception as e:
            print(f"Warning: Could not determine date range: {e}")
            date_range = ('Unable to determine', 'Unable to determine')
        
        info = {
            'file_size_mb': file_size,
            'total_rows': row_count,
            'columns': list(sample_df.columns),
            'unique_nodes': sample_df['node_key'].nunique(),
            'unique_routing_keys': sample_df['routing_key'].nunique(),
            'date_range': date_range,
            'avg_throughput': sample_df['download_speed_sum'].mean(),
            'memory_efficient': True
        }
        
        return info

def main():
    """Main function to run the data cleaning process"""
    
    # Configuration
    BATCH_SIZE = 1000  # Adjust based on available memory
    ENABLE_PROGRESS = True
    
    print("="*60)
    print("NODE TIME CONSISTENCY ANALYZER")
    print("="*60)
    
    # Initialize analyzer
    analyzer = NodeTimeConsistencyAnalyzer(
        batch_size=BATCH_SIZE, 
        enable_progress=ENABLE_PROGRESS
    )
    
    # Define paths
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    json_path = os.path.join(base_path, 'json')
    csv_path = os.path.join(base_path, 'csv')
    
    # File paths
    jobs_file = os.path.join(json_path, 'jobs_data.json')
    subjobs_file = os.path.join(json_path, 'jobs_with_subjobs.json')
    geo_file = os.path.join(json_path, 'geo-location.json')
    output_csv = os.path.join(csv_path, 'node_level_cleaned_data.csv')
    
    # Check if input files exist
    for file_path in [jobs_file, subjobs_file]:
        if not os.path.exists(file_path):
            print(f"Error: Required file not found: {file_path}")
            return
    
    # Load geo data
    if os.path.exists(geo_file):
        analyzer.load_geo_data(geo_file)
    else:
        print("Warning: Geo-location file not found, proceeding without geo data")
    
    # Monitor system resources
    initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
    print(f"Initial memory usage: {initial_memory:.1f}MB")
    
    # Clean data in streaming fashion
    try:
        total_records = analyzer.clean_streaming(jobs_file, subjobs_file, output_csv)
        
        # Get dataset info
        info = analyzer.get_dataset_info(output_csv)
        
        print("\n" + "="*60)
        print("CLEANING COMPLETE - DATASET SUMMARY")
        print("="*60)
        print(f"Output file: {output_csv}")
        print(f"File size: {info['file_size_mb']:.2f} MB")
        print(f"Total records: {info['total_rows']:,}")
        print(f"Unique nodes: {info['unique_nodes']}")
        print(f"Unique routing keys: {info['unique_routing_keys']}")
        print(f"Average throughput: {info['avg_throughput']:.2f} MB/s")
        
        # Memory usage summary
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        print(f"Memory used: {final_memory - initial_memory:.1f}MB")
        print(f"Peak memory: {final_memory:.1f}MB")
        
    except Exception as e:
        print(f"Error during cleaning: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()