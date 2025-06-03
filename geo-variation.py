# Group by "url". Create vertical bar graph: y-axis is download_speed, x-axis is "routing_key"
import pandas as pd
import matplotlib.pyplot as plt
import json

# Load jobs into a DataFrame
with open("job_with_subjobs.json", "r") as f:
    data = json.load(f)
f.close()
if not data:
    print("No jobs to process.")
    exit()

df = pd.json_normalize(data)

# Group by 'url' and calculate the mean download speed
df.groupby('url')

# Unfinished
