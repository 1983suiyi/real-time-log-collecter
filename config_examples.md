# 配置示例和帮助文档

## 概述

本文档提供了日志行为配置的详细说明和示例，帮助您创建和验证配置文件。

## 配置结构

配置文件采用JSON格式，主要包含以下部分：

```json
{
  "behaviors": [
    // 行为配置数组
  ],
  "globalSettings": {
    // 全局设置
  }
}
```

## 行为配置字段说明

### 基础字段

- **name** (必需): 行为名称，用于标识该行为
- **description** (可选): 行为描述
- **pattern** (必需): 正则表达式模式，用于匹配日志消息
- **level** (可选): 日志级别 (info, warning, error)
- **enabled** (可选): 是否启用该行为，默认为 true

### 数据类型和验证

- **dataType** (可选): 数据类型，支持以下值：
  - `text`: 文本类型（默认）
  - `json`: JSON格式数据
  - `number`: 数字类型
  - `boolean`: 布尔类型
  - `regex`: 正则表达式类型

- **validation** (可选): 验证规则，根据数据类型不同而不同

### 数据提取器

- **extractors** (可选): 数据提取器数组，用于从日志中提取结构化数据

## 配置示例

### 1. 基础文本匹配

```json
{
  "name": "会话开启",
  "description": "检测用户会话开始",
  "pattern": "Session started for user (\\w+)",
  "level": "info",
  "dataType": "text"
}
```

### 2. JSON数据验证

```json
{
  "name": "用户行为数据",
  "description": "捕获和验证用户行为的JSON数据",
  "pattern": "UserAction: (\\{.*\\})",
  "level": "info",
  "dataType": "json",
  "validation": {
    "schema": {
      "type": "object",
      "properties": {
        "action": {
          "type": "string",
          "enum": ["click", "scroll", "input", "navigate"]
        },
        "timestamp": {
          "type": "number"
        },
        "element": {
          "type": "string"
        }
      },
      "required": ["action", "timestamp"]
    }
  },
  "extractors": [
    {
      "name": "actionData",
      "pattern": "UserAction: (\\{.*\\})",
      "group": 1,
      "dataType": "json"
    }
  ]
}
```

### 3. 数字类型验证

```json
{
  "name": "性能指标",
  "description": "监控性能指标数值",
  "pattern": "Performance: CPU usage (\\d+(?:\\.\\d+)?)%",
  "level": "warning",
  "dataType": "number",
  "validation": {
    "min": 0,
    "max": 100
  },
  "extractors": [
    {
      "name": "cpuUsage",
      "pattern": "CPU usage (\\d+(?:\\.\\d+)?)%",
      "group": 1,
      "dataType": "number"
    }
  ]
}
```

### 4. 布尔类型验证

```json
{
  "name": "错误状态",
  "description": "检测系统错误状态",
  "pattern": "System error: (true|false)",
  "level": "error",
  "dataType": "boolean",
  "extractors": [
    {
      "name": "hasError",
      "pattern": "System error: (true|false)",
      "group": 1,
      "dataType": "boolean"
    }
  ]
}
```

### 5. 复杂配置示例

```json
{
  "name": "API请求监控",
  "description": "监控API请求的详细信息",
  "pattern": "API Request: (\\{.*\\})",
  "level": "info",
  "dataType": "json",
  "validation": {
    "schema": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "enum": ["GET", "POST", "PUT", "DELETE"]
        },
        "url": {
          "type": "string",
          "pattern": "^https?://"
        },
        "statusCode": {
          "type": "number",
          "minimum": 100,
          "maximum": 599
        },
        "responseTime": {
          "type": "number",
          "minimum": 0
        }
      },
      "required": ["method", "url", "statusCode"]
    }
  },
  "extractors": [
    {
      "name": "requestData",
      "pattern": "API Request: (\\{.*\\})",
      "group": 1,
      "dataType": "json"
    },
    {
      "name": "method",
      "pattern": "\"method\":\"(\\w+)\"",
      "group": 1,
      "dataType": "text"
    },
    {
      "name": "statusCode",
      "pattern": "\"statusCode\":(\\d+)",
      "group": 1,
      "dataType": "number"
    }
  ],
  "triggers": [
    {
      "condition": "statusCode >= 400",
      "action": "alert",
      "message": "API请求失败"
    }
  ]
}
```

## 全局设置

```json
{
  "globalSettings": {
    "enableValidation": true,
    "strictMode": false,
    "maxLogBuffer": 1000,
    "defaultLevel": "info",
    "timestampFormat": "ISO8601"
  }
}
```

## JSON Schema 验证规则

当 `dataType` 为 `json` 时，可以使用 JSON Schema 进行数据验证：

### 基本类型

- `string`: 字符串类型
- `number`: 数字类型
- `integer`: 整数类型
- `boolean`: 布尔类型
- `array`: 数组类型
- `object`: 对象类型
- `null`: 空值类型

### 验证关键字

- `required`: 必需字段数组
- `properties`: 对象属性定义
- `enum`: 枚举值
- `pattern`: 正则表达式模式
- `minimum/maximum`: 数字范围
- `minLength/maxLength`: 字符串长度范围
- `minItems/maxItems`: 数组长度范围

## 常见错误和解决方案

### 1. 正则表达式错误

**错误**: `无效的正则表达式模式`

**解决方案**: 检查正则表达式语法，确保转义字符正确

```json
// 错误
"pattern": "User (\w+) logged in"

// 正确
"pattern": "User (\\w+) logged in"
```

### 2. JSON Schema 错误

**错误**: `无效的JSON Schema`

**解决方案**: 确保 schema 是有效的 JSON Schema 格式

```json
// 错误
"schema": {
  "type": "object",
  "properties": {
    "name": "string"  // 错误：应该是对象
  }
}

// 正确
"schema": {
  "type": "object",
  "properties": {
    "name": {
      "type": "string"
    }
  }
}
```

### 3. 数据类型不匹配

**错误**: `数据类型验证失败`

**解决方案**: 确保提取的数据与指定的数据类型匹配

## 最佳实践

1. **使用描述性的名称**: 为行为和提取器使用清晰、描述性的名称
2. **合理使用验证**: 只在需要时使用验证规则，避免过度复杂化
3. **测试正则表达式**: 在配置前测试正则表达式模式
4. **渐进式配置**: 从简单配置开始，逐步添加复杂功能
5. **文档化配置**: 为复杂配置添加详细的描述

## 调试技巧

1. **使用系统日志**: 查看系统日志中的验证错误信息
2. **实时验证**: 利用前端的实时验证功能检查配置
3. **分步测试**: 先测试基本匹配，再添加验证规则
4. **日志样本**: 准备典型的日志样本进行测试

## 更新日志

- v2.0: 添加了JSON数据验证支持
- v2.1: 增加了多种数据类型支持
- v2.2: 添加了实时配置验证功能