#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时日志收集器服务器

这是一个基于 Flask 和 SocketIO 的实时日志收集和分析服务器，支持多平台日志收集：
- Android (通过 adb logcat)
- iOS (通过 idevicesyslog)
- HarmonyOS (通过 hdc hilog)

主要功能：
1. 实时日志流收集和转发
2. 基于正则表达式的行为模式匹配
3. 结构化数据提取和验证
4. 配置文件管理和验证
5. WebSocket 实时通信
"""

import re
import json
import yaml
import os
import subprocess
import threading
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import jsonschema
from jsonschema import validate, ValidationError

# Flask 应用初始化
app = Flask(__name__, static_folder='public')
CORS(app)  # 启用跨域资源共享
socketio = SocketIO(app, cors_allowed_origins="*")  # WebSocket 服务器

# 服务器端口配置
PORT = int(os.environ.get('PORT', 3000))

# 全局变量
log_process = None          # 主日志进程
grep_process = None         # grep 过滤进程
behavior_config = {'behaviors': []}  # 行为配置
logging_active = False      # 日志流控制标志
log_threads = []            # 活跃线程列表

# 配置管理相关函数
def load_config():
    """
    加载行为配置文件
    
    从 config.yaml 文件中加载行为配置，并进行结构验证。
    如果加载失败，将使用默认的空配置。
    
    全局变量:
        behavior_config: 存储加载的行为配置
    
    异常处理:
        - 文件不存在或读取失败
        - YAML 解析错误
        - 配置结构验证失败
    """
    global behavior_config
    try:
        # 读取 YAML 配置文件
        with open('config.yaml', 'r', encoding='utf-8') as f:
            behavior_config = yaml.safe_load(f)
        # 验证配置结构
        validate_config_structure(behavior_config)
    except Exception as e:
        print(f'Error reading or parsing config.yaml: {e}')
        # 使用默认空配置
        behavior_config = {'behaviors': []}

def validate_config_structure(config):
    """
    验证配置结构是否符合 JSON Schema
    
    使用 config_schema.json 文件中定义的 JSON Schema 来验证配置结构的有效性。
    
    参数:
        config (dict): 需要验证的配置字典
    
    返回:
        tuple: (是否有效, 错误信息)
            - (True, None): 验证通过
            - (False, error_message): 验证失败，包含错误信息
    
    异常处理:
        - ValidationError: JSON Schema 验证失败
        - FileNotFoundError: Schema 文件不存在
        - 其他异常: 通用错误处理
    """
    try:
        # 读取 JSON Schema 文件
        with open('config_schema.json', 'r', encoding='utf-8') as f:
            schema = json.load(f)
        # 使用 jsonschema 库验证配置
        validate(instance=config, schema=schema)
        return True, None
    except ValidationError as e:
        return False, f"Configuration validation error: {e.message}"
    except FileNotFoundError:
        print("Warning: config_schema.json not found, skipping schema validation")
        return True, None
    except Exception as e:
        return False, f"Schema validation error: {str(e)}"

def validate_data_by_type(data, data_type, validation_rules=None):
    """
    根据指定类型和规则验证数据
    
    支持多种数据类型的验证，包括 JSON、数字、布尔值和文本。
    可以应用额外的验证规则，如 JSON Schema、数值范围、字符串长度等。
    
    参数:
        data: 需要验证的原始数据
        data_type (str): 数据类型 ('json', 'number', 'boolean', 'text')
        validation_rules (dict, optional): 额外的验证规则
    
    返回:
        tuple: (是否有效, 解析后的数据, 错误信息)
            - (True, parsed_data, None): 验证通过
            - (False, None, error_message): 验证失败
    
    支持的验证规则:
        - jsonSchema: JSON 数据的 Schema 验证
        - numberRange: 数值范围验证 (min, max)
        - stringLength: 字符串长度验证 (min, max)
    """
    try:
        if data_type == 'json':
            # JSON 数据类型处理
            if isinstance(data, str):
                parsed_data = json.loads(data)  # 解析 JSON 字符串
            else:
                parsed_data = data
            
            # 应用 JSON Schema 验证（如果提供）
            if validation_rules and 'jsonSchema' in validation_rules:
                validate(instance=parsed_data, schema=validation_rules['jsonSchema'])
            return True, parsed_data, None
            
        elif data_type == 'number':
            # 数字类型处理
            if isinstance(data, str):
                num_data = float(data)  # 字符串转浮点数
            else:
                num_data = float(data)  # 确保为浮点数类型
            
            # 应用数值范围验证（如果提供）
            if validation_rules and 'numberRange' in validation_rules:
                range_rules = validation_rules['numberRange']
                # 检查最小值
                if 'min' in range_rules and num_data < range_rules['min']:
                    return False, None, f"Number {num_data} is below minimum {range_rules['min']}"
                # 检查最大值
                if 'max' in range_rules and num_data > range_rules['max']:
                    return False, None, f"Number {num_data} is above maximum {range_rules['max']}"
            return True, num_data, None
            
        elif data_type == 'boolean':
            # 布尔类型处理
            if isinstance(data, str):
                # 字符串转布尔值，支持多种表示方式
                bool_data = data.lower() in ('true', '1', 'yes', 'on')
            else:
                bool_data = bool(data)  # 直接转换为布尔值
            return True, bool_data, None
            
        elif data_type == 'text':
            # 文本类型处理
            str_data = str(data)  # 转换为字符串
            # 应用字符串长度验证（如果提供）
            if validation_rules and 'stringLength' in validation_rules:
                length_rules = validation_rules['stringLength']
                # 检查最小长度
                if 'min' in length_rules and len(str_data) < length_rules['min']:
                    return False, None, f"String length {len(str_data)} is below minimum {length_rules['min']}"
                # 检查最大长度
                if 'max' in length_rules and len(str_data) > length_rules['max']:
                    return False, None, f"String length {len(str_data)} is above maximum {length_rules['max']}"
            return True, str_data, None
            
        else:
            # 未知类型，直接返回原数据
            return True, data, None
            
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON format: {str(e)}"
    except ValueError as e:
        return False, None, f"Invalid {data_type} format: {str(e)}"
    except ValidationError as e:
        return False, None, f"JSON schema validation failed: {e.message}"
    except Exception as e:
        return False, None, f"Validation error: {str(e)}"

def extract_data_from_log(log_message, extractors):
    """
    使用提取器从日志消息中提取结构化数据
    
    遍历所有配置的提取器，使用正则表达式匹配日志消息，
    提取指定的数据字段并进行类型验证。
    
    参数:
        log_message (str): 待解析的日志消息
        extractors (list): 提取器配置列表
    
    返回:
        dict: 提取的数据字典，包含每个提取器的结果
    
    提取器配置格式:
        {
            'name': '提取器名称',
            'pattern': '正则表达式模式',
            'dataType': '数据类型 (text/json/number/boolean)'
        }
    """
    extracted_data = {}
    
    for extractor in extractors:
        try:
            # 编译正则表达式模式（忽略大小写）
            pattern = re.compile(extractor['pattern'], re.IGNORECASE)
            match = pattern.search(log_message)
            
            if match:
                # 提取原始数据：优先使用第一个捕获组，否则使用整个匹配
                raw_data = match.group(1) if match.groups() else match.group(0)
                data_type = extractor.get('dataType', 'text')  # 默认为文本类型
                
                # 验证提取的数据类型
                is_valid, parsed_data, error = validate_data_by_type(raw_data, data_type)
                
                if is_valid:
                    # 验证成功，存储解析后的数据
                    extracted_data[extractor['name']] = {
                        'value': parsed_data,
                        'type': data_type,
                        'raw': raw_data
                    }
                else:
                    # 验证失败，存储错误信息
                    extracted_data[extractor['name']] = {
                        'value': None,
                        'type': data_type,
                        'raw': raw_data,
                        'error': error
                    }
        except re.error as e:
            # 正则表达式错误，发送系统日志
            socketio.emit('log', {
                'platform': 'system',
                'message': f'Invalid regex pattern in extractor "{extractor.get("name", "unknown")}": {extractor["pattern"]} - {str(e)}'
            })
    
    return extracted_data

# Initialize configuration
load_config()

# 静态文件服务
@app.route('/')
def index():
    """
    提供主页面服务
    
    返回:
        HTML: 应用程序的主页面 (index.html)
    """
    return send_from_directory('public', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    """
    提供静态文件服务
    
    为前端应用提供 CSS、JavaScript、图片等静态资源文件。
    
    参数:
        filename (str): 请求的文件路径
    
    返回:
        File: 对应的静态文件
    """
    return send_from_directory('public', filename)

# API 端点
@app.route('/config', methods=['GET'])
def get_config():
    """
    获取当前配置
    
    返回当前加载的行为配置，包括所有已定义的行为模式。
    
    返回:
        JSON: 当前配置的 JSON 格式数据
    """
    return jsonify(behavior_config)

@app.route('/config', methods=['POST'])
def update_config():
    """
    更新配置
    
    接收新的配置数据，验证其结构和内容的有效性，
    然后保存到配置文件并更新全局配置。
    
    请求体:
        JSON: 新的配置数据，必须包含 'behaviors' 数组
    
    返回:
        JSON: 操作结果消息
        - 成功: {'message': 'Configuration updated successfully.'}
        - 失败: {'error': '错误信息'} (HTTP 400/500)
    
    验证内容:
        - 基本结构验证（必须包含 behaviors 数组）
        - JSON Schema 验证
        - 正则表达式模式验证
    """
    global behavior_config
    try:
        new_config = request.get_json()
        
        # 基本结构验证
        if not new_config or 'behaviors' not in new_config or not isinstance(new_config['behaviors'], list):
            return jsonify({'error': 'Invalid configuration format. Must contain "behaviors" array.'}), 400
        
        # 使用 JSON Schema 验证配置结构
        is_valid, error_message = validate_config_structure(new_config)
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        # 验证每个行为的正则表达式模式
        validation_errors = []
        for i, behavior in enumerate(new_config['behaviors']):
            # 验证主模式
            try:
                re.compile(behavior['pattern'])
            except re.error as e:
                validation_errors.append(f"Behavior {i+1} '{behavior.get('name', 'unknown')}': Invalid regex pattern '{behavior['pattern']}' - {str(e)}")
            
            # 验证提取器模式（如果存在）
            if 'extractors' in behavior:
                for j, extractor in enumerate(behavior['extractors']):
                    try:
                        re.compile(extractor['pattern'])
                    except re.error as e:
                        validation_errors.append(f"Behavior {i+1} '{behavior.get('name', 'unknown')}', Extractor {j+1} '{extractor.get('name', 'unknown')}': Invalid regex pattern '{extractor['pattern']}' - {str(e)}")
        
        if validation_errors:
            return jsonify({'error': 'Regex validation errors', 'details': validation_errors}), 400
        
        # 保存到配置文件
        with open('config.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(new_config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        # 更新内存中的配置
        behavior_config = new_config
        
        socketio.emit('log', {'platform': 'system', 'message': 'Configuration updated successfully.'})
        return jsonify({'message': 'Configuration updated successfully.'}), 200
    except json.JSONDecodeError as e:
        error_msg = f'Invalid JSON format: {str(e)}'
        socketio.emit('log', {'platform': 'system', 'message': f'Error updating configuration: {error_msg}'})
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        error_msg = f'Error updating configuration: {str(e)}'
        socketio.emit('log', {'platform': 'system', 'message': error_msg})
        return jsonify({'error': error_msg}), 500

@app.route('/reload-config', methods=['POST'])
def reload_config():
    """
    重新加载配置
    
    从配置文件重新读取配置信息，用于在外部修改配置文件后
    刷新应用程序的配置状态。
    
    返回:
        str: 操作结果消息
        - 成功: 'Configuration reloaded.' (HTTP 200)
        - 失败: 'Error reloading configuration.' (HTTP 500)
    """
    try:
        load_config()  # 重新加载配置文件
        socketio.emit('log', {'platform': 'system', 'message': 'Configuration reloaded successfully.'})
        return 'Configuration reloaded.', 200
    except Exception as e:
        socketio.emit('log', {'platform': 'system', 'message': f'Error reloading configuration: {str(e)}'})
        return 'Error reloading configuration.', 500

def analyze_log_behavior(log_message, platform):
    """
    分析日志消息是否匹配配置的行为模式
    
    遍历所有配置的行为模式，使用正则表达式检查日志消息是否匹配。
    如果匹配成功，则提取相关数据并触发行为事件。
    
    参数:
        log_message (str): 待分析的日志消息
        platform (str): 日志来源平台
    
    行为匹配流程:
        1. 遍历所有配置的行为模式
        2. 跳过已禁用的行为
        3. 使用正则表达式匹配日志消息
        4. 如果匹配成功，提取数据并验证
        5. 发送行为触发事件
    """
    for behavior in behavior_config.get('behaviors', []):
        # Skip disabled behaviors
        if not behavior.get('enabled', True):
            continue
            
        try:
            pattern = re.compile(behavior['pattern'], re.IGNORECASE)
            match = pattern.search(log_message)
            
            if match:
                # Extract structured data if extractors are defined
                extracted_data = {}
                if 'extractors' in behavior:
                    extracted_data = extract_data_from_log(log_message, behavior['extractors'])
                
                # Validate extracted data if validation rules are defined
                validation_results = {}
                if 'validation' in behavior and extracted_data:
                    data_type = behavior.get('dataType', 'text')
                    validation_rules = behavior['validation']
                    
                    # Get the main data to validate (first extractor or matched text)
                    main_data = None
                    if extracted_data:
                        first_extractor = list(extracted_data.values())[0]
                        main_data = first_extractor.get('raw')
                    else:
                        main_data = match.group(1) if match.groups() else match.group(0)
                    
                    if main_data:
                        is_valid, parsed_data, error = validate_data_by_type(main_data, data_type, validation_rules)
                        validation_results = {
                            'isValid': is_valid,
                            'parsedData': parsed_data,
                            'error': error,
                            'dataType': data_type
                        }
                
                # Emit behavior triggered event with enhanced data
                socketio.emit('behavior_triggered', {
                    'behavior': behavior,
                    'log': log_message,
                    'extractedData': extracted_data,
                    'validationResults': validation_results,
                    'platform': platform,
                    'timestamp': threading.current_thread().ident  # Simple timestamp substitute
                })
                
                # Log validation errors if any
                if validation_results.get('error'):
                    socketio.emit('log', {
                        'platform': 'system',
                        'message': f'Validation error in behavior "{behavior.get("name", "unknown")}": {validation_results["error"]}'
                    })
                    
        except re.error as e:
            socketio.emit('log', {
                'platform': 'system', 
                'message': f'Invalid regex pattern in behavior "{behavior.get("name", "unknown")}": {behavior["pattern"]} - {str(e)}'
            })

def read_log_stream(process, platform, tag=None):
    """
    读取日志流并发送给客户端，支持多行日志合并
    
    从指定进程读取日志流，处理多行日志消息的合并，并通过 WebSocket 实时发送给客户端。
    特别针对 Android 日志格式进行了优化，能够正确识别和合并多行日志条目。
    
    参数:
        process: 日志进程对象，包含 stdout 流
        platform (str): 日志来源平台名称
        tag (str, optional): 标签过滤器（当前未使用，保留用于扩展）
    
    功能:
        1. 识别 Android 日志格式的行首模式
        2. 合并多行日志消息
        3. 处理日志超时和缓冲
        4. 实时发送日志到前端
        5. 触发行为分析
        6. 优雅处理进程终止
    
    日志格式:
        Android: MM-DD HH:MM:SS.mmm PID TID LEVEL TAG: message
    """
    global logging_active
    
    # 匹配 Android 日志格式的正则表达式
    # 格式: MM-DD HH:MM:SS.mmm PID TID LEVEL TAG: message
    android_log_pattern = re.compile(r'^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+\d+\s+\d+\s+[VDIWEF]\s+\w+:')
    
    log_buffer = ""  # 日志缓冲区，用于合并多行日志
    last_log_time = time.time()  # 最后一次日志时间
    timeout_seconds = 2.0  # 不完整日志的超时时间
    
    def send_buffered_log():
        """
        发送缓冲的日志（如果不为空）
        
        将缓冲区中的日志内容发送到前端，并触发行为分析。
        发送后清空缓冲区以准备下一条日志。
        """
        nonlocal log_buffer
        if log_buffer.strip():
            # 发送日志到前端
            socketio.emit('log', {'platform': platform, 'message': log_buffer.strip()})
            # 分析行为模式
            analyze_log_behavior(log_buffer.strip(), platform)
            log_buffer = ""  # 清空缓冲区
    
    try:
        while logging_active and process.poll() is None:
            # Use select to check if data is available with timeout
            import select
            ready, _, _ = select.select([process.stdout], [], [], 0.1)  # 100ms timeout
            
            if not ready:
                # No data available, check timeout and continue
                current_time = time.time()
                if log_buffer and (current_time - last_log_time) > timeout_seconds:
                    send_buffered_log()
                    last_log_time = current_time
                continue
            
            line = process.stdout.readline()
            if not line:
                continue
            
            # Check again if logging is still active before processing
            if not logging_active:
                break
                
            log_message = line.decode('utf-8', errors='ignore').strip()
            if not log_message:
                continue
                
            current_time = time.time()
            
            # Check if this line starts a new log entry
            if android_log_pattern.match(log_message):
                # Send any buffered log before starting a new one
                if log_buffer:
                    send_buffered_log()
                
                # Start new log buffer
                log_buffer = log_message
                last_log_time = current_time
            else:
                # This is a continuation line, append to buffer
                if log_buffer:
                    log_buffer += "\n" + log_message
                else:
                    # If no buffer exists, treat as standalone message
                    socketio.emit('log', {'platform': platform, 'message': log_message})
                    analyze_log_behavior(log_message, platform)
                last_log_time = current_time
                
        # Send any remaining buffered log
        if log_buffer:
            send_buffered_log()
            
    except Exception as e:
        if logging_active:  # Only emit error if logging is still active
            socketio.emit('log', {'platform': 'system', 'message': f'Error reading log stream: {str(e)}'})
    finally:
        # Send any remaining buffered log before terminating
        if log_buffer:
            send_buffered_log()
        # Force terminate the process if it's still running
        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=2)
            except:
                process.kill()  # Force kill if terminate doesn't work

def check_command_available(command):
    """
    检查系统中是否存在指定命令
    
    首先检查本地工具目录，然后检查系统 PATH。
    这对于验证日志收集工具（如 adb、idevicesyslog、hdc 等）是否已安装非常有用。
    
    参数:
        command (str): 要检查的命令名称
    
    返回:
        bool: 如果命令可用返回 True，否则返回 False
    
    示例:
        >>> check_command_available('adb')
        True
        >>> check_command_available('nonexistent_command')
        False
    """
    # First check if command exists in local tools directory
    local_tool_path = os.path.join(os.path.dirname(__file__), 'tools', command)
    if os.path.isfile(local_tool_path) and os.access(local_tool_path, os.X_OK):
        return True
    
    # For hdc, also check toolchains subdirectory
    if command == 'hdc':
        toolchains_path = os.path.join(os.path.dirname(__file__), 'tools', 'toolchains', 'hdc')
        if os.path.isfile(toolchains_path) and os.access(toolchains_path, os.X_OK):
            return True
    
    # Then check system PATH
    try:
        subprocess.run([command, '--version'], capture_output=True, check=False, timeout=5)
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        try:
            # Try alternative check methods
            subprocess.run(['which', command], capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
            return False

def get_command_path(command):
    """
    获取命令的完整路径
    
    优先使用本地工具目录中的命令，然后回退到系统 PATH。
    这对于需要使用命令的绝对路径执行操作时很有用。
    
    参数:
        command (str): 要查找的命令名称
    
    返回:
        str: 命令的完整路径或命令名称（用于系统 PATH 查找）
    
    示例:
        >>> get_command_path('adb')
        '/path/to/tools/adb'  # 如果在本地工具目录中
        'adb'  # 如果需要从系统 PATH 查找
    """
    # First check local tools directory
    local_tool_path = os.path.join(os.path.dirname(__file__), 'tools', command)
    if os.path.isfile(local_tool_path) and os.access(local_tool_path, os.X_OK):
        return local_tool_path
    
    # For hdc, also check toolchains subdirectory
    if command == 'hdc':
        toolchains_path = os.path.join(os.path.dirname(__file__), 'tools', 'toolchains', 'hdc')
        if os.path.isfile(toolchains_path) and os.access(toolchains_path, os.X_OK):
            return toolchains_path
    
    # Return command name for system PATH lookup
    return command

@app.route('/start-log', methods=['POST'])
def start_log():
    """
    启动指定平台的日志收集
    
    根据请求的平台类型启动相应的日志收集进程。支持 Android、iOS 和 HarmonyOS 平台。
    在启动新的日志收集前，会先停止现有的日志收集进程。
    
    请求体:
        JSON: {
            'platform': str,  # 平台类型 ('android', 'ios', 'harmonyos')
            'tag': str        # 可选的标签过滤器
        }
    
    返回:
        str: 操作结果消息
        - 成功: '{platform} logging started.' (HTTP 200)
        - 失败: 错误信息 (HTTP 400/500)
    
    支持的平台:
        - android: 使用 adb logcat 命令
        - ios: 使用 idevicesyslog 命令
        - harmonyos: 使用 hdc hilog 命令
    
    前置条件:
        - 对应平台的工具必须已安装并在 PATH 中可用
        - 设备必须已连接并可被工具识别
    """
    global log_process, grep_process, logging_active
    
    # 解析请求数据
    data = request.get_json()
    platform = data.get('platform')
    tag = data.get('tag', '').strip()
    
    # 检查是否已有日志进程在运行
    if log_process and log_process.poll() is None:
        return 'A logging process is already running.', 400
    
    # 初始化命令配置
    command = []
    command_name = ''
    
    # 根据平台设置特定的命令
    if platform == 'android':
        # Android 平台：使用 adb logcat
        command_name = 'adb'
        command = [get_command_path('adb'), 'logcat']
    elif platform == 'ios':
        # iOS 平台：使用 idevicesyslog
        # 注意：需要安装 libimobiledevice
        # 安装命令：brew install libimobiledevice
        command_name = 'idevicesyslog'
        # 优先使用 Homebrew 安装路径，然后回退到通用路径查找
        if os.path.isfile('/opt/homebrew/bin/idevicesyslog'):
            command = ['/opt/homebrew/bin/idevicesyslog']
        else:
            command = [get_command_path('idevicesyslog')]
    elif platform == 'harmonyos':
        # HarmonyOS 平台：使用 hdc hilog
        # 注意：支持本地工具目录和系统安装的 hdc
        command_name = 'hdc'
        command = [get_command_path('hdc'), 'hilog']
    else:
        # 不支持的平台
        return 'Invalid platform specified.', 400
    
    # 检查命令是否可用
    if not check_command_available(command_name):
        if platform == 'android':
            install_guide = 'Please install Android SDK Platform Tools and ensure adb is in your PATH, or place adb in the tools/ directory.'
        elif platform == 'ios':
            install_guide = 'Please install libimobiledevice: brew install libimobiledevice, or place idevicesyslog in the tools/ directory.'
        elif platform == 'harmonyos':
            install_guide = 'Please download HarmonyOS SDK and add hdc to your PATH, or place hdc executable in the tools/ directory. Download from: https://developer.harmonyos.com/cn/develop/deveco-studio'
        
        error_message = f'Command "{command_name}" not found. {install_guide}'
        socketio.emit('log', {'platform': 'system', 'message': error_message})
        return error_message, 400
    
    try:
        # 设置日志收集活跃标志
        logging_active = True
        
        # 启动主日志进程
        log_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,  # 捕获标准输出
            stderr=subprocess.PIPE,  # 捕获标准错误
            universal_newlines=False,  # 使用字节模式
            bufsize=1  # 行缓冲
        )
        
        socketio.emit('log', {'platform': 'system', 'message': f'Starting {platform} log collection...'})
        
        # 如果请求标签过滤，通过 grep 管道处理
        if tag:
            socketio.emit('log', {'platform': 'system', 'message': f'Applying tag filter: "{tag}"'})
            grep_process = subprocess.Popen(
                ['grep', '--line-buffered', '-F', tag],  # 行缓冲模式，固定字符串匹配
                stdin=log_process.stdout,   # 从日志进程的输出读取
                stdout=subprocess.PIPE,     # 捕获过滤后的输出
                stderr=subprocess.PIPE,     # 捕获错误
                universal_newlines=False,   # 使用字节模式
                bufsize=1  # 行缓冲
            )
            log_process.stdout.close()  # 关闭原始输出，允许 grep 进程接管
            
            # 启动线程读取 grep 进程输出
            log_thread = threading.Thread(
                target=read_log_stream,
                args=(grep_process, platform, tag)
            )
            log_threads.append(log_thread)
            
            # 启动线程处理 grep 标准错误
            def read_grep_stderr():
                try:
                    while logging_active:
                        line = grep_process.stderr.readline()
                        if not line:
                            if grep_process.poll() is not None:
                                break
                            continue
                        if not logging_active:
                            break
                        error_message = line.decode('utf-8', errors='ignore').strip()
                        if error_message:
                            socketio.emit('log', {'platform': 'system', 'message': f'Grep ERROR: {error_message}'})
                except Exception as e:
                    if logging_active:
                        socketio.emit('log', {'platform': 'system', 'message': f'Error reading grep stderr: {str(e)}'})
            
            grep_stderr_thread = threading.Thread(target=read_grep_stderr)
            log_threads.append(grep_stderr_thread)
            grep_stderr_thread.start()
        else:
            # 启动线程直接从主进程读取
            log_thread = threading.Thread(
                target=read_log_stream,
                args=(log_process, platform, tag)
            )
            log_threads.append(log_thread)
        
        log_thread.start()
        
        # 启动线程处理标准错误
        def read_stderr():
            try:
                while logging_active and log_process.poll() is None:
                    line = log_process.stderr.readline()
                    if not line:
                        continue
                    if not logging_active:
                        break
                    error_message = line.decode('utf-8', errors='ignore').strip()
                    if error_message:
                        socketio.emit('log', {'platform': 'system', 'message': f'ERROR: {error_message}'})
            except Exception as e:
                if logging_active:
                    socketio.emit('log', {'platform': 'system', 'message': f'Error reading stderr: {str(e)}'})
        
        stderr_thread = threading.Thread(target=read_stderr)
        log_threads.append(stderr_thread)
        stderr_thread.start()
        
        # 通知前端日志收集已激活
        socketio.emit('logging_status', {'active': True})
        
        return f'{platform} logging started.', 200
        
    except Exception as e:
        # Provide platform-specific installation guidance
        if platform == 'android':
            install_guide = 'Please install Android SDK Platform Tools and ensure adb is in your PATH.'
        elif platform == 'ios':
            install_guide = 'Please install libimobiledevice: brew install libimobiledevice'
        elif platform == 'harmonyos':
            install_guide = 'Please download and install HarmonyOS SDK, then add hdc to your PATH. You can download it from: https://developer.harmonyos.com/cn/develop/deveco-studio'
        else:
            install_guide = 'Please ensure the required command is installed and accessible.'
        
        error_message = f'Failed to start {platform} logging. {install_guide} Error: {str(e)}'
        socketio.emit('log', {'platform': 'system', 'message': error_message})
        return error_message, 500

@app.route('/stop-log', methods=['POST'])
def stop_log():
    """
    停止日志收集
    
    终止当前运行的日志收集进程，包括主日志进程和可能的 grep 过滤进程。
    同时清理相关的线程资源，并通知前端日志收集已停止。
    
    返回:
        str: 操作结果消息
        - 成功: 'Logging processes stopped successfully.' (HTTP 200)
        - 失败: 'No logging process was running.' (HTTP 200)
    
    清理流程:
        1. 设置日志收集状态为非活跃
        2. 立即通知前端状态变更
        3. 等待所有相关线程结束
        4. 终止 grep 过滤进程（如果存在）
        5. 终止主日志收集进程
        6. 清理进程和线程资源
    """
    global log_process, grep_process, logging_active, log_threads
    
    # 设置日志收集状态为非活跃，停止日志流处理
    logging_active = False
    
    # 立即向前端发送状态更新
    socketio.emit('logging_status', {'active': False})
    
    stopped_processes = []
    
    # 等待所有日志处理线程结束
    for thread in log_threads:
        if thread.is_alive():
            try:
                thread.join(timeout=1)  # 最多等待1秒让每个线程结束
                if thread.is_alive():
                    stopped_processes.append('thread (timeout)')
                else:
                    stopped_processes.append('thread')
            except Exception as e:
                socketio.emit('log', {'platform': 'system', 'message': f'Error stopping thread: {str(e)}'})
    
    # 清空线程列表
    log_threads.clear()
    
    # 首先停止 grep 过滤进程（如果存在）
    if grep_process and grep_process.poll() is None:
        try:
            grep_process.terminate()  # 发送终止信号
            try:
                grep_process.wait(timeout=2)  # 等待进程优雅退出
                stopped_processes.append('grep filter')
            except subprocess.TimeoutExpired:
                grep_process.kill()  # 强制杀死进程
                grep_process.wait()
                stopped_processes.append('grep filter (force killed)')
        except Exception as e:
            socketio.emit('log', {'platform': 'system', 'message': f'Error stopping grep process: {str(e)}'})
        finally:
            grep_process = None
    
    # 停止主日志收集进程
    if log_process and log_process.poll() is None:
        try:
            log_process.terminate()  # 发送终止信号
            try:
                log_process.wait(timeout=2)  # 等待进程优雅退出
                stopped_processes.append('log collection')
            except subprocess.TimeoutExpired:
                log_process.kill()  # 强制杀死进程
                log_process.wait()
                stopped_processes.append('log collection (force killed)')
        except Exception as e:
            socketio.emit('log', {'platform': 'system', 'message': f'Error stopping log process: {str(e)}'})
        finally:
            log_process = None
    
    # 根据停止的进程数量返回相应的消息
    if stopped_processes:
        message = f"Stopped: {', '.join(stopped_processes)}"
        socketio.emit('log', {'platform': 'system', 'message': message})
        return 'Logging processes stopped successfully.', 200
    else:
        socketio.emit('log', {'platform': 'system', 'message': 'No active logging processes found.'})
        return 'No logging process was running.', 200

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """
    处理客户端连接事件
    
    当新的客户端连接到WebSocket服务器时触发此函数。
    主要功能是记录连接信息并向新连接的客户端发送当前的日志收集状态。
    
    功能:
        1. 记录客户端连接信息（包含会话ID）
        2. 向新连接的客户端发送当前日志收集状态
    
    发送事件:
        - 'logging_status': 包含当前日志收集是否活跃的状态信息
    """
    print(f'Client connected: {request.sid}')  # 记录客户端连接，包含唯一会话ID
    # 向新连接的客户端发送当前日志收集状态
    emit('logging_status', {'active': logging_active})
    emit('log', {'platform': 'system', 'message': 'Connected to log server.'})

@socketio.on('disconnect')
def handle_disconnect():
    """
    处理客户端断开连接事件
    
    当客户端从WebSocket服务器断开连接时触发此函数。
    主要功能是记录断开连接的信息，用于调试和监控目的。
    
    功能:
        1. 记录客户端断开连接信息（包含会话ID）
    
    注意:
        客户端断开连接不会影响正在进行的日志收集进程，
        其他连接的客户端仍然可以继续接收日志数据。
    """
    print(f'Client disconnected: {request.sid}')  # 记录客户端断开连接，包含唯一会话ID

if __name__ == '__main__':
    """
    主程序入口
    
    当脚本直接运行时执行以下操作：
    1. 加载配置文件
    2. 启动Flask-SocketIO服务器
    
    服务器配置:
        - host: '0.0.0.0' - 监听所有网络接口，允许外部访问
        - port: PORT - 服务器端口（从环境变量或默认3000）
        - debug: False - 生产模式，禁用调试功能
    
    注意:
        在开发环境中可以将 debug 设置为 True
    """
    print(f'Log viewer server running on http://localhost:{PORT}')
    socketio.run(app, host='0.0.0.0', port=PORT, debug=False)