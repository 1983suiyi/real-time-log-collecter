#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试RUM数据上报的JSON Schema验证

这个脚本用于测试RUM数据上报中module字段的类型验证是否正常工作。
根据配置，module字段应该是number类型，但实际可能是string类型。
"""

import time
import json
import socketio
import sys
import re

# 服务器地址
SERVER_URL = "http://localhost:3000"

# 测试数据
test_logs = [
    # 测试1：module为数字类型（符合schema）
    '2023-09-09 10:00:00 INFO AppName: RUM element flushed success: {"app_id":123,"data_version":"1.0","event":"page_view","rum_id":"abc123","ts":"2023-09-09T10:00:00Z","properties":{"app_version":"1.0.0","sdk_version":"2.1.0","device":"iPhone","os":"iOS","module":42}}',
    
    # 测试2：module为字符串类型（不符合schema）
    '2023-09-09 10:01:00 INFO AppName: RUM element flushed success: {"app_id":123,"data_version":"1.0","event":"page_view","rum_id":"abc124","ts":"2023-09-09T10:01:00Z","properties":{"app_version":"1.0.0","sdk_version":"2.1.0","device":"iPhone","os":"iOS","module":"42"}}',
    
    # 测试3：app_id为字符串类型（会导致JSON Schema验证失败）
    '2023-09-09 10:02:00 INFO AppName: RUM element flushed success: {"app_id":"idletycoon.global.prod","data_version":"1.0","event":"page_view","rum_id":"abc125","ts":"2023-09-09T10:02:00Z","properties":{"app_version":"1.0.0","sdk_version":"2.1.0","device":"iPhone","os":"iOS","module":43}}'
]

# 创建SocketIO客户端
sio = socketio.Client()

# 测试结果
test_results = []

# 是否捕获到JSON Schema验证错误
schema_validation_errors = []

@sio.event
def connect():
    print("已连接到服务器")

@sio.event
def disconnect():
    print("已断开连接")

# 接收日志事件处理
@sio.on('log')
def on_log(data):
    platform = data.get('platform', 'unknown')
    message = data.get('message', '')
    print(f"收到日志 [{platform}]: {message}")
    
    # 捕获服务器端的验证错误日志
    if 'validation' in message.lower() and 'error' in message.lower():
        print(f"\n捕获到验证错误: {message}")
        test_results.append({
            'type': 'validation_error_log',
            'message': message
        })
    
    # 捕获JSON Schema验证相关日志
    if 'json schema' in message.lower():
        print(f"\n捕获到JSON Schema验证日志: {message}")
        test_results.append({
            'type': 'json_schema_log',
            'message': message
        })
        
    # 特别捕获module字段类型检查日志
    if 'module字段' in message or 'module字段值' in message:
        print(f"\n捕获到module字段类型检查: {message}")
        test_results.append({
            'type': 'module_type_check',
            'message': message
        })
        
        # 尝试从日志中提取module字段的类型信息
        type_match = re.search(r'类型=([a-zA-Z0-9_]+)', message)
        if type_match:
            module_type = type_match.group(1)
            print(f"提取到module字段类型: {module_type}")
            test_results.append({
                'type': 'module_type_extracted',
                'module_type': module_type
            })
            
    # 捕获Schema定义日志
    if 'schema中module字段定义' in message.lower():
        print(f"\n捕获到Schema定义: {message}")
        test_results.append({
            'type': 'schema_definition',
            'message': message
        })
        
        # 尝试从日志中提取Schema定义
        try:
            schema_match = re.search(r'\{.*\}', message)
            if schema_match:
                schema_json = json.loads(schema_match.group(0))
                print(f"提取到Schema定义: {json.dumps(schema_json, indent=2)}")
                test_results.append({
                    'type': 'schema_definition_extracted',
                    'schema': schema_json
                })
        except Exception as e:
            print(f"提取Schema定义失败: {e}")


@sio.on('behavior_triggered')
def on_behavior_triggered(data):
    print("\n检测到行为触发:")
    print(f"行为名称: {data['behavior']['name']}")
    
    # 打印提取的数据
    print("\n提取的数据:")
    print(json.dumps(data['extractedData'], ensure_ascii=False, indent=2))
    
    # 打印验证结果
    print("\n验证结果:")
    print(json.dumps(data['validationResults'], ensure_ascii=False, indent=2))
    
    # 检查是否有验证错误
    if 'validationResults' in data and data['validationResults'] and 'isValid' in data['validationResults']:
        if not data['validationResults']['isValid']:
            print("\n捕获到JSON Schema验证错误:")
            print(f"错误信息: {data['validationResults'].get('error', '未知错误')}")
            schema_validation_errors.append({
                'type': 'json_schema_validation_error',
                'error': data['validationResults'].get('error', '未知错误'),
                'behavior_name': data['behavior']['name']
            })
            test_results.append({
                'type': 'json_schema_validation_error',
                'error': data['validationResults'].get('error', '未知错误'),
                'behavior_name': data['behavior']['name']
            })
            
    # 检查是否有验证错误消息
    if 'validationErrorMessage' in data:
        print("\n捕获到验证错误消息:")
        print(f"错误消息: {data['validationErrorMessage']}")
        schema_validation_errors.append({
            'type': 'validation_error_message',
            'message': data['validationErrorMessage'],
            'behavior_name': data['behavior']['name']
        })
        test_results.append({
            'type': 'validation_error_message',
            'message': data['validationErrorMessage'],
            'behavior_name': data['behavior']['name']
        })
    
    # 特别检查module字段的类型
    if 'rumData' in data['extractedData']:
        try:
            rum_data = json.loads(data['extractedData']['rumData']['raw'])
            print("\nRUM数据详情:")
            print(json.dumps(rum_data, ensure_ascii=False, indent=2))
            
            if 'properties' in rum_data and 'module' in rum_data['properties']:
                module_value = rum_data['properties']['module']
                module_type = type(module_value).__name__
                print(f"\nmodule字段值: {module_value}")
                print(f"module字段类型: {module_type}")
                
                # 记录module字段信息
                test_results.append({
                    'type': 'rum_module_field',
                    'module_value': module_value,
                    'module_type': module_type
                })
                
                # 检查验证结果
                if data['validationResults']:
                    print("\nJSON Schema验证结果:")
                    is_valid = data['validationResults'].get('isValid', False)
                    print(f"验证是否通过: {is_valid}")
                    
                    # 记录测试结果
                    test_result = {
                        'type': 'behavior_validation',
                        'behavior_name': data['behavior']['name'],
                        'module_value': module_value,
                        'module_type': module_type,
                        'is_valid': is_valid,
                        'validation_results': data['validationResults']
                    }
                    test_results.append(test_result)
                    
                    if not is_valid:
                        error = data['validationResults'].get('error', '未知错误')
                        print(f"验证错误: {error}")
                        
                        # 检查错误是否与module字段类型有关
                        if 'module' in error.lower() or 'properties' in error.lower():
                            print(f"\n检测到module字段类型验证错误: {error}")
                            schema_validation_errors.append({
                                'type': 'module_type_validation_error',
                                'module_value': module_value,
                                'module_type': module_type,
                                'error': error
                            })
                        else:
                            print("\n注意: 验证失败，但可能与module字段类型无关")
                    else:
                        print("\n注意: JSON Schema验证通过，这可能表明module字段类型验证没有生效")
        except Exception as e:
            print(f"解析RUM数据时出错: {e}")
            test_results.append({
                'type': 'rum_data_parse_error',
                'error': str(e)
            })

# 主函数
def main():
    try:
        # 连接到服务器
        print(f"正在连接到服务器: {SERVER_URL}...")
        sio.connect(SERVER_URL)
        
        # 等待连接建立
        time.sleep(1)
        
        # 发送测试日志
        print("\n开始发送测试日志...")
        for i, log in enumerate(test_logs):
            print(f"\n发送测试日志 {i+1}/{len(test_logs)}:")
            print(f"日志内容: {log[:100]}...")
            
            # 提取JSON部分进行分析
            json_pattern = re.compile(r'({[^{}]*(?:{[^{}]*}[^{}]*)*})')
            json_match = json_pattern.search(log)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    json_obj = json.loads(json_str)
                    if 'properties' in json_obj and 'module' in json_obj['properties']:
                        module_value = json_obj['properties']['module']
                        module_type = type(module_value).__name__
                        print(f"发送的module字段值: {module_value}, 类型: {module_type}")
                except Exception as e:
                    print(f"解析JSON失败: {e}")
            
            # 发送日志到服务器
            sio.emit('client_log', {'platform': 'test', 'message': log})
            time.sleep(2)  # 等待服务器处理
        
        # 等待所有事件处理完成
        print("\n等待服务器处理所有日志...")
        time.sleep(3)
        
        # 断开连接
        print("\n测试完成，断开连接")
        sio.disconnect()
        
        # 输出测试结果摘要
        print("\n" + "="*50)
        print("测试结果摘要:")
        print("="*50)
        print(f"总共捕获到 {len(test_results)} 个测试结果")
        
        # 分析JSON Schema验证错误
        json_schema_errors = [r for r in test_results if r['type'] == 'json_schema_log' and 'error' in r.get('message', '').lower()]
        json_schema_validation_errors = [r for r in test_results if r['type'] == 'json_schema_validation_error']
        validation_error_messages = [r for r in test_results if r['type'] == 'validation_error_message']
        
        print(f"\nJSON Schema验证错误日志: {len(json_schema_errors)} 个")
        print(f"JSON Schema验证错误: {len(json_schema_validation_errors)} 个")
        print(f"验证错误消息: {len(validation_error_messages)} 个")
        
        # 打印验证错误详情
        if json_schema_validation_errors:
            print("\n验证错误详情:")
            for i, error in enumerate(json_schema_validation_errors):
                print(f"错误 {i+1}: {error.get('error', '未知错误')}")
        
        if validation_error_messages:
            print("\n验证错误消息详情:")
            for i, error in enumerate(validation_error_messages):
                print(f"消息 {i+1}: {error.get('message', '未知消息')}")
        
        # 分析module字段类型检查结果
        module_type_checks = [r for r in test_results if r.get('type') == 'module_type_check']
        print(f"\nmodule字段类型检查: {len(module_type_checks)} 个")
        for i, check in enumerate(module_type_checks):
            print(f"\n检查 {i+1}: {check.get('message')}")
        
        # 分析Schema定义
        schema_defs = [r for r in test_results if r.get('type') == 'schema_definition_extracted']
        print(f"\nSchema定义: {len(schema_defs)} 个")
        for i, schema in enumerate(schema_defs):
            print(f"\nSchema {i+1}: {json.dumps(schema.get('schema'), ensure_ascii=False, indent=2)}")
        
        # 总结问题
        if not json_schema_errors and not json_schema_validation_errors and not validation_error_messages:
            print("\n未发现任何JSON Schema验证错误，请检查服务器日志以获取更多信息")
        else:
            print("\n发现JSON Schema验证错误，请检查module字段的类型定义")
            
    except Exception as e:
        print(f"测试过程中出错: {e}")
    finally:
        # 确保断开连接
        if sio.connected:
            sio.disconnect()

# 执行测试
if __name__ == "__main__":
    main()