import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import seaborn as sns
from datetime import datetime, time
import warnings
import os
import psutil
import random
from tqdm import tqdm
import gc
import math

warnings.filterwarnings('ignore')

# Set style for better-looking plots
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

def monitor_memory(func):
    """Decorator to monitor memory usage"""
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        result = func(*args, **kwargs)
        
        end_time = datetime.now()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        print(f"Function: {func.__name__}")
        print(f"Time: {(end_time - start_time).total_seconds():.2f} seconds")
        print(f"Memory used: {end_memory - start_memory:.2f} MB")
        print(f"Peak memory: {end_memory:.2f} MB")
        
        return result
    return wrapper

class NodeThroughputAnalyzer:
    """
    Memory-efficient analyzer that can handle large datasets through sampling,
    chunked processing, and paginated output generation.
    """
    
    def __init__(self, data_file, max_sample_size=50000, max_nodes_per_pdf=50, enable_progress=True):
        """
        Initialize with memory-conscious defaults
        
        Args:
            data_file: Path to the cleaned CSV data
            max_sample_size: Maximum number of rows to load for analysis (None = load all)
            max_nodes_per_pdf: Maximum nodes per PDF file (prevents huge PDFs)
            enable_progress: Show progress bars and memory usage
        """
        self.data_file = data_file
        self.max_sample_size = max_sample_size
        self.max_nodes_per_pdf = max_nodes_per_pdf
        self.enable_progress = enable_progress
        
        # Will be populated by prepare_data
        self.df = None
        self.df_valid = None
        self.unique_nodes = None
        self.unique_routing_keys = None
        self.unique_worker_counts = None
        self.is_sampled = False
        
        print(f"Initialized analyzer with max_sample_size={max_sample_size}")
        
    def get_dataset_info(self):
        """Get dataset information without loading the full file"""
        print("Analyzing dataset size...")
        
        file_size = os.path.getsize(self.data_file) / (1024 * 1024)  # MB
        
        # Count rows efficiently
        with open(self.data_file, 'r') as f:
            total_rows = sum(1 for _ in f) - 1  # Subtract header
        
        # Sample small subset to understand structure
        sample_df = pd.read_csv(self.data_file, nrows=1000)
        estimated_memory = (total_rows / 1000) * (sample_df.memory_usage(deep=True).sum() / 1024 / 1024)
        
        info = {
            'file_size_mb': file_size,
            'total_rows': total_rows,
            'estimated_memory_mb': estimated_memory,
            'needs_sampling': estimated_memory > 1000  # Sample if >1GB estimated
        }
        
        print(f"Dataset info: {total_rows:,} rows, {file_size:.1f}MB file, ~{estimated_memory:.1f}MB memory needed")
        
        return info
    
    @monitor_memory    
    def load_data_smart(self):
        """Intelligently load data based on size - sample if too large"""
        info = self.get_dataset_info()
        
        if self.max_sample_size and (info['total_rows'] > self.max_sample_size or info['needs_sampling']):
            print(f"Large dataset detected. Sampling {self.max_sample_size:,} rows from {info['total_rows']:,} total rows")
            self.df = self._load_sampled_data(info['total_rows'])
            self.is_sampled = True
        else:
            print("Loading full dataset...")
            self.df = pd.read_csv(self.data_file)
            self.is_sampled = False
            
        print(f"Loaded {len(self.df):,} rows into memory")
        return self.df
    
    def _load_sampled_data(self, total_rows):
        """Load a stratified sample of the data"""
        # Calculate skip pattern for roughly even sampling
        skip_ratio = total_rows / self.max_sample_size
        
        if skip_ratio <= 1:
            return pd.read_csv(self.data_file)
        
        # Create list of row indices to skip
        rows_to_skip = []
        for i in range(1, total_rows + 1):  # Start from 1 to preserve header
            if i % int(skip_ratio) != 0:
                rows_to_skip.append(i)
        
        # Randomly skip some additional rows to get closer to target sample size
        if len(rows_to_skip) > total_rows - self.max_sample_size:
            rows_to_skip = random.sample(rows_to_skip, total_rows - self.max_sample_size)
        
        print(f"Skipping {len(rows_to_skip):,} rows...")
        return pd.read_csv(self.data_file, skiprows=rows_to_skip)
        
    def prepare_data(self):
        """Prepare data for analysis with memory efficiency"""
        print("Preparing data for analysis...")
        
        # Load data intelligently
        self.load_data_smart()
        
        # Convert timestamps efficiently using vectorized operations
        print("Converting timestamps...")
        self.df['earliest_start'] = pd.to_datetime(self.df['earliest_start'], errors='coerce')
        self.df['latest_end'] = pd.to_datetime(self.df['latest_end'], errors='coerce')
        self.df['deadline_at'] = pd.to_datetime(self.df['deadline_at'], errors='coerce')
        
        # Extract time of day efficiently
        self.df['time_of_day'] = self.df['earliest_start'].apply(
            lambda x: datetime.combine(datetime.today().date(), x.time()) 
            if pd.notna(x) else pd.NaT
        )
        
        # Filter out rows with missing time data
        self.df_valid = self.df[self.df['time_of_day'].notna()].copy()
        
        # Get unique values efficiently
        self.unique_nodes = self.df_valid['node_key'].unique()
        self.unique_routing_keys = sorted(self.df_valid['routing_key'].unique())
        self.unique_worker_counts = sorted(self.df_valid['worker_count'].unique())
        
        # Calculate size mapping for worker counts
        self.min_worker = min(self.unique_worker_counts) if self.unique_worker_counts else 1
        self.max_worker = max(self.unique_worker_counts) if self.unique_worker_counts else 1
        
        print(f"Data prepared: {len(self.df_valid):,} valid subjobs across {len(self.unique_nodes)} nodes")
        print(f"Unique routing keys: {len(self.unique_routing_keys)}")
        print(f"Worker counts found: {self.unique_worker_counts}")
        
        if self.is_sampled:
            print("⚠️  Note: Results are based on a sample of the full dataset")
        
        # Clean up original dataframe to save memory
        del self.df
        gc.collect()
        
    def get_dot_size(self, worker_count):
        """Convert worker count to dot size with better scaling"""
        if self.max_worker == self.min_worker:
            return 300
        
        # Exponential scaling for more dramatic size differences
        normalized = (worker_count - self.min_worker) / (self.max_worker - self.min_worker)
        size = 100 + (normalized ** 1.5) * 700
        return size
    
    def plot_nodes_by_routing_key_paginated(self, output_dir):
        """Create paginated PDF output to handle large datasets"""
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Split nodes into batches
        node_batches = []
        for i in range(0, len(self.unique_nodes), self.max_nodes_per_pdf):
            batch = self.unique_nodes[i:i + self.max_nodes_per_pdf]
            node_batches.append(batch)
        
        print(f"Creating {len(node_batches)} PDF files with up to {self.max_nodes_per_pdf} nodes each")
        
        pdf_files = []
        
        # Create overview PDF first
        overview_pdf = os.path.join(output_dir, '00_overview_analysis.pdf')
        with PdfPages(overview_pdf) as pdf:
            self.create_overview_page(pdf)
        pdf_files.append(overview_pdf)
        print(f"Created overview: {overview_pdf}")
        
        # Process each batch
        for batch_idx, node_batch in enumerate(node_batches):
            batch_pdf = os.path.join(output_dir, f'{batch_idx+1:02d}_nodes_batch_{batch_idx+1}.pdf')
            
            print(f"Processing batch {batch_idx+1}/{len(node_batches)}: {len(node_batch)} nodes")
            
            with PdfPages(batch_pdf) as pdf:
                # Add batch overview page
                self.create_batch_overview_page(pdf, node_batch, batch_idx + 1)
                
                # Process nodes in this batch
                for node_idx, node_key in enumerate(node_batch):
                    if self.enable_progress and node_idx % 10 == 0:
                        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                        print(f"  Processing node {node_idx+1}/{len(node_batch)}, Memory: {current_memory:.1f}MB")
                    
                    self.create_node_page(pdf, node_key)
                    
                    # Periodic garbage collection
                    if node_idx % 10 == 0:
                        gc.collect()
            
            pdf_files.append(batch_pdf)
            print(f"Created batch PDF: {batch_pdf}")
        
        print(f"\nAnalysis complete! Created {len(pdf_files)} PDF files:")
        for pdf_file in pdf_files:
            file_size = os.path.getsize(pdf_file) / (1024 * 1024)
            print(f"  - {os.path.basename(pdf_file)} ({file_size:.1f}MB)")
        
        return pdf_files
        
    def create_node_page(self, pdf, node_key):
        """Create a page for a single node with efficient data filtering"""
        
        # Get data for this node efficiently
        node_data = self.df_valid[self.df_valid['node_key'] == node_key].copy()
        
        # Skip if too few data points
        if len(node_data) < 3:
            return
        
        # Get routing keys present for this node
        node_routing_keys = sorted(node_data['routing_key'].unique())
        
        if len(node_routing_keys) == 0:
            return
        
        # Get node info for title
        node_ip = node_data['server_ip'].iloc[0]
        node_country = node_data['country'].iloc[0]
        
        # Determine subplot layout efficiently
        n_routing_keys = len(node_routing_keys)
        n_rows, n_cols = self._calculate_subplot_layout(n_routing_keys)
        
        # Process routing keys in batches if necessary
        max_subplots = n_rows * n_cols
        for batch_start in range(0, n_routing_keys, max_subplots):
            batch_end = min(batch_start + max_subplots, n_routing_keys)
            batch_routing_keys = node_routing_keys[batch_start:batch_end]
            
            # Create figure
            fig = plt.figure(figsize=(20, 14))
            
            # Add main title
            fig.suptitle(
                f'Node: {node_key}\n in {node_country} using following networks',
                fontsize=24
            )
            
            # Calculate common axis limits for all subplots on this page
            batch_data = node_data[node_data['routing_key'].isin(batch_routing_keys)]
            x_min, x_max, y_min, y_max = self._calculate_axis_limits(batch_data)
            
            # Create subplot for each routing key
            for idx, routing_key in enumerate(batch_routing_keys):
                ax = plt.subplot(n_rows, n_cols, idx + 1)
                
                # Get data for this routing key
                routing_data = node_data[node_data['routing_key'] == routing_key].copy()
                routing_data = routing_data.sort_values('time_of_day')
                
                # Create the plot
                self.create_routing_key_plot(ax, routing_data, routing_key)
                
                # Set consistent axis limits
                ax.set_xlim(x_min, x_max)
                ax.set_ylim(y_min, y_max)
            
            # Remove empty subplots
            for idx in range(len(batch_routing_keys), max_subplots):
                ax = plt.subplot(n_rows, n_cols, idx + 1)
                ax.axis('off')
            
            # Adjust layout and save
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches='tight')
            plt.close()
    
    def _calculate_subplot_layout(self, n_items):
        """Calculate optimal subplot layout"""
        if n_items == 1:
            return 1, 1
        elif n_items == 2:
            return 1, 2
        elif n_items <= 4:
            return 2, 2
        elif n_items <= 6:
            return 2, 3
        else:
            return 3, 3
    
    def _calculate_axis_limits(self, data):
        """Calculate common axis limits for consistent scaling"""
        if len(data) == 0:
            return 0, 1, 0, 1
            
        # Time range (x-axis)
        min_time = data['time_of_day'].min()
        max_time = data['time_of_day'].max()
        time_padding = (max_time - min_time) * 0.05 if max_time > min_time else pd.Timedelta(minutes=30)
        x_min = min_time - time_padding
        x_max = max_time + time_padding
        
        # Throughput range (y-axis)
        min_throughput = data['download_speed_sum'].min()
        max_throughput = data['download_speed_sum'].max()
        throughput_padding = (max_throughput - min_throughput) * 0.1 if max_throughput > min_throughput else 10
        y_min = max(0, min_throughput - throughput_padding)
        y_max = max_throughput + throughput_padding
        
        return x_min, x_max, y_min, y_max
        
    def create_routing_key_plot(self, ax, data, routing_key):
        """Create a single plot for a specific routing key with optimized rendering"""
        
        if len(data) == 0:
            ax.text(0.5, 0.5, 'No data available', transform=ax.transAxes, 
                   ha='center', va='center', fontsize=16)
            return
        
        # Get unique worker counts in this data
        worker_counts = sorted(data['worker_count'].unique())
        
        # Use efficient color mapping
        colors = plt.cm.Set1(np.linspace(0, 1, min(len(worker_counts), 9)))
        if len(worker_counts) > 9:
            colors = plt.cm.tab20(np.linspace(0, 1, len(worker_counts)))
        
        # Plot each worker count with different colors and sizes
        for idx, worker_count in enumerate(worker_counts):
            worker_data = data[data['worker_count'] == worker_count]
            dot_size = self.get_dot_size(worker_count)
            color = colors[idx % len(colors)]
            
            # Plot scatter points
            ax.scatter(worker_data['time_of_day'], 
                      worker_data['download_speed_sum'],
                      s=dot_size,
                      color=color,
                      alpha=0.7,
                      edgecolors='black',
                      linewidth=1.5,
                      label=f'{worker_count} workers')
        
        # Connect points with line if multiple points exist
        if len(data) > 1:
            data_sorted = data.sort_values('time_of_day')
            ax.plot(data_sorted['time_of_day'], 
                   data_sorted['download_speed_sum'],
                   color='lightgray',
                   alpha=0.4,
                   linestyle='-',
                   linewidth=1,
                   zorder=0)
        
        # Format the plot
        ax.set_xlabel('Time of Day', fontsize=24)
        ax.set_ylabel('Throughput (MB/s)', fontsize=24)
        ax.set_title(f'Routing Key: {routing_key} (n={len(data)} measurements)', fontsize=24, pad=20)
        
        # Format x-axis to show time
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.tick_params(axis='x', labelsize=12, rotation=45)
        ax.tick_params(axis='y', labelsize=12)
        
        # Add grid
        ax.grid(True, alpha=0.3)
        
        # Add legend with smart positioning
        if len(worker_counts) <= 6:
            legend = ax.legend(loc='upper right', fontsize=11, title='Worker Count', 
                             title_fontsize=12, framealpha=0.9)
        else:
            legend = ax.legend(loc='upper right', fontsize=9, title='Worker Count', 
                             title_fontsize=10, ncol=2, framealpha=0.9)
        
        # Style legend
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_edgecolor('black')
        
        # Add statistics box
        stats_text = (
            f'μ={data["download_speed_sum"].mean():.1f} MB/s\n'
            f'σ={data["download_speed_sum"].std():.1f}\n'
            f'Range: {data["download_speed_sum"].min():.1f}-{data["download_speed_sum"].max():.1f}\n'
            f'Workers: {data["worker_count"].min()}-{data["worker_count"].max()}'
        )
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8),
               verticalalignment='top', fontsize=10, weight='bold')
        
        # Add size reference
        size_ref_text = 'Color & Size = Worker Count\n(Larger & Different Color = More Workers)'
        ax.text(0.98, 0.02, size_ref_text, transform=ax.transAxes,
               bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8),
               verticalalignment='bottom', horizontalalignment='right', 
               fontsize=8, weight='bold')
        
    def create_overview_page(self, pdf):
        """Create an overview page with summary statistics"""
        
        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        sample_note = " (Sampled Data)" if self.is_sampled else ""
        fig.suptitle(f'Node Throughput Analysis by Routing Key - Overview{sample_note}', fontsize=24)
        
        # 1. Average throughput by routing key
        ax1 = axes[0, 0]
        routing_stats = self.df_valid.groupby('routing_key').agg({
            'download_speed_sum': ['mean', 'std', 'count']
        }).reset_index()
        routing_stats.columns = ['routing_key', 'mean_throughput', 'std_throughput', 'count']
        
        # Plot with error bars
        x_pos = range(len(routing_stats))
        ax1.errorbar(x_pos, 
                    routing_stats['mean_throughput'],
                    yerr=routing_stats['std_throughput'],
                    fmt='o-', capsize=5, markersize=10, linewidth=2)
        ax1.set_xlabel('Routing Key', fontsize=16)
        ax1.set_ylabel('Average Throughput (MB/s)', fontsize=16)
        ax1.set_title('Average Throughput by Routing Key', fontsize=18)
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(routing_stats['routing_key'], rotation=45, fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='y', labelsize=10)
        
        # Add count labels
        for i, row in routing_stats.iterrows():
            ax1.text(i, row['mean_throughput'] + row['std_throughput'] + 10, 
                    f'n={row["count"]}', ha='center', fontsize=10)
        
        # 2. Distribution of measurements across routing keys
        ax2 = axes[0, 1]
        routing_dist = self.df_valid['routing_key'].value_counts()
        ax2.bar(range(len(routing_dist)), routing_dist.values, alpha=0.7, edgecolor='black')
        ax2.set_xlabel('Routing Key', fontsize=16)
        ax2.set_ylabel('Number of Measurements', fontsize=16)
        ax2.set_title('Distribution of Measurements by Routing Key', fontsize=18)
        ax2.set_xticks(range(len(routing_dist)))
        ax2.set_xticklabels(routing_dist.index, rotation=45, fontsize=10)
        ax2.tick_params(axis='y', labelsize=10)
        
        # 3. Worker count distribution across routing keys
        ax3 = axes[1, 0]
        
        # Create a heatmap showing worker count distribution by routing key
        worker_routing_dist = self.df_valid.groupby(['routing_key', 'worker_count']).size().unstack(fill_value=0)
        
        # Use seaborn heatmap
        sns.heatmap(worker_routing_dist.T, annot=True, fmt='d', cmap='Blues', ax=ax3, cbar_kws={'shrink': 0.8})
        ax3.set_xlabel('Routing Key', fontsize=16)
        ax3.set_ylabel('Worker Count', fontsize=16)
        ax3.set_title('Worker Count Distribution by Routing Key', fontsize=18)
        ax3.tick_params(axis='both', labelsize=8)
        
        # 4. Throughput vs Worker Count scatter
        ax4 = axes[1, 1]
        
        # Create scatter plot with different colors for routing keys
        routing_keys = self.df_valid['routing_key'].unique()
        colors = plt.cm.Set1(np.linspace(0, 1, len(routing_keys)))
        
        for idx, routing_key in enumerate(routing_keys):
            routing_data = self.df_valid[self.df_valid['routing_key'] == routing_key]
            
            # Use smaller sizes for overview plot
            sizes = [self.get_dot_size(wc) / 8 for wc in routing_data['worker_count']]
            
            ax4.scatter(routing_data['worker_count'], 
                       routing_data['download_speed_sum'],
                       label=routing_key,
                       color=colors[idx % len(colors)],
                       alpha=0.7,
                       s=sizes,
                       edgecolors='black',
                       linewidth=0.5)
        
        ax4.set_xlabel('Worker Count', fontsize=16)
        ax4.set_ylabel('Throughput (MB/s)', fontsize=16)
        ax4.set_title('Throughput vs Worker Count by Routing Key', fontsize=16)
        ax4.legend(loc='best', fontsize=10)
        ax4.grid(True, alpha=0.3)
        ax4.tick_params(axis='both', labelsize=10)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
    def create_batch_overview_page(self, pdf, node_batch, batch_number):
        """Create an overview page for a batch of nodes"""
        
        fig, axes = plt.subplots(2, 2, figsize=(18, 12))
        fig.suptitle(f'Batch {batch_number} Overview - {len(node_batch)} Nodes', fontsize=24)
        
        # Get data for this batch of nodes
        batch_data = self.df_valid[self.df_valid['node_key'].isin(node_batch)]
        
        if len(batch_data) == 0:
            fig.text(0.5, 0.5, 'No data available for this batch', 
                    ha='center', va='center', fontsize=20)
            pdf.savefig(fig, bbox_inches='tight')
            plt.close()
            return
        
        # 1. Throughput distribution across nodes in this batch
        ax1 = axes[0, 0]
        node_stats = batch_data.groupby('node_key')['download_speed_sum'].agg(['mean', 'count']).reset_index()
        node_stats = node_stats.sort_values('mean', ascending=False)
        
        # Show top 10 nodes to avoid overcrowding
        top_nodes = node_stats.head(10)
        
        bars = ax1.bar(range(len(top_nodes)), top_nodes['mean'], alpha=0.7, edgecolor='black')
        ax1.set_xlabel('Node (Top 10)', fontsize=14)
        ax1.set_ylabel('Average Throughput (MB/s)', fontsize=14)
        ax1.set_title(f'Top Performing Nodes in Batch {batch_number}', fontsize=16)
        ax1.set_xticks(range(len(top_nodes)))
        ax1.set_xticklabels([f'Node {i+1}' for i in range(len(top_nodes))], fontsize=8)
        ax1.tick_params(axis='y', labelsize=10)
        
        # Add value labels on bars
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=8)
        
        # 2. Geographic distribution
        ax2 = axes[0, 1]
        country_dist = batch_data['country'].value_counts().head(10)
        wedges, texts, autotexts = ax2.pie(country_dist.values, labels=country_dist.index, autopct='%1.1f%%')
        
        # Set font sizes for pie chart labels
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_fontsize(8)
            
        ax2.set_title(f'Geographic Distribution (Batch {batch_number})', fontsize=16)
        
        # 3. Routing key performance in this batch
        ax3 = axes[1, 0]
        routing_stats = batch_data.groupby('routing_key')['download_speed_sum'].mean().sort_values(ascending=False)
        ax3.bar(range(len(routing_stats)), routing_stats.values, alpha=0.7, edgecolor='black')
        ax3.set_xlabel('Routing Key', fontsize=14)
        ax3.set_ylabel('Average Throughput (MB/s)', fontsize=14)
        ax3.set_title(f'Routing Key Performance (Batch {batch_number})', fontsize=16)
        ax3.set_xticks(range(len(routing_stats)))
        ax3.set_xticklabels(routing_stats.index, rotation=45, fontsize=10)
        ax3.tick_params(axis='y', labelsize=10)
        
        # 4. Batch summary statistics
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        # Calculate batch statistics
        total_measurements = len(batch_data)
        avg_throughput = batch_data['download_speed_sum'].mean()
        std_throughput = batch_data['download_speed_sum'].std()
        unique_routing_keys = batch_data['routing_key'].nunique()
        unique_countries = batch_data['country'].nunique()
        
        summary_text = f"""
BATCH {batch_number} SUMMARY

Nodes in Batch: {len(node_batch)}
Total Measurements: {total_measurements:,}
Unique Routing Keys: {unique_routing_keys}
Unique Countries: {unique_countries}

Performance Metrics:
• Average Throughput: {avg_throughput:.2f} MB/s
• Std Deviation: {std_throughput:.2f} MB/s
• Min Throughput: {batch_data['download_speed_sum'].min():.2f} MB/s
• Max Throughput: {batch_data['download_speed_sum'].max():.2f} MB/s

Worker Statistics:
• Worker Count Range: {batch_data['worker_count'].min()}-{batch_data['worker_count'].max()}
• Avg Workers per Job: {batch_data['worker_count'].mean():.1f}
        """
        
        ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes,
                fontsize=12, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()
        
    def create_summary_report(self, output_file):
        """Generate a memory-efficient summary report"""
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("NODE THROUGHPUT ANALYSIS BY ROUTING KEY - SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            if self.is_sampled:
                f.write("⚠️  NOTE: This analysis is based on a SAMPLE of the full dataset\n")
                f.write(f"Sample size: {len(self.df_valid):,} records\n\n")
            
            f.write(f"Valid Subjobs Analyzed: {len(self.df_valid):,}\n")
            f.write(f"Unique Nodes: {len(self.unique_nodes)}\n")
            f.write(f"Routing Keys: {self.unique_routing_keys}\n")
            f.write(f"Worker Counts: {self.unique_worker_counts}\n\n")
            
            # Memory usage info
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            f.write(f"Current Memory Usage: {current_memory:.1f} MB\n\n")
            
            # Performance by routing key using efficient groupby
            f.write("PERFORMANCE BY ROUTING KEY:\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'Routing Key':15} | {'Mean MB/s':10} | {'Std Dev':10} | {'Count':8} | {'Min Workers':11} | {'Max Workers':11}\n")
            f.write("-" * 70 + "\n")
            
            routing_summary = self.df_valid.groupby('routing_key').agg({
                'download_speed_sum': ['mean', 'std', 'count'],
                'worker_count': ['min', 'max']
            }).round(2)
            
            for routing_key in self.unique_routing_keys:
                if routing_key in routing_summary.index:
                    stats = routing_summary.loc[routing_key]
                    f.write(f"{routing_key:15} | {stats[('download_speed_sum', 'mean')]:10.2f} | "
                           f"{stats[('download_speed_sum', 'std')]:10.2f} | {int(stats[('download_speed_sum', 'count')]):8} | "
                           f"{int(stats[('worker_count', 'min')]):11} | {int(stats[('worker_count', 'max')]):11}\n")
            
            # Top performing configurations (limited to avoid memory issues)
            f.write("\n\nTOP PERFORMING CONFIGURATIONS (Top 20):\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'Node'[:30]:30} | {'Route':15} | {'Workers':7} | {'Avg MB/s':10} | {'Count':5}\n")
            f.write("-" * 80 + "\n")
            
            # Use efficient groupby and filtering
            config_stats = (self.df_valid
                          .groupby(['node_key', 'routing_key', 'worker_count'])
                          .agg({'download_speed_sum': ['mean', 'count']})
                          .reset_index())
            
            config_stats.columns = ['node_key', 'routing_key', 'worker_count', 'mean_throughput', 'count']
            config_stats = config_stats[config_stats['count'] >= 3]  # At least 3 measurements
            config_stats = config_stats.nlargest(20, 'mean_throughput')
            
            for _, row in config_stats.iterrows():
                node_str = str(row['node_key'])[:30]
                f.write(f"{node_str:30} | {row['routing_key']:15} | "
                       f"{row['worker_count']:7} | {row['mean_throughput']:10.2f} | {row['count']:5}\n")
            
            # Worker efficiency analysis
            f.write("\n\nWORKER COUNT SCALING ANALYSIS:\n")
            f.write("-" * 60 + "\n")
            f.write("Average throughput per worker by routing key:\n")
            f.write(f"{'Routing Key':15} | {'Efficiency (MB/s per worker)':>30}\n")
            f.write("-" * 60 + "\n")
            
            # Calculate efficiency using vectorized operations
            self.df_valid['efficiency'] = self.df_valid['download_speed_sum'] / self.df_valid['worker_count']
            efficiency_stats = self.df_valid.groupby('routing_key')['efficiency'].mean()
            
            for routing_key in self.unique_routing_keys:
                if routing_key in efficiency_stats.index:
                    f.write(f"{routing_key:15} | {efficiency_stats[routing_key]:30.2f}\n")
        
        print(f"Summary report saved to {output_file}")

def main():
    """Main function to run the consistency analysis"""
    
    print("="*60)
    print("NODE THROUGHPUT ANALYZER")
    print("="*60)
    
    # Configuration - adjust these based on your system's memory
    MAX_SAMPLE_SIZE = 50000   # None for no sampling, or set limit for large datasets
    MAX_NODES_PER_PDF = 50    # Split PDFs to avoid huge files
    ENABLE_PROGRESS = True    # Show progress and memory usage
    
    # Define paths
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    # Use the standard cleaned data file
    data_file = os.path.join(base_path, 'csv', 'node_level_cleaned_data.csv')
    
    if not os.path.exists(data_file):
        print(f"Error: Data file not found at {data_file}")
        print("Please run the data cleaner first to generate the cleaned data.")
        return
    
    print(f"Using data file: {data_file}")
    
    # Monitor initial memory
    initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
    print(f"Initial memory usage: {initial_memory:.1f}MB")
    
    try:
        # Initialize analyzer
        print("Initializing Node Throughput Analyzer...")
        analyzer = NodeThroughputAnalyzer(
            data_file=data_file,
            max_sample_size=MAX_SAMPLE_SIZE,
            max_nodes_per_pdf=MAX_NODES_PER_PDF,
            enable_progress=ENABLE_PROGRESS
        )
        
        # Prepare data
        analyzer.prepare_data()
        
        # Define output paths
        graphs_path = os.path.join(base_path, 'graphs', 'consistency')
        summary_file = os.path.join(graphs_path, 'throughput_summary.txt')
        
        # Create paginated plots
        print(f"\nGenerating paginated PDF analysis...")
        print(f"Output directory: {graphs_path}")
        pdf_files = analyzer.plot_nodes_by_routing_key_paginated(graphs_path)
        
        # Create summary report
        analyzer.create_summary_report(summary_file)
        
        # Final memory usage
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE!")
        print("="*60)
        print(f"Generated {len(pdf_files)} PDF files:")
        for pdf_file in pdf_files:
            print(f"  - {os.path.basename(pdf_file)}")
        print(f"Summary report: {os.path.basename(summary_file)}")
        print(f"Memory usage: {final_memory - initial_memory:.1f}MB (Peak: {final_memory:.1f}MB)")
        
        if analyzer.is_sampled:
            print(f"\n⚠️  Results based on sample of {len(analyzer.df_valid):,} records")
            print("For full dataset analysis, increase MAX_SAMPLE_SIZE or set to None")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()