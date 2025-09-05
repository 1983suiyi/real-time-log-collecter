# 实时日志收集器配置指南

## 目录

1. [配置概述](#配置概述)
2. [配置文件格式](#配置文件格式)
3. [行为配置](#行为配置)
   - [基本字段](#基本字段)
   - [数据提取器](#数据提取器)
   - [数据验证](#数据验证)
4. [全局设置](#全局设置)
5. [事件顺序规则](#事件顺序规则)
6. [配置示例](#配置示例)
   - [基础配置](#基础配置)
   - [高级配置](#高级配置)
7. [配置管理](#配置管理)
   - [通过Web界面管理](#通过web界面管理)
   - [通过API管理](#通过api管理)
   - [通过文件管理](#通过文件管理)
8. [配置验证](#配置验证)
   - [验证规则](#验证规则)
   - [常见错误](#常见错误)
9. [最佳实践](#最佳实践)

## 配置概述

实时日志收集器使用YAML格式的配置文件来定义行为模式、数据提取和验证规则。配置文件主要包含三个部分：

1. **behaviors**: 行为模式定义数组
2. **globalSettings**: 全局设置
3. **event_order**: 事件顺序规则

配置文件默认位置为项目根目录下的`config.yaml`。

## 配置文件格式

配置文件使用YAML格式，基本结构如下：

```yaml
behaviors:  # 行为定义数组
  - name: "行为名称"  # 第一个行为
    description: "行为描述"
    # 其他行为属性...
  
  - name: "另一个行为"  # 第二个行为
    # 其他行为属性...

globalSettings:  # 全局设置
  maxLogHistory: 1000
  # 其他全局设置...

event_order:  # 事件顺序规则
  - ["事件1", "事件2", "事件3"]  # 第一组顺序规则
  - ["事件4", "事件5"]  # 第二组顺序规则
```

## 行为配置

行为配置定义了系统如何识别、提取和验证日志中的特定模式。

### 基本字段

| 字段 | 类型 | 描述 | 必填 | 默认值 |
|------|------|------|------|--------|
| name | 字符串 | 行为名称 | 是 | - |
| description | 字符串 | 行为描述 | 否 | "" |
| level | 字符串 | 行为级别 | 是 | "info" |
| pattern | 字符串 | 正则表达式模式 | 是 | - |
| dataType | 字符串 | 数据类型 | 是 | "text" |
| extractors | 数组 | 数据提取器配置 | 否 | [] |
| validation | 对象 | 数据验证规则 | 否 | {} |
| enabled | 布尔值 | 是否启用该行为 | 是 | true |
| priority | 整数 | 行为优先级 (1-10) | 是 | 5 |

#### level 可选值

- **critical**: 严重错误或关键事件
- **error**: 错误
- **warning**: 警告
- **info**: 信息
- **debug**: 调试信息

#### dataType 可选值

- **text**: 文本数据
- **json**: JSON格式数据
- **number**: 数值数据
- **boolean**: 布尔值数据

### 数据提取器

数据提取器用于从匹配的日志行中提取特定数据。

```yaml
extractors:
  - name: "提取器名称"  # 提取器名称，用于标识提取的数据
    pattern: "提取正则表达式"  # 提取数据的正则表达式，必须包含一个捕获组
    dataType: "json"  # 提取数据的类型：text, json, number, boolean
```

#### 提取器示例

1. **提取JSON数据**:
```yaml
extractors:
  - name: "userBehaviorData"
    pattern: "user_behavior:\s*({.*})"
    dataType: "json"
```

2. **提取数值**:
```yaml
extractors:
  - name: "fpsValue"
    pattern: "fps:\s*(\d+)"
    dataType: "number"
```

3. **提取布尔值**:
```yaml
extractors:
  - name: "errorState"
    pattern: "error_state:\s*(true|false)"
    dataType: "boolean"
```

4. **提取文本**:
```yaml
extractors:
  - name: "userName"
    pattern: "user:\s*([\w-]+)"
    dataType: "text"
```

### 数据验证

数据验证用于验证提取的数据是否符合预期格式和规则。

```yaml
validation:
  required: true  # 是否必须验证通过
  jsonSchema: {}  # JSON Schema验证规则
  numberRange: {}  # 数字范围验证
  stringLength: {}  # 字符串长度验证
```

#### 验证规则示例

1. **JSON Schema验证**:
```yaml
validation:
  required: true
  jsonSchema:
    type: "object"
    properties:
      userId: {"type": "string"}
      action: {"type": "string"}
      timestamp: {"type": "number"}
    required: ["userId", "action", "timestamp"]
```

2. **数字范围验证**:
```yaml
validation:
  numberRange:
    min: 0
    max: 120
```

3. **字符串长度验证**:
```yaml
validation:
  stringLength:
    min: 3
    max: 50
```

## 全局设置

全局设置用于配置系统的整体行为。

```yaml
globalSettings:
  maxLogHistory: 1000  # 最大日志历史记录数
  enableRealTimeValidation: true  # 启用实时验证
  validationTimeout: 5000  # 验证超时时间（毫秒）
```

| 字段 | 类型 | 描述 | 默认值 |
|------|------|------|--------|
| maxLogHistory | 整数 | 最大日志历史记录数 | 1000 |
| enableRealTimeValidation | 布尔值 | 启用实时验证 | true |
| validationTimeout | 整数 | 验证超时时间（毫秒） | 5000 |

## 事件顺序规则

事件顺序规则用于定义事件必须按特定顺序触发的规则。

```yaml
event_order:
  - ["事件1", "事件2", "事件3"]  # 第一组顺序规则
  - ["事件4", "事件5"]  # 第二组顺序规则
```

每个子数组定义一个必须按顺序触发的事件序列。如果事件触发顺序不符合规则，系统将发送`event_order_violation`事件。

## 配置示例

### 基础配置

```yaml
behaviors:
  - name: "SDK 初始化成功"
    description: "SDK 初始化成功"
    level: "info"
    pattern: ".*installSuccess.*"
    dataType: "text"
    enabled: true
    priority: 5

  - name: "TGA 会话开启"
    description: "TGA 会话开启"
    level: "info"
    pattern: ".*thinking game TGTrace eventname:session_start.*"
    dataType: "text"
    enabled: true
    priority: 5

  - name: "TGA 会话关闭"
    description: "TGA 会话关闭"
    level: "info"
    pattern: ".*thinking game TGTrace eventname:session_end.*"
    dataType: "text"
    enabled: true
    priority: 5

globalSettings:
  maxLogHistory: 1000
  enableRealTimeValidation: true
  validationTimeout: 5000

event_order:
  - ["SDK 初始化成功", "TGA 会话开启", "TGA 会话关闭"]
```

### 高级配置

```yaml
behaviors:
  - name: "用户行为数据"
    description: "检测用户行为JSON数据"
    level: "info"
    pattern: ".*user_behavior.*"
    dataType: "json"
    validation:
      required: true
      jsonSchema:
        type: "object"
        properties:
          userId: {"type": "string"}
          action: {"type": "string"}
          timestamp: {"type": "number"}
          data: {"type": "object"}
        required: ["userId", "action", "timestamp"]
    extractors:
      - name: "userBehaviorData"
        pattern: "user_behavior:\\s*({.*})"
        dataType: "json"
    enabled: true
    priority: 8

  - name: "性能指标"
    description: "检测性能相关的数值数据"
    level: "warn"
    pattern: ".*performance.*fps:\\s*(\\d+)"
    dataType: "number"
    validation:
      numberRange:
        min: 0
        max: 120
    extractors:
      - name: "fpsValue"
        pattern: "fps:\\s*(\\d+)"
        dataType: "number"
    enabled: true
    priority: 7

  - name: "错误状态"
    description: "检测错误状态的布尔值"
    level: "error"
    pattern: ".*error_state:\\s*(true|false)"
    dataType: "boolean"
    extractors:
      - name: "errorState"
        pattern: "error_state:\\s*(true|false)"
        dataType: "boolean"
    enabled: true
    priority: 9

globalSettings:
  maxLogHistory: 1000
  enableRealTimeValidation: true
  validationTimeout: 5000

event_order:
  - ["SDK 初始化成功", "TGA 会话关闭", "BI 会话结束"]
```

## 配置管理

### 通过Web界面管理

1. 点击Web界面上的"Reload Config"按钮重新加载配置文件
2. 点击"Load YAML Config"按钮上传新的配置文件

### 通过API管理

1. **获取当前配置**:
```bash
curl -X GET http://localhost:3000/config
```

2. **更新配置**:
```bash
curl -X POST http://localhost:3000/config \
  -H "Content-Type: application/json" \
  -d '{"behaviors":[...],"globalSettings":{...},"event_order":[...]}
```

3. **重新加载配置文件**:
```bash
curl -X POST http://localhost:3000/reload_config
```

### 通过文件管理

1. 直接编辑项目根目录下的`config.yaml`文件
2. 重启服务器或使用"Reload Config"按钮重新加载配置

## 配置验证

系统会在加载配置时自动验证配置格式和内容。

### 验证规则

1. **YAML语法验证**: 确保配置文件符合YAML语法
2. **结构验证**: 确保配置包含必要的字段和正确的数据类型
3. **正则表达式验证**: 确保行为模式和提取器模式是有效的正则表达式
4. **JSON Schema验证**: 确保JSON Schema验证规则是有效的

### 常见错误

1. **YAML语法错误**:
   - 缩进不一致
   - 缺少冒号
   - 引号不匹配

2. **结构错误**:
   - 缺少必要字段
   - 字段类型错误
   - 数组格式错误

3. **正则表达式错误**:
   - 语法错误
   - 捕获组缺失
   - 过于复杂导致性能问题

4. **JSON Schema错误**:
   - 格式错误
   - 引用不存在的字段
   - 类型不匹配

## 最佳实践

1. **行为命名**:
   - 使用简洁明了的名称
   - 避免使用特殊字符
   - 保持一致的命名风格

2. **正则表达式**:
   - 尽量使用简单的正则表达式
   - 避免使用过于通用的模式
   - 测试正则表达式匹配效果

3. **数据提取**:
   - 为每个提取器指定明确的名称
   - 确保捕获组能准确提取所需数据
   - 根据数据类型选择合适的提取方式

4. **数据验证**:
   - 为重要数据添加验证规则
   - 设置合理的验证范围
   - 避免过于严格的验证规则

5. **事件顺序**:
   - 只定义关键事件的顺序
   - 避免过于复杂的顺序规则
   - 确保事件名称与行为名称一致

6. **性能考虑**:
   - 控制行为数量
   - 优化正则表达式
   - 调整`maxLogHistory`和`validationTimeout`参数