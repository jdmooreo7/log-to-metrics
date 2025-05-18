import os
import pandas as pd
from pinecone import Pinecone, ServerlessSpec

# Initialize Pinecone
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index_name = 'log-metrics'
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=3,
        metric='euclidean',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')  # Replace with your Pinecone environment
    )

index = pc.Index(index_name)

# Load metrics
df = pd.read_csv('metrics.csv')

# Store as vectors
vectors = []
for _, row in df.iterrows():
    vector = [float(row['request_count']), float(row['error_count']), float(row['avg_latency'])]
    timestamp = str(row['timestamp'])
    vectors.append((timestamp, vector, {'timestamp': timestamp}))

# Upsert vectors
index.upsert(vectors)

print(f"Stored {len(vectors)} vectors in Pinecone")