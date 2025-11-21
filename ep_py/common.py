import json
import logging
import os
import re
import subprocess
import urllib.parse
from collections import defaultdict, Counter
from datetime import datetime

import boto3
import pandas as pd
import pytz
import yaml

from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from tabulate import tabulate
from tqdm import tqdm



class Processor:
    def process(self, data):
        raise NotImplementedError

class CustomScriptProcessor(Processor):
    def __init__(self, script_path, args):
        self.script_path = script_path
        self.args = args

    def process(self, data):
        # This processor runs after all data is written, so it doesn't process batches.
        # The logic is handled in the main script.
        pass

    def run_script(self):
        command = ['python', self.script_path] + self.args
        logging.info(f"Executing custom script: {' '.join(command)}")
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            logging.info(f"Script output:\n{result.stdout}")
            if result.stderr:
                logging.warning(f"Script errors:\n{result.stderr}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Custom script failed with exit code {e.returncode}")
            logging.error(f"Stdout: {e.stdout}")
            logging.error(f"Stderr: {e.stderr}")
            raise
        except FileNotFoundError:
            logging.error(f"Custom script not found at: {self.script_path}")
            raise

class RegexFilterProcessor(Processor):
    def __init__(self, field, pattern):
        self.field = field
        self.pattern = re.compile(pattern)

    def process(self, data):
        filtered_data = []
        for item in data:
            source = item.get('_source', {})
            field_value = source.get(self.field)
            if field_value and self.pattern.search(str(field_value)):
                filtered_data.append(item)
        return filtered_data

class DeduplicateProcessor(Processor):
    def __init__(self, fields):
        self.fields = fields
        self.seen_combinations = set()

    def process(self, data):
        deduplicated_data = []
        for item in data:
            # 从 _source 中提取数据
            source = item.get('_source', {})
            # 构建用于去重的组合键
            combination = tuple(source.get(field) for field in self.fields)
            if combination not in self.seen_combinations:
                self.seen_combinations.add(combination)
                deduplicated_data.append(item)
        return deduplicated_data

class TimestampConverterProcessor(Processor):
    def __init__(self, field, unit='s', timezone='UTC'):
        self.field = field
        self.unit = unit
        self.timezone = timezone

    def process(self, data):
        from datetime import datetime, timezone as dt_timezone

        try:
            tz = pytz.timezone(self.timezone)
        except pytz.UnknownTimeZoneError:
            logging.error(f"Unknown timezone: {self.timezone}. Falling back to UTC.")
            tz = dt_timezone.utc

        for item in data:
            source = item.get('_source', {})
            if self.field in source:
                timestamp = source[self.field]
                try:
                    # Convert to float, as timestamp can be int or float
                    timestamp = float(timestamp)
                    if self.unit == 'ms':
                        timestamp /= 1000
                    
                    # Create a timezone-aware datetime object
                    dt_object = datetime.fromtimestamp(timestamp, tz)
                    source[self.field] = dt_object.isoformat()

                except (ValueError, TypeError) as e:
                    logging.warning(f"Could not convert timestamp for field '{self.field}' with value '{timestamp}': {e}")
        return data

class URLDecodeProcessor(Processor):
    def __init__(self, fields):
        # 支持传入字符串（单个字段）或列表（多个字段）
        if isinstance(fields, str):
            self.fields = [fields]
        elif isinstance(fields, list):
            self.fields = fields
        else:
            raise ValueError("fields parameter must be a string or list of strings")

    def process(self, data):
        for item in data:
            source = item.get('_source', {})
            for field in self.fields:
                if field in source:
                    field_value = source[field]
                    if field_value:
                        try:
                            # 对字段值进行URL解码
                            decoded_value = urllib.parse.unquote(str(field_value))
                            source[field] = decoded_value
                        except Exception as e:
                            logging.warning(f"Could not URL decode field '{field}' with value '{field_value}': {e}")
        return data


class KvParser(Processor):
    def __init__(self, field, pair_delimiter=',', kv_delimiter='='):
        self.field = field
        self.pair_delimiter = pair_delimiter
        self.kv_delimiter = kv_delimiter

    def process(self, data):
        for item in data:
            source = item.get('_source', {})
            if self.field in source:
                kv_string = source.get(self.field)
                if kv_string:
                    try:
                        pairs = kv_string.split(self.pair_delimiter)
                        for pair in pairs:
                            if self.kv_delimiter in pair:
                                key, value = pair.split(self.kv_delimiter, 1)
                                source[key.strip()] = value.strip()
                    except Exception as e:
                        logging.warning(f"Could not parse key-value string for field '{self.field}' with value '{kv_string}': {e}")
        return data


class GrokParser(Processor):
    def __init__(self, field, pattern):
        self.field = field
        self.pattern = pattern
        try:
            from pygrok import Grok
            self.grok = Grok(pattern)
        except ImportError:
            logging.error("pygrok is not installed. Please install it with \"pip install pygrok\"")
            self.grok = None

    def process(self, data):
        if not self.grok:
            return data
        for item in data:
            source = item.get('_source', {})
            if self.field in source:
                log_entry = source.get(self.field)
                if log_entry:
                    try:
                        match = self.grok.match(log_entry)
                        if match:
                            source.update(match)
                    except Exception as e:
                        logging.warning(f"Grok parsing failed for field '{self.field}' with value '{log_entry}': {e}")
        return data


class TypeConverter(Processor):
    def __init__(self, fields):
        self.fields = fields

    def process(self, data):
        for item in data:
            source = item.get('_source', {})
            for field_config in self.fields:
                field_name = field_config.get('name')
                target_type = field_config.get('type')
                if field_name in source:
                    value = source[field_name]
                    try:
                        if target_type == 'integer':
                            source[field_name] = int(value)
                        elif target_type == 'float':
                            source[field_name] = float(value)
                        elif target_type == 'boolean':
                            source[field_name] = str(value).lower() in ['true', '1', 't', 'y', 'yes']
                    except (ValueError, TypeError) as e:
                        logging.warning(f"Could not convert field '{field_name}' with value '{value}' to type '{target_type}': {e}")
        return data


class DatetimeParser(Processor):
    def __init__(self, field, formats, output_format='%Y-%m-%dT%H:%M:%S.%f%z', timezone=None):
        self.field = field
        self.formats = formats
        self.output_format = output_format
        self.timezone = timezone

    def process(self, data):
        import dateutil.parser
        import pytz

        for item in data:
            source = item.get('_source', {})
            if self.field in source:
                date_str = source[self.field]
                if not date_str:
                    continue

                parsed_date = None
                for fmt in self.formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue

                if not parsed_date:
                    try:
                        parsed_date = dateutil.parser.parse(date_str)
                    except dateutil.parser._parser.ParserError:
                        logging.warning(f"Could not parse date string: {date_str}")
                        continue

                if self.timezone:
                    tz = pytz.timezone(self.timezone)
                    if parsed_date.tzinfo is None:
                        parsed_date = tz.localize(parsed_date)
                    else:
                        parsed_date = parsed_date.astimezone(tz)

                if self.output_format == 'epoch_millis':
                    source[self.field] = int(parsed_date.timestamp() * 1000)
                else:
                    source[self.field] = parsed_date.strftime(self.output_format)
        return data


class FieldMerger(Processor):
    def __init__(self, source_fields, target_field, separator=' '):
        self.source_fields = source_fields
        self.target_field = target_field
        self.separator = separator

    def process(self, data):
        for item in data:
            source = item.get('_source', {})
            merged_value = []
            for field in self.source_fields:
                if field in source:
                    merged_value.append(str(source[field]))
            if merged_value:
                source[self.target_field] = self.separator.join(merged_value)
        return data


class LookupEnricher(Processor):
    def __init__(self, field, target_field, dictionary=None, file_path=None):
        self.field = field
        self.target_field = target_field
        self.lookup_table = {}

        if dictionary:
            self.lookup_table = dictionary
        elif file_path:
            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        parts = line.strip().split(':', 1)
                        if len(parts) == 2:
                            self.lookup_table[parts[0].strip()] = parts[1].strip()
            except FileNotFoundError:
                logging.error(f"Lookup file not found: {file_path}")
            except Exception as e:
                logging.error(f"Error reading lookup file {file_path}: {e}")
        else:
            logging.error("LookupEnricher requires either a 'dictionary' or a 'file_path'")

    def process(self, data):
        for item in data:
            source = item.get('_source', {})
            if self.field in source:
                lookup_value = source.get(self.field)
                if lookup_value in self.lookup_table:
                    source[self.target_field] = self.lookup_table[lookup_value]
        return data









class JsonToCsvProcessor(Processor):
    def __init__(self, field, output_path_template, ctx, task_config=None, pre_process_pattern=None):
        self.field = field
        self.output_path_template = output_path_template
        self.ctx = ctx
        self.task_config = task_config or {}
        self.pre_process_pattern = pre_process_pattern if pre_process_pattern is not None else '({.*})'
        self.data_to_write = []
        self.output_path = self._get_output_path()

    def _get_output_path(self):
        # A simplified version of get_output_path from generic_exporter.py
        template_vars = self.ctx.params.copy()
        template_vars['query_name'] = self.task_config.get('query_name', 'export')
        template_vars['date'] = datetime.now().strftime('%Y%m%d')
        template_vars['time'] = datetime.now().strftime('%H%M%S')

        processed_path = self.output_path_template
        for key, value in template_vars.items():
            if value is not None:
                processed_path = processed_path.replace(f'{{{{{key}}}}}', str(value))

        if not any(processed_path.endswith(ext) for ext in ['.csv', '.jsonl']):
            processed_path = f"{processed_path}.csv"

        if not os.path.isabs(processed_path):
            # Correctly determine the project root relative to the current file's location
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # Place the data folder inside the project root
            processed_path = os.path.join(project_root, 'data', os.path.basename(processed_path))

        # Ensure the directory exists
        os.makedirs(os.path.dirname(processed_path), exist_ok=True)

        return processed_path

    def flatten_json_dict(self, json_dict):
        processed_data = {}
        for key, value in json_dict.items():
            if isinstance(value, str):
                try:
                    nested_json = json.loads(value)
                    if isinstance(nested_json, dict):
                        # it's a nested json object, flatten it by merging
                        processed_data.update(nested_json)
                    else:
                        # it's a json literal, not an object to flatten
                        processed_data[key] = nested_json
                except (json.JSONDecodeError, TypeError):
                    # not a valid json string, keep original value
                    processed_data[key] = value
            else:
                processed_data[key] = value
        return processed_data

    def process(self, data):
        for item in data:
            source = item.get('_source', {})
            raw_value = source.get(self.field)

            if not raw_value:
                continue

            text = str(raw_value)
            json_data = None
            str_to_parse = text  # Default to the whole text

            # 1. If a pattern is defined, try to extract a substring
            if self.pre_process_pattern:
                match = re.search(self.pre_process_pattern, text, re.DOTALL)
                if match:
                    str_to_parse = match.group(1) if match.groups() else match.group(0)
                else:
                    # If pattern doesn't match, we still use the whole 'text' as str_to_parse
                    logging.debug(f"Pattern '{self.pre_process_pattern}' did not match in field '{self.field}'. Will attempt to parse the whole field.")

            # 2. Try to parse the determined string (either extracted or the whole field)
            try:
                json_data = json.loads(str_to_parse)
            except json.JSONDecodeError:
                # If that fails, try wrapping it in braces
                try:
                    json_data = json.loads(f"{{{str_to_parse}}}")
                except json.JSONDecodeError:
                    # If both attempts fail, json_data remains None
                    pass

            # 3. If we have data, process it
            if json_data:
                if isinstance(json_data, list):
                    processed_list = []
                    for list_item in json_data:
                        if isinstance(list_item, dict):
                            processed_list.append(self.flatten_json_dict(list_item))
                        else:
                            processed_list.append(list_item)
                    self.data_to_write.extend(processed_list)
                elif isinstance(json_data, dict):
                    self.data_to_write.append(self.flatten_json_dict(json_data))
            else:
                logging.warning(f"Could not extract/decode JSON from field '{self.field}' with value '{raw_value}'")

        return data

    def close(self):
        if not self.data_to_write:
            logging.info("No data to write to CSV from JsonToCsvProcessor.")
            return

        # Convert to DataFrame and save as CSV
        df = pd.DataFrame(self.data_to_write)
        df.to_csv(self.output_path, index=False, encoding='utf-8')
        logging.info(f"JsonToCsvProcessor successfully wrote data to {self.output_path}")



class StatsCollectorProcessor(Processor):
    """
    通用统计收集器：支持多种字段组合的统计分析
    """
    def __init__(self, stats_configs=None, output_stats=True):
        """
        初始化统计收集器
        
        Args:
            stats_configs: 统计配置列表，每个配置包含：
                - name: 统计名称
                - fields: 要统计的字段列表
                - description: 统计描述（可选）
            output_stats: 是否输出统计结果
        """
        # 兼容旧版本参数
        if stats_configs is None:
            # 如果没有提供配置，使用默认配置
            stats_configs = [{
                'name': 'service_error_stats',
                'fields': ['httpServiceName', 'errorCode'],
                'description': 'httpServiceName与errorCode联合统计'
            }]
        elif isinstance(stats_configs, dict):
            # 如果是单个配置，转换为列表
            stats_configs = [stats_configs]
        
        self.stats_configs = stats_configs
        self.output_stats = output_stats
        self.total_records = 0
        
        # 为每个统计配置初始化计数器
        self.stats_data = {}
        for config in self.stats_configs:
            config_name = config['name']
            self.stats_data[config_name] = {
                'config': config,
                'combined_counter': Counter(),
                'field_counters': {field: Counter() for field in config['fields']},
                'valid_records': 0
            }
    
    def process(self, data):
        """
        处理数据批次，收集统计信息
        """
        for item in data:
            source = item.get('_source', {})
            self.total_records += 1
            
            # 为每个统计配置处理数据
            for config_name, stats_info in self.stats_data.items():
                config = stats_info['config']
                fields = config['fields']
                
                # 获取所有字段的值
                field_values = []
                all_fields_present = True
                
                for field in fields:
                    value = source.get(field)
                    if value is None:
                        all_fields_present = False
                        break
                    field_values.append(str(value))
                
                # 只统计所有字段都不为空的记录
                if all_fields_present:
                    stats_info['valid_records'] += 1
                    
                    # 联合统计（使用|分隔符连接所有字段值）
                    combined_key = '|'.join(field_values)
                    stats_info['combined_counter'][combined_key] += 1
                    
                    # 单独统计每个字段
                    for i, field in enumerate(fields):
                        stats_info['field_counters'][field][field_values[i]] += 1
        
        return data
    
    def get_stats_summary(self):
        """
        获取统计摘要
        """
        summary = {
            'total_records': self.total_records,
            'stats_configs': []
        }
        
        for config_name, stats_info in self.stats_data.items():
            config = stats_info['config']
            config_summary = {
                'name': config_name,
                'description': config.get('description', config_name),
                'fields': config['fields'],
                'valid_records': stats_info['valid_records'],
                'unique_combinations': len(stats_info['combined_counter']),
                'field_unique_counts': {}
            }
            
            # 计算每个字段的唯一值数量
            for field, counter in stats_info['field_counters'].items():
                config_summary['field_unique_counts'][field] = len(counter)
            
            summary['stats_configs'].append(config_summary)
        
        return summary
    
    def print_stats(self):
        """
        打印统计结果
        """
        if not self.output_stats:
            return
            
        print("\n" + "="*80)
        print("📊 数据统计分析结果")
        print("="*80)
        
        # 总体汇总信息
        summary = self.get_stats_summary()
        print("\n📋 总体汇总信息:")
        summary_data = [["总记录数", summary['total_records']]]
        print(tabulate(summary_data, headers=['指标', '数值'], tablefmt='grid'))
        
        # 为每个统计配置显示详细结果
        for config_summary in summary['stats_configs']:
            config_name = config_summary['name']
            description = config_summary['description']
            fields = config_summary['fields']
            
            print(f"\n{'='*60}")
            print(f"📈 {description} ({config_name})")
            print(f"{'='*60}")
            
            # 配置详细信息
            config_data = [
                ["统计字段", ", ".join(fields)],
                ["有效记录数", config_summary['valid_records']],
                ["唯一组合数量", config_summary['unique_combinations']]
            ]
            
            # 添加每个字段的唯一值数量
            for field, count in config_summary['field_unique_counts'].items():
                config_data.append([f"唯一{field}数量", count])
            
            print(tabulate(config_data, headers=['指标', '数值'], tablefmt='grid'))
            
            # 获取对应的统计数据
            stats_info = self.stats_data[config_name]
            
            # 联合统计（前20个）
            if stats_info['combined_counter']:
                print(f"\n📊 {description}联合统计 (前20个):")
                combined_data = []
                for combined_key, count in stats_info['combined_counter'].most_common(20):
                    field_values = combined_key.split('|')
                    row = field_values + [count]
                    combined_data.append(row)
                
                headers = fields + ['Count']
                print(tabulate(combined_data, headers=headers, tablefmt='grid', stralign='left'))
            
            # 单个字段统计（前10个）
            for field in fields:
                field_counter = stats_info['field_counters'][field]
                if field_counter:
                    print(f"\n📈 {field}统计 (前10个):")
                    field_data = [[value, count] for value, count in field_counter.most_common(10)]
                    print(tabulate(field_data, headers=[field, 'Count'], 
                                  tablefmt='grid', stralign='left'))
    
    def save_stats_to_file(self, output_dir):
        """
        保存统计结果到文件
        """
        saved_files = []
        
        for config_name, stats_info in self.stats_data.items():
            config = stats_info['config']
            combined_counter = stats_info['combined_counter']
            
            if not combined_counter:
                continue
                
            # 准备数据
            combined_data = []
            fields = config['fields']
            
            for combined_key, count in combined_counter.most_common():
                field_values = combined_key.split('|')
                row_data = {}
                
                # 为每个字段创建列
                for i, field in enumerate(fields):
                    row_data[field] = field_values[i] if i < len(field_values) else ''
                
                row_data['count'] = count
                combined_data.append(row_data)
            
            # 保存到CSV
            if combined_data:
                df = pd.DataFrame(combined_data)
                stats_file = os.path.join(output_dir, f'{config_name}_stats.csv')
                df.to_csv(stats_file, index=False, encoding='utf-8')
                
                logging.info(f"统计结果已保存到: {stats_file}")
                saved_files.append(stats_file)
        
        return saved_files if saved_files else None

class EsUtil:

    def __init__(self, env='default', service='es', config_path=None):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

        if config_path:
            if not os.path.isabs(config_path):
                config_path = os.path.join(project_root, config_path)
        else:
            # 默认在config目录下寻找local_config.yaml或local_config_cn.yaml
            default_cn_config = os.path.join(project_root, 'config', 'local_config_cn.yaml')
            default_config = os.path.join(project_root, 'config', 'local_config.yaml')
            if env and 'cn' in env and os.path.exists(default_cn_config):
                config_path = default_cn_config
            else:
                config_path = default_config

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found at {config_path}")

        logging.info(f"Loading configuration from: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            local_config = yaml.safe_load(f)

        # Load credentials securely
        # Priority: 1. Environment Variables -> 2. Config File -> 3. Boto3 Session
        access_key = os.environ.get('AWS_ACCESS_KEY_ID')
        secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        session_token = os.environ.get('AWS_SESSION_TOKEN')

        if all([access_key, secret_key, session_token]):
            logging.info("Using credentials from environment variables.")
        else:
            logging.info("Credentials not found in environment variables, trying config file.")
            credentials = local_config.get('aws_credentials', {})
            access_key = credentials.get('access_key_id')
            secret_key = credentials.get('secret_access_key')
            session_token = credentials.get('session_token')
            if all([access_key, secret_key, session_token]):
                logging.info("Using credentials from config file.")

        # If credentials are not in the config, try to get them from boto3
        if not all([access_key, secret_key, session_token]):
            logging.info("Credentials not found in config file, trying boto3 session.")
            try:
                # If a session token was partially provided, ensure it's used.
                session_kwargs = {}
                if session_token:
                    session_kwargs['aws_session_token'] = session_token
                
                boto_session = boto3.Session(
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    **session_kwargs
                )
                boto_credentials = boto_session.get_credentials()
                access_key = boto_credentials.access_key
                secret_key = boto_credentials.secret_key
                session_token = boto_credentials.token
                logging.info("Using credentials from boto3 session.")
            except Exception as e:
                logging.warning(f"Could not retrieve credentials from boto3 session: {e}")

        if not all([access_key, secret_key]):
            raise ValueError("AWS credentials not found in config or boto3 session.")

        # Load ES config for the specified environment
        es_configs = local_config.get('es_config', {})
        env_config = es_configs.get(env)

        if not env_config:
            raise ValueError(f"ES configuration for environment '{env}' not found in {config_path}")

        host = env_config.get('host')
        region = env_config.get('region')

        if not all([host, region]):
            raise ValueError(f"'host' and 'region' must be defined for environment '{env}' in {config_path}")

        self.host = host
        self.region = region
        self.search_count = env_config.get('search.max_open_scroll_context', 1000)
        self.awsauth = AWS4Auth(access_key, secret_key, region, service, session_token=session_token)

        from botocore.config import Config

        self.search_client = OpenSearch(
            hosts=[{'host': self.host, 'port': 443}],
            http_auth=self.awsauth,
            use_ssl=True,
            verify_certs=True,
            http_compress=True,
            connection_class=RequestsHttpConnection,
            timeout=30,
            client_config=Config(connect_timeout=60, read_timeout=60)
        )

    def search(self, query, index_name, process_batch=None):
        try:
            search_result = self.search_client.search(index=index_name, body=query, scroll='1m', size=self.search_count, request_timeout=60)
        except Exception as e:
            logging.error(f"Error executing ES search: {e}")
            logging.error(f"Failed query: {json.dumps(query, indent=2)}")
            return {}

        scroll_id = search_result.get('_scroll_id')
        total_hits = search_result.get('hits', {}).get('total', {}).get('value', 0)

        aggregations = search_result.get('aggregations')
        all_hits = []

        def process_and_collect(hits):
            if process_batch:
                process_batch(hits)
            else:
                all_hits.extend(hits)

        # Process the first batch
        with tqdm(total=total_hits, desc="Downloading", unit="docs") as pbar:
            first_batch = search_result.get('hits', {}).get('hits', [])
            process_and_collect(first_batch)
            pbar.update(len(first_batch))

            # Start scrolling if there's a scroll_id
            if scroll_id:
                try:
                    while True:
                        scroll_result = self.search_client.scroll(scroll_id=scroll_id, scroll='1m', request_timeout=60)
                        scroll_id = scroll_result.get('_scroll_id')
                        hits_in_batch = scroll_result.get('hits', {}).get('hits', [])
                        
                        if not hits_in_batch:
                            break
                        
                        process_and_collect(hits_in_batch)
                        pbar.update(len(hits_in_batch))

                        if not scroll_id:
                            break
                except Exception as e:
                    logging.error(f"Error during scroll: {e}")
                finally:
                    if scroll_id:
                        try:
                            self.search_client.clear_scroll(scroll_id=scroll_id)
                            logging.debug(f"Cleared scroll context: {scroll_id}")
                        except Exception as e:
                            if 'AuthorizationException' not in str(e):
                                logging.error(f"Error clearing scroll context: {e}")
        
        # Return aggregations and total hits if they exist
        if aggregations:
            return {
                'aggregations': aggregations,
                'total_hits': total_hits
            }

        return all_hits


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Example usage:
    try:
        # 使用env参数来指定环境
        es_util = EsUtil(env='sandbox') 
        # 定义你的查询和索引
        index_to_search = 'your_index_name' # 替换为你的索引名
        query = {
            "query": {
                "match_all": {}
            },
            "size": 10
        }
        # search方法现在需要传入index_name
        results = es_util.search(query, index_name=index_to_search)
        for hit in results:
            print(json.dumps(hit, indent=2))
    except (FileNotFoundError, ValueError) as e:
        logging.error(f"Setup failed, please check your config or credentials: {e}")