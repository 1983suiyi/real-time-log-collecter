import os
import sys
import csv
import json
import argparse
import logging
from datetime import datetime, timedelta, timezone

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from ep_py.common import EsUtil
from ep_py.es_query_builder import ESQueryBuilder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main(start_time, end_time, env):
    """Main function to execute the script."""
    # Initialize ESQueryBuilder with the new config file
    query_builder = ESQueryBuilder('config/example/export_repeated_reason.yaml')

    runtime_params = {
        'start_time': start_time,
        'end_time': end_time
    }

    # Build the query
    query = query_builder.build_query(runtime_params=runtime_params)

    # Initialize ES_UTIL for the specified environment
    es_util = EsUtil(env=env)

    # Execute the search with batch processing
    logging.info(f"Executing query on index {query_builder.index_name} for environment {env}")
    result = es_util.search(query, index_name=query_builder.index_name)

    if result:
        logging.info(f"Successfully fetched {len(result)} records.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Export data from Elasticsearch based on a configuration.')
    parser.add_argument('--start_time', type=str, help='Start time in YYYY-MM-DD HH:MM:SS format.')
    parser.add_argument('--end_time', type=str, help='End time in YYYY-MM-DD HH:MM:SS format.')
    parser.add_argument('--days', type=int, help='Number of days to look back from now.')
    parser.add_argument('--hours', type=int, help='Number of hours to look back from now.')
    parser.add_argument('--env', type=str, default='cn', choices=['sandbox', 'production', 'cn'], help='Environment to run on.')
    args = parser.parse_args()

    start_time = args.start_time
    end_time = args.end_time

    if not start_time or not end_time:
        end_time_dt = datetime.now(timezone.utc)
        if args.hours is not None:
            start_time_dt = end_time_dt - timedelta(hours=args.hours)
        elif args.days is not None:
            start_time_dt = end_time_dt - timedelta(days=args.days)
        else:
            # Default to 1 hour if neither is specified
            start_time_dt = end_time_dt - timedelta(hours=1)
        
        start_time = start_time_dt.strftime('%Y-%m-%d %H:%M:%S')
        end_time = end_time_dt.strftime('%Y-%m-%d %H:%M:%S')

    logging.info(f"Time range: {start_time} to {end_time}")
    main(start_time, end_time, args.env)