#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用统计分析脚本：支持多种字段组合的统计分析
用法：python stats_analyzer.py <csv_file_path> [--stats-configs <json_config>]
"""

import pandas as pd
import sys
import os
import json
import argparse
from collections import Counter
from tabulate import tabulate

def analyze_stats(csv_file_path, stats_configs=None, top_n=20):
    """
    分析CSV文件中指定字段的统计信息
    
    Args:
        csv_file_path (str): CSV文件路径
        stats_configs (list): 统计配置列表
        top_n (int): 显示前N个结果
    
    Returns:
        dict: 统计结果
    """
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file_path)
        
        # 默认配置（兼容旧版本）
        if stats_configs is None:
            stats_configs = [{
                'name': 'service_error_stats',
                'fields': ['httpServiceName', 'errorCode'],
                'description': 'httpServiceName与errorCode联合统计'
            }]
        
        print(f"📁 分析文件: {csv_file_path}")
        print(f"📊 总记录数: {len(df)}")
        print("\n" + "="*80)
        print("📈 数据统计分析结果")
        print("="*80)
        
        all_results = {}
        
        # 为每个统计配置进行分析
        for config in stats_configs:
            config_name = config['name']
            fields = config['fields']
            description = config.get('description', config_name)
            
            print(f"\n{'='*60}")
            print(f"📊 {description} ({config_name})")
            print(f"{'='*60}")
            
            # 检查必要的列是否存在
            missing_columns = [col for col in fields if col not in df.columns]
            
            if missing_columns:
                print(f"⚠️  警告：CSV文件中缺少必要的列: {missing_columns}")
                print(f"📋 可用的列: {list(df.columns)}")
                continue
            
            # 过滤掉空值
            df_filtered = df.dropna(subset=fields)
            
            print(f"📈 有效记录数（所有字段非空）: {len(df_filtered)}")
            
            if len(df_filtered) == 0:
                print("⚠️  没有有效记录可供分析")
                continue
            
            # 配置详细信息
            config_data = [
                ["统计字段", ", ".join(fields)],
                ["有效记录数", len(df_filtered)],
            ]
            
            # 计算每个字段的唯一值数量
            for field in fields:
                unique_count = df_filtered[field].nunique()
                config_data.append([f"唯一{field}数量", unique_count])
            
            print("\n📋 配置信息:")
            print(tabulate(config_data, headers=['指标', '数值'], tablefmt='grid'))
            
            # 联合统计（多字段组合）
            if len(fields) > 1:
                combined_stats = df_filtered.groupby(fields).size().reset_index(name='count')
                combined_stats = combined_stats.sort_values('count', ascending=False)
                
                config_data.append(["唯一组合数量", len(combined_stats)])
                
                print(f"\n📊 {description}联合统计 (前{min(top_n, len(combined_stats))}个):")
                table_data = []
                for _, row in combined_stats.head(top_n).iterrows():
                    row_data = [row[field] for field in fields] + [row['count']]
                    table_data.append(row_data)
                
                headers = fields + ['Count']
                print(tabulate(table_data, headers=headers, tablefmt='grid', stralign='left'))
                
                # 保存联合统计到文件
                output_dir = os.path.dirname(csv_file_path)
                stats_file = os.path.join(output_dir, f'{config_name}_stats.csv')
                combined_stats.to_csv(stats_file, index=False, encoding='utf-8')
                print(f"💾 联合统计已保存到: {stats_file}")
                
                all_results[config_name] = {
                    'config': config,
                    'valid_records': len(df_filtered),
                    'combined_stats': combined_stats
                }
            
            # 单个字段统计
            for field in fields:
                field_stats = df_filtered[field].value_counts()
                print(f"\n📈 {field}统计 (前{min(top_n//2, len(field_stats))}个):")
                field_table = [[value, count] for value, count in field_stats.head(top_n//2).items()]
                print(tabulate(field_table, headers=[field, 'Count'], 
                              tablefmt='grid', stralign='left'))
                
                if config_name not in all_results:
                    all_results[config_name] = {
                        'config': config,
                        'valid_records': len(df_filtered)
                    }
                
                all_results[config_name][f'{field}_stats'] = field_stats
        
        return all_results
        
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {csv_file_path}")
        return None
    except pd.errors.EmptyDataError:
        print(f"❌ 错误：文件 {csv_file_path} 为空")
        return None
    except Exception as e:
        print(f"❌ 错误：处理文件时发生异常 - {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description='通用统计分析脚本')
    parser.add_argument('csv_file', help='要分析的CSV文件路径')
    parser.add_argument('--stats-configs', type=str, help='统计配置JSON字符串')
    parser.add_argument('--top', type=int, default=20, help='显示前N个结果（默认20）')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_file):
        print(f"❌ 错误：文件 {args.csv_file} 不存在")
        sys.exit(1)
    
    # 解析统计配置
    stats_configs = None
    if args.stats_configs:
        try:
            stats_configs = json.loads(args.stats_configs)
        except json.JSONDecodeError as e:
            print(f"❌ 错误：无法解析统计配置JSON - {str(e)}")
            sys.exit(1)
    
    print(f"🔍 开始分析文件: {args.csv_file}")
    print("="*80)
    
    result = analyze_stats(args.csv_file, stats_configs, args.top)
    
    if result is None:
        sys.exit(1)
    
    print("\n✅ 分析完成！")

if __name__ == '__main__':
    main()