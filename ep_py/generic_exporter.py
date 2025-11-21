# -*- coding: utf-8 -*-

import click
import logging
import json
import os
import re
import sys
from datetime import datetime, timedelta

import yaml
import pytz

# 将项目根目录添加到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from ep_py.common import EsUtil, DeduplicateProcessor, CustomScriptProcessor, RegexFilterProcessor, TimestampConverterProcessor, URLDecodeProcessor, StatsCollectorProcessor, JsonToCsvProcessor, KvParser, GrokParser, TypeConverter, DatetimeParser, FieldMerger, LookupEnricher
from ep_py.es_query_builder import ESQueryBuilder
from ep_py.exporters import get_exporter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_output_path(config, ctx, file_extension, is_final=False):
    """根据配置和参数决定输出文件路径。"""
    output_config = config.get('output', {})
    path_key = 'final_path' if is_final else 'path'

    # 命令行参数优先级最高
    if ctx.params.get('output_path') and not is_final:
        return ctx.params['output_path']

    path_template = output_config.get(path_key)
    if not path_template:
        if is_final:
            return None  # final_path不是必须的
        # Fallback to a default filename if 'path' is not in config
        query_name = config.get('query_name', 'export')
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{query_name}_{date_str}.{file_extension}"
        return os.path.join(project_root, 'data', filename)

    # 替换模板变量
    template_vars = ctx.params.copy()
    template_vars['query_name'] = config.get('query_name', 'export')
    template_vars['date'] = datetime.now().strftime('%Y%m%d')
    template_vars['time'] = datetime.now().strftime('%H%M%S')

    processed_path = path_template
    for key, value in template_vars.items():
        if value is not None:
            processed_path = processed_path.replace(f'{{{{{key}}}}}', str(value))

    # 添加文件扩展名
    if not any(processed_path.endswith(ext) for ext in ['.csv', '.jsonl']):
        processed_path = f"{processed_path}.{file_extension}"

    # 处理相对路径
    if not os.path.isabs(processed_path):
        processed_path = os.path.join(project_root, 'data', processed_path)

    return processed_path

@click.command()
@click.option('--config', required=True, help="任务YAML配置文件的路径")
@click.option('--env', default='default', help="要使用的环境 (对应local_config.yaml中的配置)")
@click.option('--days', type=int, help="查询最近N天的数据")
@click.option('--hours', type=int, help="查询最近N小时的数据")
@click.option('--start-time', help="查询的开始时间 (YYYY-MM-DD HH:MM:SS)")
@click.option('--end-time', help="查询的结束时间 (YYYY-MM-DD HH:MM:SS)")
@click.option('--output-path', help="输出文件的完整路径（可选）")
@click.option('--dry-run', is_flag=True, help="只打印查询语句而不执行")
def main(config, env, days, hours, start_time, end_time, output_path, dry_run):

    # 加载任务配置
    with open(config, 'r', encoding='utf-8') as f:
        task_config = yaml.safe_load(f)

    # 设置时区
    if env == 'cn':
        tz = pytz.timezone('Asia/Shanghai')
        logging.info("Using timezone: Asia/Shanghai (Beijing Time)")
    else:
        tz = pytz.utc
        logging.info("Using timezone: UTC")

    # 构建查询
    runtime_params = {
        'config': config,
        'env': env,
        'days': days,
        'hours': hours,
        'start_time': start_time,
        'end_time': end_time,
        'output_path': output_path,
        'dry_run': dry_run
    }
    now = datetime.now(tz)
    
    # 确定时间范围
    end_time_val = now
    if end_time:
        end_time_val = tz.localize(datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S'))

    start_time_val = None
    if start_time:
        start_time_val = tz.localize(datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S'))
    elif days is not None:
        start_time_val = end_time_val - timedelta(days=days)
    elif hours is not None:
        start_time_val = end_time_val - timedelta(hours=hours)

    # 格式化时间为UTC ISO 8601格式，用于ES查询
    if start_time_val:
        runtime_params['start_time'] = start_time_val.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    runtime_params['end_time'] = end_time_val.astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    query_builder = ESQueryBuilder(config)
    query = query_builder.build_query(runtime_params=runtime_params)

    if dry_run:
        logging.info("--- DRY RUN ---")
        logging.info(f"Index: {query_builder.index_name}")
        logging.info(f"Query: \n{json.dumps(query, indent=2, ensure_ascii=False)}")
        return

    # 准备导出
    output_config = task_config.get('output', {})
    output_fields = output_config.get('fields')
    dynamic_fields = output_fields and (output_fields == '*' or output_fields == ['*'])

    exporter = None
    output_path_val = None
    file_extension = ''

    args_like = type('Args', (), {'params': runtime_params})()

    if not dynamic_fields:
        temp_exporter = get_exporter(task_config)
        file_extension = temp_exporter.file_extension
        output_path_val = get_output_path(task_config, args_like, file_extension, is_final=False)
        exporter = get_exporter(task_config, output_path_val)
    else:
        output_format = output_config.get('format', 'csv').lower()
        file_extension = 'csv' if output_format == 'csv' else 'jsonl'
        output_path_val = get_output_path(task_config, args_like, file_extension, is_final=False)

    final_output_path = get_output_path(task_config, args_like, file_extension, is_final=True)

    # 确保输出目录存在
    output_dir = os.path.dirname(output_path_val)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    if final_output_path:
        final_output_dir = os.path.dirname(final_output_path)
        if final_output_dir:
            os.makedirs(final_output_dir, exist_ok=True)

    # 执行查询并导出
    try:
        es_util = EsUtil(env=env)
        if exporter:
            exporter.write_header()
        
        # 初始化后处理器
        batch_processors = []
        final_processors = []
        post_processing_rules = task_config.get('post_processing', [])


        for rule in post_processing_rules:
            processor_name = rule.get('name') or rule.get('type')
            params = rule.get('params', {})

            if processor_name == 'deduplicate':
                batch_processors.append(DeduplicateProcessor(fields=params.get('fields', [])))
            elif processor_name == 'filter_by_regex':
                batch_processors.append(RegexFilterProcessor(field=params.get('field'), pattern=params.get('pattern')))
            elif processor_name == 'timestamp_converter':
                batch_processors.append(TimestampConverterProcessor(
                    field=params.get('field'),
                    unit=params.get('unit', 's'),
                    timezone=params.get('timezone', 'UTC')
                ))
            elif processor_name == 'url_decode':
                # 支持field（单个字段）或fields（多个字段）参数
                fields_param = params.get('fields') or params.get('field')
                if not fields_param:
                    raise ValueError("url_decode processor requires 'field' or 'fields' parameter")
                batch_processors.append(URLDecodeProcessor(fields=fields_param))
            elif processor_name == 'json_to_csv':
                batch_processors.append(JsonToCsvProcessor(
                    field=params.get('field'),
                    output_path_template=params.get('output_path_template'),
                    ctx=args_like,
                    task_config=task_config,
                    pre_process_pattern=params.get('pre_process_pattern')
                ))
            elif processor_name == 'kv_parser':
                batch_processors.append(KvParser(
                    field=params.get('field'),
                    pair_delimiter=params.get('pair_delimiter', '&'),
                    kv_delimiter=params.get('kv_delimiter', '=')
                ))
            elif processor_name == 'grok_parser':
                batch_processors.append(GrokParser(
                    field=params.get('field'),
                    pattern=params.get('pattern')
                ))
            elif processor_name == 'type_converter':
                batch_processors.append(TypeConverter(
                    fields=params.get('fields')
                ))
            elif processor_name == 'datetime_parser':
                batch_processors.append(DatetimeParser(
                    field=params.get('field'),
                    formats=params.get('formats', []),
                    output_format=params.get('output_format', '%Y-%m-%dT%H:%M:%S.%f%z'),
                    timezone=params.get('timezone')
                ))
            elif processor_name == 'field_merger':
                batch_processors.append(FieldMerger(
                    source_fields=params.get('source_fields'),
                    target_field=params.get('target_field'),
                    separator=params.get('separator', ' ')
                ))
            elif processor_name == 'lookup_enricher':
                batch_processors.append(LookupEnricher(
                    field=params.get('field'),
                    target_field=params.get('target_field'),
                    dictionary=params.get('dictionary'),
                    file_path=params.get('file_path')
                ))
            elif processor_name == 'stats_collector':
                # 支持新的通用配置格式
                stats_configs = params.get('stats_configs')
                output_stats = params.get('output_stats', True)
                
                # 兼容旧版本参数格式
                if stats_configs is None:
                    service_field = params.get('service_field', 'httpServiceName')
                    error_field = params.get('error_field', 'errorCode')
                    # 构建兼容的配置格式
                    stats_configs = [{
                        'name': 'service_error_stats',
                        'fields': [service_field, error_field],
                        'description': f'{service_field}与{error_field}联合统计'
                    }]
                
                batch_processors.append(StatsCollectorProcessor(
                    stats_configs=stats_configs,
                    output_stats=output_stats
                ))
            elif processor_name == 'custom_script':
                script_path = os.path.join(project_root, params['script_path'])
                script_args = params.get('args', [])
                
                # Replace placeholders in args
                template_vars = runtime_params.copy()
                template_vars['output_path'] = output_path_val
                if final_output_path:
                    template_vars['final_output_path'] = final_output_path
                template_vars['query_name'] = task_config.get('query_name', 'export')
                template_vars['date'] = datetime.now().strftime('%Y%m%d')
                template_vars['time'] = datetime.now().strftime('%H%M%S')

                processed_args = []
                for arg in script_args:
                    processed_arg = arg
                    for key, value in template_vars.items():
                        if value is not None:
                            placeholder = f'{{{{{key}}}}}'
                            processed_arg = str(processed_arg).replace(placeholder, str(value))
                    processed_args.append(processed_arg)

                final_processors.append(CustomScriptProcessor(script_path, processed_args))

        def batch_processor_func(hits):
            nonlocal exporter
            processed_hits = hits
            for processor in batch_processors:
                processed_hits = processor.process(processed_hits)

            if not processed_hits:
                return

            # If fields are dynamic, initialize exporter with fields from the first record
            if exporter is None and dynamic_fields:
                first_hit_source = processed_hits[0].get('_source', {})
                if first_hit_source:
                    dynamic_output_fields = list(first_hit_source.keys())
                    
                    # Create a temporary config with the dynamic fields
                    dynamic_task_config = task_config.copy()
                    if 'output' not in dynamic_task_config:
                        dynamic_task_config['output'] = {}
                    dynamic_task_config['output']['fields'] = dynamic_output_fields
                    
                    exporter = get_exporter(dynamic_task_config, output_path_val)
                    exporter.write_header()

            if exporter:
                source_hits = [item.get('_source', {}) for item in processed_hits]
                exporter.write_batch(source_hits)
                logging.info(f"{len(source_hits)} records exported in this batch.")

        logging.info(f"Executing query:\n{json.dumps(query, indent=2)}")
        es_util.search(query, query_builder.index_name, batch_processor_func)
        logging.info(f"Raw data export completed. Output file: {output_path_val}")

        # 处理统计结果
        stats_processors = [p for p in batch_processors if isinstance(p, StatsCollectorProcessor)]
        for stats_processor in stats_processors:
            # 打印统计结果
            stats_processor.print_stats()
            
            # 保存统计结果到文件
            output_dir = os.path.dirname(output_path_val)
            stats_processor.save_stats_to_file(output_dir)

        # 调用所有处理器的 close 方法（如果存在）
        for processor in batch_processors:
            if hasattr(processor, 'close'):
                processor.close()

        # Run final processors
        for processor in final_processors:
            processor.run_script()

        # 如果定义了final_path，并且没有自定义脚本处理器，则将临时文件移动到最终位置
        if final_output_path and not any(isinstance(p, CustomScriptProcessor) for p in final_processors):
            logging.info(f"Moving temporary file {output_path_val} to {final_output_path}")
            os.rename(output_path_val, final_output_path)
            logging.info(f"Final file is available at: {final_output_path}")
        elif final_output_path and any(isinstance(p, CustomScriptProcessor) for p in final_processors):
            # 如果有自定义脚本，脚本负责处理文件
            logging.info(f"Custom script is responsible for creating the final file at {final_output_path}")
            if os.path.exists(final_output_path):
                os.remove(output_path_val)
                logging.info(f"Removed temporary file: {output_path_val}")
            else:
                logging.warning(f"Custom script was expected to create {final_output_path}, but it was not found.")
        else:
            logging.info(f"Processing finished. Output file is at: {output_path_val}")

    except Exception as e:
        logging.error(f"导出过程中发生错误: {e}", exc_info=True)
    finally:
        if exporter:
            exporter.close()

if __name__ == '__main__':
    main()