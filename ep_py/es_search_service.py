# -*- coding: utf-8 -*-
"""
Elasticsearch搜索服务模块

提供从Elasticsearch搜索日志并进行行为分析的功能
"""

import json
import logging
import threading
import time
from datetime import datetime
from flask_socketio import emit

from ep_py.es_query_builder import ESQueryBuilder
from ep_py.common import EsUtil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ElasticsearchSearchService:
    """Elasticsearch搜索服务类"""
    
    def __init__(self, env='sandbox'):
        """
        初始化Elasticsearch搜索服务
        
        参数:
            env: 环境名称 (cn/sandbox/production)
        """
        try:
            self.es_util = EsUtil(env=env)
            self.query_builder = ESQueryBuilder('config/es_search_config.yaml')
            self.search_active = False
            self.search_progress = 0
            self.processed_count = 0
            self.total_hits = 0
            self.current_thread = None
            self.env = env
            logging.info(f"Elasticsearch搜索服务初始化完成，环境: {env}")
        except Exception as e:
            logging.error(f"Elasticsearch搜索服务初始化失败: {e}")
            raise
    
    def search_logs(self, index_name, user_id, start_time, end_time, platform, socketio, query_template=None):
        """
        执行Elasticsearch日志搜索
        
        参数:
            index_name: Elasticsearch索引名称
            user_id: 用户ID
            start_time: 开始时间 (ISO格式)
            end_time: 结束时间 (ISO格式)
            platform: 平台类型
            socketio: SocketIO实例用于实时通信
            
        返回:
            dict: 搜索结果状态
        """
        if self.search_active:
            return {
                'success': False,
                'message': '已有搜索任务正在进行中'
            }
        
        # 启动搜索线程
        self.current_thread = threading.Thread(
            target=self._search_thread,
            args=(index_name, user_id, start_time, end_time, platform, socketio, query_template)
        )
        self.current_thread.start()
        
        return {
            'success': True,
            'message': '搜索任务已启动'
        }
    
    def _search_thread(self, index_name, user_id, start_time, end_time, platform, socketio, query_template=None):
        """
        搜索执行线程
        """
        self.search_active = True
        self.search_progress = 0
        self.processed_count = 0
        
        try:
            logging.info(f"开始Elasticsearch搜索: index={index_name}, user_id={user_id}")
            
            # 发送开始搜索消息
            socketio.emit('log', {
                'platform': 'system',
                'message': f'开始Elasticsearch搜索: 索引={index_name}, 用户ID={user_id}, 时间范围={start_time} 至 {end_time}, 环境={self.env}'
            })
            
            # 构建查询参数
            runtime_params = {
                'start_time': start_time,
                'end_time': end_time,
                'user_id': user_id
            }
            
            # 构建查询
            query = self.query_builder.build_query(runtime_params=runtime_params, template_override=query_template)
            logging.info(f"构建的查询: {json.dumps(query, indent=2, ensure_ascii=False)}")
            socketio.emit('log', {
                'platform': 'system',
                'message': 'ES搜索查询配置:\n' + json.dumps(query, indent=2, ensure_ascii=False)
            })
            
            # 执行搜索
            socketio.emit('log', {
                'platform': 'system',
                'message': '正在执行Elasticsearch查询...'
            })
            
            results = self.es_util.search(query, index_name)
            
            if not results:
                socketio.emit('log', {
                    'platform': 'system',
                    'message': '未找到匹配的日志数据'
                })
                return
            
            self.total_hits = len(results)
            logging.info(f"搜索完成，共找到 {self.total_hits} 条记录")
            
            socketio.emit('log', {
                'platform': 'system',
                'message': f'搜索完成，共找到 {self.total_hits} 条记录，开始行为分析...'
            })
            
            # 处理结果
            for i, hit in enumerate(results):
                if not self.search_active:
                    socketio.emit('log', {
                        'platform': 'system',
                        'message': '搜索已停止'
                    })
                    break
                
                try:
                    # 提取日志数据
                    log_data = self._extract_log_data(hit)
                    
                    # 发送原始日志到前端
                    socketio.emit('log', {
                        'platform': 'elasticsearch',
                        'message': f"[{log_data['timestamp']}] {log_data['level']} {log_data['module']} - {log_data['message']}"
                    })
                    
                    # 应用行为分析
                    self._analyze_log_with_behavior(log_data, platform, socketio)
                    
                    # 更新进度
                    self.processed_count += 1
                    self.search_progress = self.processed_count / self.total_hits
                    
                    # 每处理10条发送一次进度更新
                    if self.processed_count % 10 == 0:
                        socketio.emit('es_search_progress', {
                            'processed': self.processed_count,
                            'total': self.total_hits,
                            'progress': self.search_progress
                        })
                    
                    # 添加小延迟避免过载
                    time.sleep(0.01)
                    
                except Exception as e:
                    logging.error(f"处理日志数据失败: {e}")
                    socketio.emit('log', {
                        'platform': 'system',
                        'message': f'处理日志数据失败: {str(e)}'
                    })
            
            # 搜索完成
            socketio.emit('log', {
                'platform': 'system',
                'message': f'Elasticsearch搜索和行为分析完成，共处理 {self.processed_count} 条日志'
            })
            
            socketio.emit('es_search_complete', {
                'success': True,
                'total_hits': self.total_hits,
                'processed': self.processed_count,
                'message': f'搜索完成，处理了 {self.processed_count} 条日志'
            })
            
        except Exception as e:
            logging.error(f"Elasticsearch搜索失败: {e}")
            socketio.emit('log', {
                'platform': 'system',
                'message': f'Elasticsearch搜索失败: {str(e)}'
            })
            socketio.emit('es_search_complete', {
                'success': False,
                'message': f'搜索失败: {str(e)}'
            })
        finally:
            self.search_active = False
            self.search_progress = 0
    
    def stop_search(self):
        """停止搜索"""
        self.search_active = False
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread.join(timeout=5)
        logging.info("Elasticsearch搜索已停止")
    
    def get_search_status(self):
        """获取搜索状态"""
        return {
            'searching': self.search_active,
            'progress': self.search_progress,
            'processed': self.processed_count,
            'total': self.total_hits
        }
    
    def _extract_log_data(self, hit):
        """
        从Elasticsearch结果中提取日志数据
        
        参数:
            hit: Elasticsearch命中文档
            
        返回:
            dict: 提取的日志数据
        """
        source = hit.get('_source', {})
        
        # 提取时间戳
        timestamp = source.get('@timestamp', '')
        if not timestamp:
            timestamp = source.get('timestamp', datetime.now().isoformat())
        
        # 提取消息内容
        message = source.get('message', '')
        if not message:
            # 尝试其他可能的字段
            message = source.get('msg', source.get('log', '无消息内容'))
        
        return {
            'timestamp': timestamp,
            'message': message,
            'userId': source.get('userId', source.get('user_id', '')),
            'level': source.get('level', 'INFO'),
            'module': source.get('module', source.get('component', '')),
            'properties': source.get('properties', {}),
            'raw_data': json.dumps(source, ensure_ascii=False)
        }
    
    def _analyze_log_with_behavior(self, log_data, platform, socketio):
        """
        使用现有行为分析逻辑处理日志
        
        参数:
            log_data: 日志数据
            platform: 平台类型
            socketio: SocketIO实例
        """
        try:
            # 将日志数据格式化为现有分析函数所需的格式
            formatted_log = self._format_log_for_analysis(log_data)
            
            # 这里可以调用现有的analyze_log_behavior函数
            # 但由于该函数在server.py中，我们需要将分析逻辑提取出来或在这里重新实现
            
            # 简化版的行为分析 - 可以扩展为调用完整的分析逻辑
            self._perform_basic_analysis(formatted_log, platform, socketio)
            
        except Exception as e:
            logging.error(f"行为分析失败: {e}")
            socketio.emit('log', {
                'platform': 'system',
                'message': f'行为分析失败: {str(e)}'
            })
    
    def _format_log_for_analysis(self, log_data):
        """
        格式化日志数据用于分析
        
        参数:
            log_data: 原始日志数据
            
        返回:
            str: 格式化后的日志字符串
        """
        # 根据现有系统的日志格式进行格式化
        timestamp = log_data['timestamp']
        level = log_data['level']
        module = log_data['module']
        message = log_data['message']
        
        # 构建类似现有系统的日志格式
        formatted_log = f"{timestamp} {level} {module} - {message}"
        
        # 如果有额外属性，也添加进去
        if log_data['properties']:
            props_str = json.dumps(log_data['properties'], ensure_ascii=False)
            formatted_log += f" {props_str}"
        
        return formatted_log
    
    def _perform_basic_analysis(self, formatted_log, platform, socketio):
        """
        执行基础行为分析
        
        参数:
            formatted_log: 格式化的日志字符串
            platform: 平台类型
            socketio: SocketIO实例
        """
        # 这里可以实现基础的行为分析逻辑
        # 例如：关键词匹配、模式识别等
        
        # 示例：简单的关键词匹配
        keywords = ['error', 'exception', 'failed', 'timeout']
        log_lower = formatted_log.lower()
        
        for keyword in keywords:
            if keyword in log_lower:
                socketio.emit('log', {
                    'platform': 'behavior',
                    'message': f'发现关键词 "{keyword}": {formatted_log[:100]}...'
                })
                break


# 全局搜索服务实例
es_search_service = None


def get_es_search_service(env='sandbox'):
    """获取Elasticsearch搜索服务实例"""
    global es_search_service
    if es_search_service is None:
        try:
            es_search_service = ElasticsearchSearchService(env=env)
        except Exception as e:
            logging.error(f"创建Elasticsearch搜索服务失败: {e}")
            return None
    return es_search_service