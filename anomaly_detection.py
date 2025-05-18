import os
import pandas as pd
from pinecone import Pinecone
from scipy.spatial import distance
import numpy as np

# Initialize Pinecone
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index = pc.Index('log-metrics')

# Read metrics.csv to get timestamp IDs
df = pd.read_csv('metrics.csv')
vector_ids = [str(row['timestamp']) for _, row in df.iterrows()]

# Fetch vectors
response = index.fetch(vector_ids)
vectors = [(k, v['values']) for k, v in response.vectors.items() if v is not None]

# Calculate mean and standard deviation
if not vectors:
    print("No vectors found in Pinecone")
else:
    values = [v for _, v in vectors]
    mean = np.mean(values, axis=0)
    std = np.std(values, axis=0)

    # Detect anomalies (vectors > 2 standard deviations from mean)
    for timestamp, vector in vectors:
        dist = distance.euclidean(vector, mean)
        if dist > 2 * np.mean(std):
            print(f"Anomaly detected at {timestamp}: {vector}")
        else:
            print(f"No anomaly at {timestamp}: {vector}")