import json
import time
import pandas as pd
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timedelta
from pinecone import Pinecone, ServerlessSpec

# Initialize Pinecone
try:
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    index_name = 'log-metrics'
    if index_name not in pc.list_indexes().names():
        print(f"Creating Pinecone index {index_name}...")
        pc.create_index(
            name=index_name,
            dimension=3,
            metric='euclidean',
            spec=ServerlessSpec(cloud='aws', region='us-east-1')  # Replace with your environment
        )
    index = pc.Index(index_name)
    print("Pinecone initialized successfully")
except Exception as e:
    print(f"Pinecone initialization failed: {e}")
    exit(1)

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
            print(f"Set initial position for {self.log_file} to {self.last_position}")

    def on_modified(self, event):
        print(f"File modified: {event.src_path}")
        if event.src_path == self.log_file:
            print("Processing new logs...")
            self.process_new_logs()

    def process_new_logs(self):
        global current_window, metrics
        try:
            with open(self.log_file, 'r') as f:
                f.seek(self.last_position)
                new_lines = f.readlines()
                self.last_position = f.tell()
                print(f"Read {len(new_lines)} new lines")

                for line in new_lines:
                    print(f"Processing line: {line.strip()}")
                    try:
                        log = json.loads(line.strip())
                        timestamp = datetime.strptime(log['timestamp'], '%Y-%m-%dT%H:%M:%S.%fZ')
                        status = log['status']
                        response_time = log['responseTime']
                        print(f"Parsed log: timestamp={timestamp}, status={status}, responseTime={response_time}")

                        # Round timestamp to nearest 10-second window
                        window_start = timestamp - timedelta(seconds=timestamp.second % window_duration, microseconds=timestamp.microsecond)
                        window_str = window_start.strftime('%Y-%m-%d %H:%M:%S')

                        if current_window != window_str:
                            if current_window:
                                # Save previous window's metrics
                                save_metrics()
                            current_window = window_str
                            metrics = []
                            print(f"New window: {window_str}")

                        metrics.append({
                            'timestamp': window_str,
                            'status': status,
                            'response_time': response_time
                        })
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        print(f"Error processing log: {e}")
        except Exception as e:
            print(f"Error reading file: {e}")

def save_metrics():
    global metrics
    if not metrics:
        print("No metrics to save")
        return

    print(f"Saving {len(metrics)} metrics")
    df = pd.DataFrame(metrics)
    grouped = df.groupby('timestamp').agg(
        request_count=('status', 'count'),
        error_count=('status', lambda x: sum(1 for s in x if s >= 400)),
        avg_latency=('response_time', 'mean')
    ).reset_index()

    # Append to metrics.csv
    try:
        if os.path.exists('metrics.csv'):
            grouped.to_csv('metrics.csv', mode='a', header=False, index=False)
        else:
            grouped.to_csv('metrics.csv', index=False)
        print("Updated metrics.csv")
    except Exception as e:
        print(f"Error writing to metrics.csv: {e}")

    # Upsert to Pinecone
    vectors = []
    for _, row in grouped.iterrows():
        vector = [float(row['request_count']), float(row['error_count']), float(row['avg_latency'])]
        timestamp = str(row['timestamp'])
        vectors.append((timestamp, vector, {'timestamp': timestamp}))
    if vectors:
        try:
            index.upsert(vectors)
            print(f"Stored {len(vectors)} vectors in Pinecone")
        except Exception as e:
            print(f"Pinecone upsert failed: {e}")
    metrics = []  # Clear metrics after saving

if __name__ == '__main__':
    log_file = 'app.log'
    print(f"Starting to monitor {log_file} in {os.getcwd()}")
    if not os.path.exists(log_file):
        print(f"Warning: {log_file} does not exist, creating empty file")
        open(log_file, 'a').close()
    event_handler = LogFileHandler(log_file)
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    print(f"Monitoring {log_file} for changes...")
    try:
        while True:
            time.sleep(1)
            if metrics:
                print(f"Pending metrics: {len(metrics)}")
                save_metrics()
    except KeyboardInterrupt:
        print("Stopping observer...")
        observer.stop()
        save_metrics()
        print("Stopped monitoring")
    observer.join()