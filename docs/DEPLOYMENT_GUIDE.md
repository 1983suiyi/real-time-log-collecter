# 实时日志收集器部署指南

## 目录

1. [系统要求](#系统要求)
2. [安装步骤](#安装步骤)
   - [基础环境准备](#基础环境准备)
   - [项目安装](#项目安装)
   - [平台特定工具安装](#平台特定工具安装)
3. [配置说明](#配置说明)
   - [服务器配置](#服务器配置)
   - [行为配置](#行为配置)
   - [配置文件示例](#配置文件示例)
4. [启动与运行](#启动与运行)
   - [启动服务器](#启动服务器)
   - [访问Web界面](#访问web界面)
   - [服务管理](#服务管理)
5. [生产环境部署](#生产环境部署)
   - [使用Gunicorn](#使用gunicorn)
   - [使用Supervisor](#使用supervisor)
   - [使用Docker](#使用docker)
6. [安全性考虑](#安全性考虑)
7. [性能优化](#性能优化)
8. [故障排除](#故障排除)

## 系统要求

### 硬件要求

- **CPU**: 双核处理器或更高
- **内存**: 最低2GB RAM，推荐4GB或更高
- **存储**: 最低500MB可用空间
- **网络**: 稳定的网络连接

### 软件要求

- **操作系统**:
  - Linux (Ubuntu 18.04+, CentOS 7+)
  - macOS 10.14+
  - Windows 10+

- **Python环境**:
  - Python 3.7+
  - pip 19.0+

- **浏览器**:
  - Chrome 80+
  - Firefox 75+
  - Safari 13+
  - Edge 80+

- **平台特定工具**:
  - Android: Android SDK (adb)
  - iOS: libimobiledevice (idevicesyslog)
  - HarmonyOS: DevEco Studio (hdc)

## 安装步骤

### 基础环境准备

#### 安装Python

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Linux (CentOS/RHEL)**:
```bash
sudo yum install python3 python3-pip
```

**macOS**:
```bash
brew install python3
```

**Windows**:
从[Python官网](https://www.python.org/downloads/)下载并安装Python 3.7+

#### 创建虚拟环境（推荐）

```bash
python3 -m venv venv
```

**激活虚拟环境**:

- Linux/macOS:
```bash
source venv/bin/activate
```

- Windows:
```bash
venv\Scripts\activate
```

### 项目安装

#### 1. 克隆项目

```bash
git clone <repository-url>
cd real-time-log-collecter
```

#### 2. 安装Python依赖

```bash
pip3 install -r requirements.txt
```

依赖包括：
- Flask==2.3.3 - Web框架
- Werkzeug==2.3.7 - WSGI工具库
- Flask-SocketIO==5.3.6 - WebSocket支持
- python-socketio==5.8.0 - Socket.IO库
- python-engineio==4.7.1 - Socket.IO引擎
- Flask-CORS==4.0.0 - 跨域资源共享
- PyYAML==6.0.1 - YAML配置解析

### 平台特定工具安装

#### Android

**Linux (Ubuntu/Debian)**:
```bash
sudo apt install android-tools-adb
```

**Linux (CentOS/RHEL)**:
```bash
sudo yum install android-tools
```

**macOS**:
```bash
brew install android-platform-tools
```

**Windows**:
1. 下载[Android SDK Platform Tools](https://developer.android.com/studio/releases/platform-tools)
2. 解压并添加到PATH环境变量

#### iOS

**macOS**:
```bash
brew install libimobiledevice
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt install libimobiledevice-utils
```

**Linux (CentOS/RHEL)**:
```bash
sudo yum install libimobiledevice
```

**Windows**:
不直接支持，需使用WSL或虚拟机

#### HarmonyOS

1. 下载并安装[DevEco Studio](https://developer.harmonyos.com/cn/develop/deveco-studio/)
2. 确保hdc工具在PATH环境变量中

## 配置说明

### 服务器配置

服务器配置主要通过环境变量和命令行参数进行设置：

| 环境变量 | 描述 | 默认值 |
|---------|------|--------|
| PORT | 服务器监听端口 | 3000 |
| HOST | 服务器监听地址 | 0.0.0.0 |
| DEBUG | 调试模式 | False |
| CONFIG_PATH | 配置文件路径 | config.yaml |

示例：
```bash
PORT=8080 DEBUG=True python3 server.py
```

### 行为配置

行为配置通过YAML文件定义，默认为`config.yaml`。配置文件包含以下主要部分：

1. **behaviors**: 行为模式定义数组
2. **globalSettings**: 全局设置
3. **event_order**: 事件顺序规则

#### 行为定义字段

| 字段 | 类型 | 描述 | 必填 |
|------|------|------|------|
| name | 字符串 | 行为名称 | 是 |
| description | 字符串 | 行为描述 | 否 |
| level | 字符串 | 行为级别 (critical, error, warning, info, debug) | 是 |
| pattern | 字符串 | 正则表达式模式 | 是 |
| dataType | 字符串 | 数据类型 (text, json, number, boolean) | 是 |
| validation | 对象 | 数据验证规则 | 否 |
| extractors | 数组 | 数据提取器配置 | 否 |
| enabled | 布尔值 | 是否启用该行为 | 是 |
| priority | 整数 | 行为优先级 (1-10) | 是 |

#### 全局设置字段

| 字段 | 类型 | 描述 | 默认值 |
|------|------|------|--------|
| maxLogHistory | 整数 | 最大日志历史记录数 | 1000 |
| enableRealTimeValidation | 布尔值 | 启用实时验证 | true |
| validationTimeout | 整数 | 验证超时时间（毫秒） | 5000 |

### 配置文件示例

```yaml
behaviors:
  - name: "SDK 初始化成功"
    description: "SDK 初始化成功"
    level: "info"
    pattern: ".*installSuccess.*"
    dataType: "text"
    enabled: true
    priority: 5

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

globalSettings:
  maxLogHistory: 1000
  enableRealTimeValidation: true
  validationTimeout: 5000

event_order:
  - ["SDK 初始化成功", "TGA 会话关闭", "BI 会话结束"]
```

## 启动与运行

### 启动服务器

#### 基本启动

```bash
python3 server.py
```

#### 指定端口启动

```bash
PORT=8080 python3 server.py
```

#### 调试模式启动

```bash
DEBUG=True python3 server.py
```

#### 指定配置文件启动

```bash
CONFIG_PATH=/path/to/custom-config.yaml python3 server.py
```

### 访问Web界面

启动服务器后，打开浏览器访问：

```
http://localhost:3000
```

如果指定了其他端口，请相应调整URL。

### 服务管理

#### 停止服务

在终端按 `Ctrl+C` 停止服务。

## 生产环境部署

### 使用Gunicorn

Gunicorn是一个Python WSGI HTTP服务器，适合生产环境部署。

#### 安装Gunicorn

```bash
pip install gunicorn
```

#### 启动服务

```bash
gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:3000 server:app
```

注意：必须使用eventlet worker类来支持WebSocket。

### 使用Supervisor

Supervisor是一个进程控制系统，可以用来管理服务进程。

#### 安装Supervisor

```bash
# Ubuntu/Debian
sudo apt install supervisor

# CentOS/RHEL
sudo yum install supervisor
```

#### 配置Supervisor

创建配置文件 `/etc/supervisor/conf.d/log-collector.conf`：

```ini
[program:log-collector]
command=/path/to/venv/bin/gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:3000 server:app
directory=/path/to/real-time-log-collecter
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/log-collector/stdout.log
stderr_logfile=/var/log/log-collector/stderr.log
environment=PORT=3000,CONFIG_PATH=/path/to/config.yaml
```

#### 启动服务

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start log-collector
```

### 使用Docker

#### 创建Dockerfile

在项目根目录创建`Dockerfile`：

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装依赖
RUN apt-get update && apt-get install -y \
    android-tools-adb \
    libimobiledevice-utils \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn eventlet

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:3000", "server:app"]
```

#### 构建镜像

```bash
docker build -t log-collector .
```

#### 运行容器

```bash
docker run -d -p 3000:3000 --name log-collector log-collector
```

## 安全性考虑

### 1. 访问控制

默认情况下，服务器不包含身份验证机制。在生产环境中，建议：

- 使用反向代理（如Nginx）添加基本身份验证
- 限制IP访问范围
- 考虑添加OAuth或其他身份验证机制

### 2. HTTPS支持

为保护数据传输安全，建议配置HTTPS：

- 使用反向代理（如Nginx）配置SSL/TLS
- 获取并配置SSL证书（可使用Let's Encrypt）

### 3. 数据安全

- 定期备份配置文件
- 避免在日志中包含敏感信息
- 考虑添加日志数据加密功能

## 性能优化

### 1. 日志过滤优化

- 使用更精确的过滤标签减少处理数据量
- 调整`maxLogHistory`参数控制内存使用

### 2. WebSocket连接优化

- 在高负载环境中增加Gunicorn工作进程数
- 考虑使用Redis作为Socket.IO消息队列

### 3. 服务器资源优化

- 监控CPU和内存使用情况
- 根据需要调整服务器规格

## 故障排除

### 1. 服务器启动失败

**症状**：运行`python3 server.py`后出现错误

**可能原因和解决方案**：

- **端口被占用**：更改端口或停止占用端口的进程
  ```bash
  PORT=3001 python3 server.py
  ```

- **依赖缺失**：确保所有依赖已安装
  ```bash
  pip install -r requirements.txt
  ```

- **Python版本不兼容**：确保使用Python 3.7+
  ```bash
  python3 --version
  ```

### 2. 设备连接问题

**症状**：无法收集设备日志

**可能原因和解决方案**：

- **Android**：
  - 检查adb是否安装：`adb --version`
  - 检查设备连接：`adb devices`
  - 重启adb服务：`adb kill-server && adb start-server`

- **iOS**：
  - 检查libimobiledevice是否安装：`idevicesyslog --help`
  - 检查设备连接：`idevice_id -l`
  - 确保设备已信任此电脑

- **HarmonyOS**：
  - 检查hdc是否安装：`hdc --help`
  - 检查设备连接：`hdc list targets`

### 3. WebSocket连接问题

**症状**：Web界面无法接收实时日志

**可能原因和解决方案**：

- **浏览器兼容性**：尝试使用Chrome或Firefox
- **网络问题**：检查防火墙设置
- **服务器错误**：查看服务器日志
  ```bash
  DEBUG=True python3 server.py
  ```

### 4. 配置加载失败

**症状**：配置无法加载或验证失败

**可能原因和解决方案**：

- **YAML语法错误**：检查配置文件格式
- **文件权限问题**：确保配置文件有读取权限
- **配置路径错误**：指定正确的配置路径
  ```bash
  CONFIG_PATH=/correct/path/to/config.yaml python3 server.py
  ```