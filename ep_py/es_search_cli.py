#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Elasticsearch搜索命令行接口

提供命令行方式调用Elasticsearch搜索服务
"""

import argparse
import json
import logging
import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ep_py.es_search_service import get_es_search_service

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class SimpleSocketIO:
    """简单的SocketIO模拟类，用于命令行模式"""
    
    def __init__(self, request_id=None):
        self.messages = []
        self.request_id = request_id or '-'
    
    def emit(self, event, data):
        """模拟SocketIO的emit方法"""
        if event == 'log':
            message = f"[{data.get('platform', 'unknown')}] [req:{self.request_id}] {data.get('message', '')}"
            print(message)
            self.messages.append(message)
        elif event == 'behavior_triggered':
            import json as _json
            print("__BEHAVIOR__ " + _json.dumps(data, ensure_ascii=False))
        elif event == 'es_search_progress':
            progress = data.get('progress', 0) * 100
            processed = data.get('processed', 0)
            total = data.get('total', 0)
            print(f"[req:{self.request_id}] 搜索进度: {progress:.1f}% ({processed}/{total})")
        elif event == 'es_search_complete':
            success = data.get('success', False)
            message = data.get('message', '')
            status = "完成" if success else "失败"
            print(f"[req:{self.request_id}] 搜索{status}: {message}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Elasticsearch日志搜索工具')
    parser.add_argument('--mode', choices=['api', 'cli'], default='cli',
                       help='运行模式: api (API调用) 或 cli (命令行)')
    parser.add_argument('--index', required=True, help='Elasticsearch索引名称')
    parser.add_argument('--user_id', required=True, help='用户ID')
    parser.add_argument('--start_time', required=True, help='开始时间 (ISO格式)')
    parser.add_argument('--end_time', required=True, help='结束时间 (ISO格式)')
    parser.add_argument('--platform', default='elasticsearch', help='平台类型')
    parser.add_argument('--env', default='sandbox', choices=['cn', 'sandbox', 'production'],
                       help='运行环境 (cn: 中国, sandbox: 沙盒, production: 生产)')
    parser.add_argument('--output', choices=['json', 'text'], default='json',
                       help='输出格式')
    parser.add_argument('--query_template', required=False, help='查询模板(JSON字符串)，优先于配置文件模板')
    parser.add_argument('--log_param', required=False, help='日志匹配参数，用于内容搜索')
    parser.add_argument('--request_id', required=False, help='请求ID，用于日志关联')
    
    args = parser.parse_args()
    
    try:
        # 获取搜索服务
        search_service = get_es_search_service(env=args.env)
        if not search_service:
            print(json.dumps({
                'success': False,
                'message': '无法初始化Elasticsearch搜索服务'
            }))
            return 1
        
        # 创建SocketIO模拟器
        socketio = SimpleSocketIO(request_id=args.request_id)
        
        if args.mode == 'cli':
            print(f"开始Elasticsearch搜索...")
            print(f"索引: {args.index}")
            print(f"用户ID: {args.user_id}")
            print(f"环境: {args.env}")
            print(f"时间范围: {args.start_time} 至 {args.end_time}")
            print("-" * 50)
        
        # 执行搜索
        result = search_service.search_logs(
            index_name=args.index,
            user_id=args.user_id,
            start_time=args.start_time,
            end_time=args.end_time,
            platform=args.platform,
            socketio=socketio,
            query_template=args.query_template,
            log_param=args.log_param
        )
        
        if args.mode == 'cli':
            print("-" * 50)
            print(f"搜索结果: {result['message']}")
        
        # 输出JSON结果
        if args.output == 'json':
            final_result = {
                'success': result['success'],
                'message': result['message'],
                'total_hits': search_service.total_hits,
                'processed': search_service.processed_count,
                'search_status': search_service.get_search_status()
            }
            print(json.dumps(final_result, ensure_ascii=False, indent=2))
        
        return 0 if result['success'] else 1
        
    except Exception as e:
        error_result = {
            'success': False,
            'message': f'搜索过程发生错误: {str(e)}'
        }
        
        if args.output == 'json':
            print(json.dumps(error_result, ensure_ascii=False))
        else:
            print(f"错误: {error_result['message']}")
        
        return 1


if __name__ == '__main__':
    sys.exit(main())