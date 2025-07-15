
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

# Load the CSV file
df = pd.read_csv('Users/zoezhao/Columbia/25Summer/fc-bms-research/consistency/node_job_subjob_throughput_debug.csv')

# Filter rows with non-null worker_count and throughput
df_clean = df.dropna(subset=['worker_count', 'subjob_throughput'])

# Convert worker_count to int and then to labeled string for plotting
df_clean['worker_count'] = df_clean['worker_count'].astype(int)
df_clean['worker_count_label'] = df_clean['worker_count'].astype(str) + ' workers'

# Define preferred worker count order (adjust if needed)
preferred_order = ['1 workers', '8 workers', '10 workers']
others = [w for w in df_clean['worker_count_label'].unique() if w not in preferred_order]
order = preferred_order + sorted(others, key=lambda x: int(x.split()[0]))

pdf_path = 'storage_nodes_bandwidth_plots_with_points.pdf'
with PdfPages(pdf_path) as pdf:
    for node in df_clean['node_id'].unique():
        node_data = df_clean[df_clean['node_id'] == node]

        plt.figure(figsize=(12, 7))

        # Boxplot showing distribution by worker count
        sns.boxplot(data=node_data, x='worker_count_label', y='subjob_throughput', order=order)

        # Overlay individual data points with jitter for clarity
        sns.stripplot(data=node_data, x='worker_count_label', y='subjob_throughput',
                      order=order, color='black', size=5, jitter=True, alpha=0.7)

        # Titles and labels
        plt.title(f'Bandwidth Distribution by Worker Count\nStorage Node: {node}')
        plt.xlabel('Worker Count')
        plt.ylabel('Subjob Throughput (Bytes/sec)')
        plt.grid(True)

        # Annotate number of samples for each worker count category
        counts = node_data.groupby('worker_count_label').size()
        for i, label in enumerate(order):
            count = counts.get(label, 0)
            plt.text(i, plt.ylim()[1] * 0.95, f'n={count}', ha='center', fontsize=10, color='red')

        plt.tight_layout()
        pdf.savefig()
        plt.close()

print(f"All annotated plots saved to {pdf_path}")

