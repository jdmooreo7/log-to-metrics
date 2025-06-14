# This script parses a log file and aggregates metrics (request count, error count, average latency)
# into 5-minute windows, then outputs the results as a CSV file.
import json
import pandas as pd
from collections import defaultdict

# Parses the log file and aggregates metrics by 5-minute time windows
def parse_logs(log_file):
    # Initialize a dictionary to store metrics for each time window
    metrics = defaultdict(lambda: {'request_count': 0, 'error_count': 0, 'total_latency': 0})
    with open(log_file, 'r') as f:
        for line in f:
            try:
                log = json.loads(line.strip())  # Parse each log line as JSON
                # Skip logs without responseTime (e.g., server startup log)
                if 'responseTime' not in log:
                    continue
                # Round timestamp down to the nearest 5 minutes for aggregation
                timestamp = pd.to_datetime(log['timestamp']).floor('5min')
                # Increment error count if log level is 'error'
                if log['level'] == 'error':
                    metrics[timestamp]['error_count'] += 1
                # Increment request count and add to total latency
                metrics[timestamp]['request_count'] += 1
                metrics[timestamp]['total_latency'] += log['responseTime']
            except json.JSONDecodeError:
                continue  # Skip lines that are not valid JSON
    # Build a list of metrics for each time window
    return [
        {
            'timestamp': ts,
            'request_count': data['request_count'],
            'error_count': data['error_count'],
            'avg_latency': data['total_latency'] / data['request_count'] if data['request_count'] > 0 else 0
        }
        for ts, data in metrics.items()
    ]

if __name__ == '__main__':
    # Parse the log file and generate metrics
    metrics = parse_logs('app.log')
    # Convert metrics to a DataFrame and save as CSV
    df = pd.DataFrame(metrics)
    df.to_csv('metrics.csv')
    print(df)