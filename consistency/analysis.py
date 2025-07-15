import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages


df = pd.read_csv('node_job_subjob_throughput_debug.csv')
unique_nodes = df['node_id'].nunique()
print(f"Unique nodes in CSV: {unique_nodes}")
