# 实时日志收集器系统使用手册

## 目录

1. [系统概述](#系统概述)
2. [系统架构](#系统架构)
3. [安装部署](#安装部署)
   - [系统要求](#系统要求)
   - [安装步骤](#安装步骤)
   - [启动服务](#启动服务)
4. [使用指南](#使用指南)
   - [基本操作](#基本操作)
   - [日志收集](#日志收集)
   - [日志过滤](#日志过滤)
   - [行为分析](#行为分析)
   - [导出功能](#导出功能)
5. [配置管理](#配置管理)
   - [配置文件格式](#配置文件格式)
   - [配置字段说明](#配置字段说明)
   - [配置示例](#配置示例)
6. [API接口](#api接口)
   - [WebSocket事件](#websocket-事件)
   - [HTTP接口](#http-接口)
7. [故障排除](#故障排除)
   - [常见问题](#常见问题)
   - [错误代码](#错误代码)
8. [开发指南](#开发指南)
   - [项目结构](#项目结构)
   - [开发环境设置](#开发环境设置)
9. [更新日志](#更新日志)

## 系统概述

实时日志收集器是一个功能强大的多平台日志收集和分析工具，专为移动应用开发和测试人员设计。系统支持Android、iOS和HarmonyOS平台，提供实时日志流收集、智能过滤、行为分析和数据验证等功能，通过直观的Web界面帮助开发者快速定位问题和分析应用行为。

### 主要功能特性

- **多平台支持**：同时支持Android、iOS和HarmonyOS设备日志收集
- **日志过滤**：支持基于标签和关键词的精确过滤，包括特殊字符和表情符号
- **行为分析**：基于配置的行为模式检测，支持数据提取和验证
- **Web界面**：直观的双窗口布局，实时显示日志和行为触发
- **配置管理**：灵活的JSON配置，支持实时验证和热重载
- **多行日志合并**：智能识别和合并多行日志条目
- **事件顺序检查**：监控并验证事件触发顺序

## 系统架构

实时日志收集器采用前后端分离架构：

- **后端**：基于Python的Flask框架，负责日志收集、处理和分析
- **前端**：基于HTML/CSS/JavaScript的Web界面，通过WebSocket实时通信
- **数据流**：设备日志 → 日志收集器 → 行为分析 → WebSocket → 前端显示

### 技术栈

#### 后端
- **Python 3.x**：主要编程语言
- **Flask**：Web框架
- **Flask-SocketIO**：WebSocket实时通信
- **正则表达式**：日志模式匹配和数据提取
- **JSON Schema**：配置和数据验证

#### 前端
- **HTML5**：页面结构
- **CSS3**：样式设计
- **JavaScript (ES6+)**：交互逻辑
- **Socket.IO**：客户端WebSocket通信

#### 外部工具
- **adb**：Android调试桥（Android日志收集）
- **idevicesyslog**：iOS设备日志收集
- **hdc**：HarmonyOS调试工具
- **grep**：日志过滤（支持固定字符串匹配）

## 安装部署

### 系统要求

- **操作系统**：支持macOS、Linux和Windows
- **Python**：3.7+
- **浏览器**：Chrome、Firefox、Safari或Edge最新版本
- **设备支持**：
  - **Android**：需安装Android SDK (adb)
  - **iOS**：需安装libimobiledevice (idevicesyslog)
  - **HarmonyOS**：需安装DevEco Studio (hdc)

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd real-time-log-collecter
```

#### 2. 安装Python依赖

```bash
pip3 install -r requirements.txt
```

#### 3. 平台特定工具安装

##### Android

```bash
# macOS (使用Homebrew)
brew install android-platform-tools

# Linux
sudo apt-get install adb

# Windows
# 下载Android SDK并添加platform-tools到PATH
```

##### iOS

```bash
# macOS (使用Homebrew)
brew install libimobiledevice

# Linux
sudo apt-get install libimobiledevice-utils

# Windows
# 不直接支持，需使用WSL或虚拟机
```

##### HarmonyOS

```bash
# 安装DevEco Studio，并确保hdc在PATH中
```

### 启动服务

```bash
python3 server.py
```

服务器默认在端口3000上启动。如需修改端口，可设置环境变量：

```bash
PORT=8080 python3 server.py
```

启动后，打开浏览器访问：http://localhost:3000

## 使用指南

### 基本操作

1. **选择平台**：在下拉菜单中选择Android、iOS或HarmonyOS
2. **设置过滤标签**（可选）：在标签输入框中输入要过滤的关键词
3. **开始日志收集**：点击"Start Logging"按钮
4. **查看日志**：实时日志将显示在左侧窗口
5. **查看行为触发**：检测到的行为将显示在右侧窗口
6. **停止日志收集**：点击"Stop Logging"按钮
7. **清理日志**：点击"Clear Logs"按钮清理所有日志窗口内容
8. **查看状态**：顶部状态栏实时显示日志收集状态

### 日志收集

#### Android设备

1. 确保设备已开启USB调试模式
2. 使用USB线连接设备到电脑
3. 运行`adb devices`确认设备已连接
4. 在Web界面选择"Android"平台
5. 点击"Start Logging"开始收集日志

#### iOS设备

1. 确保已安装libimobiledevice
2. 使用USB线连接设备到电脑
3. 确保设备已信任此电脑
4. 在Web界面选择"iOS"平台
5. 点击"Start Logging"开始收集日志

#### HarmonyOS设备

1. 确保已安装DevEco Studio和hdc工具
2. 使用USB线连接设备到电脑
3. 运行`hdc list targets`确认设备已连接
4. 在Web界面选择"HarmonyOS"平台
5. 点击"Start Logging"开始收集日志

### 日志过滤

系统支持两种过滤方式：

1. **标签过滤**：在"Filter Tag"输入框中输入标签名称
   - 支持特殊字符和表情符号
   - 区分大小写
   - 支持多个标签（用逗号分隔）

2. **关键词过滤**：在配置中设置行为模式的正则表达式

### 行为分析

行为分析基于配置文件中定义的行为模式：

1. 系统实时匹配日志与配置的行为模式
2. 匹配成功时，提取指定数据并进行验证
3. 验证结果和提取的数据显示在右侧窗口
4. 支持事件顺序检查，确保事件按预期顺序触发

### 导出功能

系统支持将日志和分析结果导出为多种格式：

1. **导出日志**：点击"Export Logs"按钮
   - CSV格式：包含时间戳、级别、标签和消息
   - HTML报告：格式化的HTML报告，包含样式和过滤功能

2. **导出行为分析**：点击"Export Behaviors"按钮
   - JSON格式：包含所有行为触发记录和提取的数据
   - HTML报告：可视化的行为分析报告

## 配置管理

### 配置文件格式

配置文件使用YAML格式，定义行为模式、数据提取和验证规则：

```yaml
behaviors:
  - name: "行为名称"
    description: "行为描述"
    level: "info"  # 级别：critical, error, warning, info, debug
    pattern: "正则表达式模式"
    dataType: "json"  # 数据类型：text, json, number, boolean
    validation: {}  # 验证规则
    extractors: []  # 数据提取器
    enabled: true  # 是否启用
    priority: 5  # 优先级（1-10）

globalSettings:
  maxLogHistory: 1000
  enableRealTimeValidation: true
  validationTimeout: 5000

event_order:
  - ["事件1", "事件2", "事件3"]  # 必须按此顺序触发
  - ["事件4", "事件5"]  # 另一组顺序规则
```

### 配置字段说明

#### 行为配置

- **name**：行为名称（必填）
- **pattern**：正则表达式模式（必填）
- **description**：行为描述
- **level**：行为级别（critical, error, warning, info, debug）
- **dataType**：数据类型（text, json, number, boolean）
- **validation**：数据验证规则
  - **jsonSchema**：JSON Schema验证规则
  - **numberRange**：数字范围验证
  - **stringLength**：字符串长度验证
  - **required**：是否必须验证通过
- **extractors**：数据提取器配置
  - **name**：提取器名称
  - **pattern**：提取正则表达式
  - **dataType**：提取数据类型
- **enabled**：是否启用该行为
- **priority**：行为优先级（1-10）

#### 全局设置

- **maxLogHistory**：最大日志历史记录数
- **enableRealTimeValidation**：启用实时验证
- **validationTimeout**：验证超时时间（毫秒）

#### 事件顺序规则

- **event_order**：事件顺序规则数组
  - 每个子数组定义一个必须按顺序触发的事件序列

### 配置示例

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

globalSettings:
  maxLogHistory: 1000
  enableRealTimeValidation: true
  validationTimeout: 5000

event_order:
  - ["登录", "主页加载", "用户信息获取"]
  - ["视频播放", "广告展示"]
```

## API接口

### WebSocket事件

#### 客户端接收事件

- **log_data**：接收实时日志数据
  ```json
  {
    "timestamp": "2024-01-01T12:00:00.000Z",
    "level": "info",
    "tag": "AppTag",
    "message": "日志消息内容"
  }
  ```

- **behavior_triggered**：接收行为触发事件
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
    }
  }
  ```

- **status_update**：接收状态更新
  ```json
  {
    "status": "active",
    "platform": "android",
    "filter_tag": "AppTag",
    "timestamp": "2024-01-01T12:00:00.000Z"
  }
  ```

- **validation_result**：接收数据验证结果
  ```json
  {
    "valid": true,
    "errors": [],
    "data": {}
  }
  ```

- **event_order_violation**：接收事件顺序违规通知
  ```json
  {
    "current_event": "用户信息获取",
    "missing_event": "主页加载",
    "expected_sequence": ["登录", "主页加载", "用户信息获取"],
    "timestamp": "2024-01-01T12:00:00.000Z"
  }
  ```

### HTTP接口

#### 日志管理

- **POST /start_log**：开始日志收集
  - 参数：
    - `platform`：平台（android/ios/harmonyos）
    - `tag`：过滤标签（可选）
  - 返回：
    ```json
    {
      "status": "success",
      "message": "日志收集已启动"
    }
    ```

- **POST /stop_log**：停止日志收集
  - 返回：
    ```json
    {
      "status": "success",
      "message": "日志收集已停止"
    }
    ```

#### 配置管理

- **GET /config**：获取当前配置
  - 返回：当前配置的JSON对象

- **POST /config**：更新配置
  - 参数：新的配置JSON对象
  - 返回：
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

- **POST /reload_config**：重新加载配置文件
  - 返回：
    ```json
    {
      "status": "success",
      "message": "配置已重新加载"
    }
    ```

- **POST /validate_config**：验证配置
  - 参数：要验证的配置JSON对象
  - 返回：
    ```json
    {
      "valid": true,
      "errors": []
    }
    ```

#### 数据处理

- **POST /extract_data**：手动触发数据提取
  - 参数：
    - `log_line`：日志行
    - `extractor_pattern`：提取器模式
    - `data_type`：数据类型
  - 返回：提取的数据对象

- **POST /validate_data**：验证提取的数据
  - 参数：
    - `data`：要验证的数据
    - `validation_rules`：验证规则
  - 返回：
    ```json
    {
      "valid": true,
      "errors": []
    }
    ```

## 故障排除

### 常见问题

#### 1. Android设备无法连接

**症状**：选择Android平台后无法收集日志

**解决方案**：
- 确保设备已开启USB调试模式
- 检查`adb devices`命令是否能看到设备
- 尝试重新连接USB线
- 确认设备已授权允许调试
- 尝试重启adb服务：`adb kill-server && adb start-server`

#### 2. iOS设备无法连接

**症状**：选择iOS平台后无法收集日志

**解决方案**：
- 确保已安装libimobiledevice
- 检查`idevicesyslog`命令是否可用
- 确保设备已信任此电脑
- 尝试重新连接USB线
- 检查设备是否已解锁

#### 3. HarmonyOS设备无法连接

**症状**：选择HarmonyOS平台后无法收集日志

**解决方案**：
- 确保已安装DevEco Studio和hdc工具
- 检查`hdc list targets`命令是否能看到设备
- 确保设备已开启调试模式
- 尝试重新连接USB线

#### 4. 配置保存失败

**症状**：点击"Save Configuration"按钮后出现错误

**解决方案**：
- 检查JSON格式是否正确
- 确保配置文件有写入权限
- 查看浏览器控制台是否有错误信息
- 检查服务器日志是否有相关错误

#### 5. WebSocket连接失败

**症状**：页面加载后无法接收实时日志

**解决方案**：
- 检查防火墙设置
- 确认端口3000未被占用
- 尝试刷新浏览器页面
- 检查浏览器控制台是否有WebSocket错误
- 重启服务器

### 错误代码

| 错误代码 | 描述 | 解决方案 |
|---------|------|--------|
| E001 | 设备连接失败 | 检查设备连接和调试模式 |
| E002 | 配置解析错误 | 检查配置文件格式 |
| E003 | 验证规则错误 | 检查验证规则语法 |
| E004 | WebSocket连接断开 | 刷新页面或重启服务器 |
| E005 | 日志进程异常退出 | 检查设备连接和系统日志 |

## 开发指南

### 项目结构

```
real-time-log-collecter/
├── server.py              # Flask后端服务器
├── config.yaml            # 行为配置文件
├── public/
│   ├── index.html         # 前端页面
│   ├── main.js            # 前端JavaScript逻辑
│   └── style.css          # 样式文件
├── docs/                  # 文档目录
│   ├── API.md             # API接口文档
│   ├── CONFIG.md          # 配置说明文档
│   ├── USER_MANUAL.md     # 用户手册（本文档）
│   └── CHANGELOG.md       # 更新日志
├── requirements.txt       # Python依赖
└── README.md              # 项目文档
```

### 开发环境设置

```bash
# 克隆项目
git clone <repository-url>
cd real-time-log-collecter

# 安装开发依赖
pip3 install -r requirements.txt

# 启动开发服务器
python3 server.py
```

## 更新日志

### v2.0.0 (2024-12-XX)
- ✨ **多行日志合并**：智能识别和合并Android多行日志条目
- ✨ **特殊字符过滤**：支持表情符号和特殊字符的精确匹配过滤
- ✨ **数据提取和验证**：支持JSON、数字、布尔值等数据类型的提取和验证
- ✨ **实时配置验证**：JSON配置实时语法检查和错误提示
- ✨ **日志清理功能**：一键清理所有日志窗口内容
- ✨ **事件顺序检查**：监控并验证事件触发顺序，确保符合预定义规则
- ✨ **状态指示器**：实时显示日志收集状态
- 🔧 **优化**：改进WebSocket通信性能和稳定性
- 🔧 **优化**：增强用户界面交互体验

### v1.0.0 (2024-01-XX)
- 🎉 初始版本发布
- ✅ 支持Android、iOS、HarmonyOS日志收集
- ✅ 基本的行为检测功能
- ✅ Web界面管理
- ✅ 配置文件管理
- ✅ 实时日志显示