import json
import time
import pandas as pd
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timedelta
from pinecone import Pinecone, ServerlessSpec

# Initialize Pinecone
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index_name = 'log-metrics'
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=3,
        metric='euclidean',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')  # Replace with your environment
    )
index = pc.Index(index_name)

# Metrics storage
metrics = []
current_window = None
window_duration = 10  # seconds

class LogFileHandler(FileSystemEventHandler):
    def __init__(self, log_file):
        self.log_file = log_file
        self.last_position = 0
        self.process_existing_logs()

    def process_existing_logs(self):
        """Process existing logs up to current position."""
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                f.seek(0, os.SEEK_END)
                self.last_position = f.tell()

    def on_modified(self, event):
        if event.src_path == self.log_file:
            self.process_new_logs()

    def process_new_logs(self):
        global current_window, metrics
        with open(self.log_file, 'r') as f:
            f.seek(self.last_position)
            new_lines = f.readlines()
            self.last_position = f.tell()

            for line in new_lines:
                try:
                    log = json.loads(line.strip())
                    timestamp = datetime.strptime(log['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    status = log['status']
                    response_time = log['responseTime']

                    # Round timestamp to nearest 10-second window
                    window_start = timestamp - timedelta(seconds=timestamp.second % window_duration, microseconds=timestamp.microsecond)
                    window_str = window_start.strftime('%Y-%m-%d %H:%M:%S')

                    if current_window != window_str:
                        if current_window:
                            # Save previous window's metrics
                            save_metrics()
                        current_window = window_str
                        metrics = []

                    metrics.append({
                        'timestamp': window_str,
                        'status': status,
                        'response_time': response_time
                    })
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"Error processing log: {e}")

def save_metrics():
    if not metrics:
        return

    df = pd.DataFrame(metrics)
    grouped = df.groupby('timestamp').agg(
        request_count=('status', 'count'),
        error_count=('status', lambda x: sum(1 for s in x if s >= 400)),
        avg_latency=('response_time', 'mean')
    ).reset_index()

    # Append to metrics.csv
    if os.path.exists('metrics.csv'):
        grouped.to_csv('metrics.csv', mode='a', header=False, index=False)
    else:
        grouped.to_csv('metrics.csv', index=False)

    # Upsert to Pinecone
    vectors = []
    for _, row in grouped.iterrows():
        vector = [float(row['request_count']), float(row['error_count']), float(row['avg_latency'])]
        timestamp = str(row['timestamp'])
        vectors.append((timestamp, vector, {'timestamp': timestamp}))
    if vectors:
        index.upsert(vectors)
        print(f"Stored {len(vectors)} vectors in Pinecone")

if __name__ == '__main__':
    log_file = 'app.log'
    event_handler = LogFileHandler(log_file)
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    print(f"Monitoring {log_file} for changes...")
    try:
        while True:
            time.sleep(1)
            # Periodically save metrics to ensure last window is captured
            if metrics:
                save_metrics()
    except KeyboardInterrupt:
        observer.stop()
        save_metrics()
        print("Stopped monitoring")
    observer.join()