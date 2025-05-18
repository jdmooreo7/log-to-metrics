import json
import pandas as pd
from collections import defaultdict

def parse_logs(log_file):
    metrics = defaultdict(lambda: {'request_count': 0, 'error_count': 0, 'total_latency': 0})
    with open(log_file, 'r') as f:
        for line in f:
            try:
                log = json.loads(line.strip())
                # Skip logs without responseTime (e.g., server startup log)
                if 'responseTime' not in log:
                    continue
                timestamp = pd.to_datetime(log['timestamp']).floor('5min')  # Aggregate by 5-minute windows
                if log['level'] == 'error':
                    metrics[timestamp]['error_count'] += 1
                metrics[timestamp]['request_count'] += 1
                metrics[timestamp]['total_latency'] += log['responseTime']
            except json.JSONDecodeError:
                continue
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
    metrics = parse_logs('app.log')
    df = pd.DataFrame(metrics)
    df.to_csv('metrics.csv')
    print(df)