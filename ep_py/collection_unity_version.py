import argparse
import pandas as pd
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_data(input_file, output_file, env):
    """
    Processes the raw data from the input file and saves the aggregated data to the output file.
    """
    try:
        # Read data using column names from the source_fields in the config
        df = pd.read_csv(input_file)
        logging.info(f"Successfully loaded {len(df)} records from {input_file}")
    except FileNotFoundError:
        logging.error(f"Error: Input file not found at {input_file}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error reading input file: {e}")
        sys.exit(1)

    if df.empty:
        logging.warning("Input file is empty. Nothing to process.")
        return

    # Data processing logic from the original script
    df['timestamp'] = pd.to_datetime(df['@timestamp'])
    df['serverTime'] = pd.to_datetime(df['serverTime'], unit='ms')
    df['游戏别名'] = df['carrier'].apply(lambda x: "SDK-Demo" if pd.isna(x) or x == '' else (f"{str(x)}-Global" if 'CN' not in str(x) else str(x)))
    df = df.sort_values(by='timestamp', ascending=True)

    group_keys = ['gameserverId', '游戏别名', 'sdkVersion', 'environment']
    
    result_df = df.groupby(group_keys).agg(
        unity_versions=('appVersion', lambda x: ", ".join(x.unique())),
        latest_unity_version=('appVersion', 'last'),
        latest_server_time=('serverTime', 'last')
    ).reset_index()

    result_df['latest_server_time'] = result_df['latest_server_time'].dt.strftime('%Y-%m-%d %H:%M:%S')

    result_df = result_df.rename(columns={
        'gameserverId': 'GameID',
        'sdkVersion': 'SDK 版本',
        'unity_versions': 'Unity 版本',
        'latest_unity_version': '最近使用的 Unity 版本',
        'latest_server_time': '最近运行时间'
    })
    
    # Select and reorder columns
    final_df = result_df[['GameID', '游戏别名', 'SDK 版本', 'Unity 版本', '最近使用的 Unity 版本', '最近运行时间', 'environment']]

    # Filter by environment if provided
    if env:
        logging.info(f"Filtering data for environment: {env}")
        final_df = final_df[final_df['environment'] == env]

    if final_df.empty:
        logging.warning("No data to save after processing and filtering.")
        # Create an empty file with headers to signify completion
        pd.DataFrame(columns=['GameID', '游戏别名', 'SDK 版本', 'Unity 版本', '最近使用的 Unity 版本', '最近运行时间']).to_csv(output_file, index=False)
        return

    # Save to output file
    try:
        final_df.drop(columns=['environment']).to_csv(output_file, index=False)
        logging.info(f"Processed data successfully saved to {output_file}")
    except Exception as e:
        logging.error(f"Error writing to output file: {e}")
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Post-process Unity Version data.')
    parser.add_argument('--input', required=True, help='Path to the raw CSV data file.')
    parser.add_argument('--output', required=True, help='Path to save the processed CSV file.')
    parser.add_argument('--env', type=str, choices=['sandbox', 'production'], help='Environment to filter on.')
    args = parser.parse_args()

    process_data(args.input, args.output, args.env)