#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试JSON提取功能

这个脚本用于测试从日志中提取JSON数据的功能，包括不同格式的JSON数据。
"""

import time
import json
import socketio

# 服务器地址
SERVER_URL = "http://localhost:3000"

# 测试日志消息
test_logs = [
    # 标准JSON格式
    "2023-09-09 10:00:00 INFO AppName: user_behavior: {\"userId\":\"user123\",\"action\":\"login\",\"timestamp\":1631234567890,\"data\":{\"device\":\"mobile\"}}",
    
    # JSON嵌入在其他文本中
    "2023-09-09 10:01:00 INFO AppName: Some text before user_behavior: {\"userId\":\"user456\",\"action\":\"click\",\"timestamp\":1631234567891,\"data\":{\"button\":\"submit\"}} and some text after",
    
    # 格式不规范的JSON（缺少引号）
    "2023-09-09 10:02:00 INFO AppName: user_behavior: {userId:\"user789\",action:\"view\",timestamp:1631234567892,data:{page:\"home\"}}",
    
    # 嵌套复杂的JSON
    "2023-09-09 10:03:00 INFO AppName: user_behavior: {\"userId\":\"user101\",\"action\":\"purchase\",\"timestamp\":1631234567893,\"data\":{\"items\":[{\"id\":1,\"name\":\"Product A\",\"price\":99.99},{\"id\":2,\"name\":\"Product B\",\"price\":49.99}],\"total\":149.98}}",
    
    # 不完整的JSON
    "2023-09-09 10:04:00 INFO AppName: user_behavior: {\"userId\":\"user202\",\"action\":\"logout\",\"timestamp\":1631234567894",
    
    # 非JSON数据
    "2023-09-09 10:05:00 INFO AppName: user_behavior: This is not a JSON data"
]

# 创建SocketIO客户端
sio = socketio.Client()

@sio.event
def connect():
    print("已连接到服务器")

@sio.event
def disconnect():
    print("已断开连接")

@sio.on('behavior_triggered')
def on_behavior_triggered(data):
    print("\n检测到行为触发:")
    print(f"行为名称: {data['behavior']['name']}")
    print(f"提取的数据: {json.dumps(data['extractedData'], ensure_ascii=False, indent=2)}")
    print(f"验证结果: {json.dumps(data['validationResults'], ensure_ascii=False, indent=2)}")

# 模拟发送日志
def send_log(log_message):
    print(f"\n发送日志: {log_message}")
    sio.emit('log', {
        'platform': 'test',
        'message': log_message
    })
    
    # 等待一下，让服务器有时间处理
    time.sleep(2)

# 主函数
def main():
    print("开始测试JSON提取功能...")
    
    try:
        # 连接到服务器
        sio.connect(SERVER_URL)
        
        # 发送测试日志
        for i, log in enumerate(test_logs):
            print(f"\n测试 {i+1}/{len(test_logs)}")
            send_log(log)
        
        print("\n测试完成！")
        
        # 等待一下，确保所有事件都被处理
        time.sleep(2)
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        # 断开连接
        if sio.connected:
            sio.disconnect()

if __name__ == "__main__":
    main()