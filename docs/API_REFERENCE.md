# 实时日志收集器 API 参考文档

## 目录

1. [概述](#概述)
2. [WebSocket API](#websocket-api)
   - [客户端接收事件](#客户端接收事件)
   - [客户端发送事件](#客户端发送事件)
3. [HTTP API](#http-api)
   - [日志管理](#日志管理)
   - [配置管理](#配置管理)
   - [数据处理](#数据处理)
4. [数据模型](#数据模型)
   - [日志数据](#日志数据)
   - [行为数据](#行为数据)
   - [配置数据](#配置数据)
5. [错误处理](#错误处理)
   - [错误代码](#错误代码)
   - [错误响应格式](#错误响应格式)
6. [使用示例](#使用示例)
   - [JavaScript 客户端示例](#javascript-客户端示例)
   - [Python 客户端示例](#python-客户端示例)
   - [Curl 命令示例](#curl-命令示例)

## 概述

实时日志收集器提供了两种类型的API接口：

1. **WebSocket API**：用于实时数据传输，包括日志流、行为触发和状态更新
2. **HTTP API**：用于控制和配置系统，包括启动/停止日志收集、配置管理等

所有API都通过同一服务器提供，默认端口为3000。

## WebSocket API

### 连接URL

```
ws://localhost:3000/socket.io/
```

### 客户端接收事件

#### 1. `log_data`

接收实时日志数据。

**数据格式**：
```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "info",
  "tag": "AppTag",
  "message": "日志消息内容",
  "platform": "android"
}
```

**字段说明**：
- `timestamp`: ISO 8601格式的时间戳
- `level`: 日志级别 (debug, info, warn, error, critical)
- `tag`: 日志标签
- `message`: 日志消息内容
- `platform`: 日志来源平台 (android, ios, harmonyos)

#### 2. `behavior_triggered`

接收行为触发事件。

**数据格式**：
```json
{
  "behavior": "用户行为数据",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "extracted_data": {
    "userBehaviorData": {
      "userId": "user123",
      "action": "click",
      "timestamp": 1704110400000
    }
  },
  "validation_result": {
    "valid": true,
    "errors": []
  },
  "level": "info"
}
```

**字段说明**：
- `behavior`: 触发的行为名称
- `timestamp`: ISO 8601格式的时间戳
- `extracted_data`: 提取的数据对象，键为提取器名称
- `validation_result`: 验证结果
  - `valid`: 是否验证通过
  - `errors`: 验证错误信息数组
- `level`: 行为级别

#### 3. `status_update`

接收状态更新。

**数据格式**：
```json
{
  "status": "active",
  "platform": "android",
  "filter_tag": "AppTag",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

**字段说明**：
- `status`: 当前状态 (active, inactive)
- `platform`: 当前平台 (android, ios, harmonyos)
- `filter_tag`: 当前过滤标签
- `timestamp`: ISO 8601格式的时间戳

#### 4. `validation_result`

接收数据验证结果。

**数据格式**：
```json
{
  "valid": true,
  "errors": [],
  "data": {}
}
```

**字段说明**：
- `valid`: 是否验证通过
- `errors`: 验证错误信息数组
- `data`: 验证的数据对象

#### 5. `event_order_violation`

接收事件顺序违规通知。

**数据格式**：
```json
{
  "current_event": "用户信息获取",
  "missing_event": "主页加载",
  "expected_sequence": ["登录", "主页加载", "用户信息获取"],
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

**字段说明**：
- `current_event`: 当前触发的事件
- `missing_event`: 缺失的事件
- `expected_sequence`: 预期的事件顺序
- `timestamp`: ISO 8601格式的时间戳

### 客户端发送事件

#### 1. `connect`

连接到WebSocket服务器。

**无需参数**

#### 2. `disconnect`

断开与WebSocket服务器的连接。

**无需参数**

## HTTP API

### 日志管理

#### 1. 开始日志收集

**请求**：
- **URL**: `/start_log`
- **方法**: `POST`
- **内容类型**: `application/json`

**请求参数**：
```json
{
  "platform": "android",
  "tag": "AppTag"
}
```

**参数说明**：
- `platform`: 平台 (android, ios, harmonyos)，必填
- `tag`: 过滤标签，可选

**响应**：
```json
{
  "status": "success",
  "message": "日志收集已启动"
}
```

#### 2. 停止日志收集

**请求**：
- **URL**: `/stop_log`
- **方法**: `POST`
- **内容类型**: `application/json`

**无需请求参数**

**响应**：
```json
{
  "status": "success",
  "message": "日志收集已停止"
}
```

### 配置管理

#### 1. 获取当前配置

**请求**：
- **URL**: `/config`
- **方法**: `GET`

**无需请求参数**

**响应**：
```json
{
  "behaviors": [...],
  "globalSettings": {...},
  "event_order": [...]
}
```

#### 2. 更新配置

**请求**：
- **URL**: `/config`
- **方法**: `POST`
- **内容类型**: `application/json`

**请求参数**：完整的配置对象
```json
{
  "behaviors": [...],
  "globalSettings": {...},
  "event_order": [...]
}
```

**响应**：
```json
{
  "status": "success",
  "message": "配置已更新",
  "validation": {
    "valid": true,
    "errors": []
  }
}
```

#### 3. 重新加载配置文件

**请求**：
- **URL**: `/reload_config`
- **方法**: `POST`

**无需请求参数**

**响应**：
```json
{
  "status": "success",
  "message": "配置已重新加载"
}
```

#### 4. 验证配置

**请求**：
- **URL**: `/validate_config`
- **方法**: `POST`
- **内容类型**: `application/json`

**请求参数**：要验证的配置对象
```json
{
  "behaviors": [...],
  "globalSettings": {...},
  "event_order": [...]
}
```

**响应**：
```json
{
  "valid": true,
  "errors": []
}
```

### 数据处理

#### 1. 手动触发数据提取

**请求**：
- **URL**: `/extract_data`
- **方法**: `POST`
- **内容类型**: `application/json`

**请求参数**：
```json
{
  "log_line": "user_behavior: {\"userId\":\"user123\",\"action\":\"click\",\"timestamp\":1704110400000}",
  "extractor_pattern": "user_behavior:\\s*({.*})",
  "data_type": "json"
}
```

**参数说明**：
- `log_line`: 日志行
- `extractor_pattern`: 提取器模式
- `data_type`: 数据类型 (text, json, number, boolean)

**响应**：提取的数据对象
```json
{
  "userId": "user123",
  "action": "click",
  "timestamp": 1704110400000
}
```

#### 2. 验证提取的数据

**请求**：
- **URL**: `/validate_data`
- **方法**: `POST`
- **内容类型**: `application/json`

**请求参数**：
```json
{
  "data": {
    "userId": "user123",
    "action": "click",
    "timestamp": 1704110400000
  },
  "validation_rules": {
    "jsonSchema": {
      "type": "object",
      "properties": {
        "userId": {"type": "string"},
        "action": {"type": "string"},
        "timestamp": {"type": "number"}
      },
      "required": ["userId", "action", "timestamp"]
    }
  }
}
```

**参数说明**：
- `data`: 要验证的数据
- `validation_rules`: 验证规则

**响应**：
```json
{
  "valid": true,
  "errors": []
}
```

## 数据模型

### 日志数据

```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "info",
  "tag": "AppTag",
  "message": "日志消息内容",
  "platform": "android"
}
```

### 行为数据

```json
{
  "name": "用户行为数据",
  "description": "检测用户行为JSON数据",
  "level": "info",
  "pattern": ".*user_behavior.*",
  "dataType": "json",
  "validation": {
    "required": true,
    "jsonSchema": {
      "type": "object",
      "properties": {
        "userId": {"type": "string"},
        "action": {"type": "string"},
        "timestamp": {"type": "number"}
      },
      "required": ["userId", "action", "timestamp"]
    }
  },
  "extractors": [
    {
      "name": "userBehaviorData",
      "pattern": "user_behavior:\\s*({.*})",
      "dataType": "json"
    }
  ],
  "enabled": true,
  "priority": 8
}
```

### 配置数据

```json
{
  "behaviors": [
    {
      "name": "用户行为数据",
      "description": "检测用户行为JSON数据",
      "level": "info",
      "pattern": ".*user_behavior.*",
      "dataType": "json",
      "validation": {...},
      "extractors": [...],
      "enabled": true,
      "priority": 8
    }
  ],
  "globalSettings": {
    "maxLogHistory": 1000,
    "enableRealTimeValidation": true,
    "validationTimeout": 5000
  },
  "event_order": [
    ["登录", "主页加载", "用户信息获取"],
    ["视频播放", "广告展示"]
  ]
}
```

## 错误处理

### 错误代码

| 错误代码 | 描述 | HTTP状态码 |
|---------|------|----------|
| E001 | 设备连接失败 | 500 |
| E002 | 配置解析错误 | 400 |
| E003 | 验证规则错误 | 400 |
| E004 | 提取数据失败 | 400 |
| E005 | 日志进程异常退出 | 500 |

### 错误响应格式

```json
{
  "status": "error",
  "error": {
    "code": "E001",
    "message": "设备连接失败",
    "details": "无法连接到Android设备，请检查USB连接"
  }
}
```

## 使用示例

### JavaScript 客户端示例

```javascript
// 连接WebSocket
const socket = io('http://localhost:3000');

// 接收日志数据
socket.on('log_data', (data) => {
  console.log('收到日志:', data);
});

// 接收行为触发
socket.on('behavior_triggered', (data) => {
  console.log('行为触发:', data);
});

// 接收状态更新
socket.on('status_update', (data) => {
  console.log('状态更新:', data);
});

// 开始日志收集
async function startLogging() {
  const response = await fetch('http://localhost:3000/start_log', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      platform: 'android',
      tag: 'AppTag'
    })
  });
  const result = await response.json();
  console.log(result);
}

// 停止日志收集
async function stopLogging() {
  const response = await fetch('http://localhost:3000/stop_log', {
    method: 'POST'
  });
  const result = await response.json();
  console.log(result);
}
```

### Python 客户端示例

```python
import requests
import socketio

# 创建Socket.IO客户端
sio = socketio.Client()

# 连接到服务器
sio.connect('http://localhost:3000')

# 注册事件处理函数
@sio.on('log_data')
def on_log_data(data):
    print('收到日志:', data)

@sio.on('behavior_triggered')
def on_behavior_triggered(data):
    print('行为触发:', data)

@sio.on('status_update')
def on_status_update(data):
    print('状态更新:', data)

# 开始日志收集
def start_logging():
    response = requests.post(
        'http://localhost:3000/start_log',
        json={
            'platform': 'android',
            'tag': 'AppTag'
        }
    )
    print(response.json())

# 停止日志收集
def stop_logging():
    response = requests.post('http://localhost:3000/stop_log')
    print(response.json())

# 使用示例
start_logging()
# ... 等待一段时间 ...
stop_logging()
sio.disconnect()
```

### Curl 命令示例

```bash
# 开始日志收集
curl -X POST http://localhost:3000/start_log \
  -H "Content-Type: application/json" \
  -d '{"platform":"android","tag":"AppTag"}'

# 停止日志收集
curl -X POST http://localhost:3000/stop_log

# 获取当前配置
curl -X GET http://localhost:3000/config

# 重新加载配置
curl -X POST http://localhost:3000/reload_config
```