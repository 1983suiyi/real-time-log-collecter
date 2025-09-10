# Real-time Log Viewer

一个实时的移动设备日志查看器，支持Android、iOS和HarmonyOS设备的日志收集、过滤和行为分析。

## 功能特性

### 📱 多平台支持
- **Android设备**: 通过 `adb logcat` 获取实时日志
- **iOS设备**: 通过 `idevicesyslog` 获取实时日志
- **HarmonyOS设备**: 通过 `hdc hilog` 获取实时日志

### 🔍 日志过滤
- **标签过滤**: 支持按指定标签过滤日志内容
- **精确匹配**: 使用grep -F进行固定字符串匹配，支持特殊字符和表情符号
- **实时过滤**: 在日志收集过程中实时应用过滤规则
- **多行日志合并**: 智能识别Android日志格式，自动合并多行日志为完整条目

### 🎯 行为分析
- **配置化规则**: 通过JSON配置文件定义监控行为
- **正则表达式**: 支持复杂的日志模式匹配
- **数据提取**: 支持从日志中提取结构化数据（JSON、数字、布尔值等）
- **数据验证**: 内置数据类型验证和JSON Schema验证
- **验证错误提示**: 在行为日志中直观显示JSON Schema验证失败信息
- **实时触发**: 当检测到指定行为时立即通知
- **行为分类**: 支持不同级别的行为分类（如critical、info等）
- **优先级控制**: 支持行为优先级设置和启用/禁用控制
- **事件顺序检查**: 监控事件触发顺序，确保符合预定义的顺序规则

### 🌐 Web界面
- **实时显示**: 通过WebSocket实时显示日志内容
- **双窗口布局**: 分别显示原始日志和触发的行为
- **配置管理**: 通过Web界面直接编辑和管理行为配置
- **实时配置验证**: 输入时实时验证JSON配置格式和内容
- **滚动控制**: 智能的自动滚动和手动滚动检测
- **日志清理**: 一键清理所有日志窗口内容
- **状态指示**: 实时显示日志收集状态

### ⚙️ 配置管理
- **Web配置**: 通过浏览器界面管理配置
- **实时更新**: 配置更改立即生效，无需重启服务
- **JSON格式**: 直观的JSON配置格式
- **配置验证**: 自动验证配置格式和正则表达式的正确性
- **Schema验证**: 支持JSON Schema验证配置结构
- **错误提示**: 详细的配置错误提示和行号定位
- **实时验证**: 编辑时实时验证配置内容

## 技术栈

### 后端 (Python)
- **Flask**: Web框架
- **Flask-SocketIO**: WebSocket支持
- **Flask-CORS**: 跨域请求支持
- **subprocess**: 系统命令执行
- **threading**: 多线程日志处理

### 前端
- **HTML5**: 现代Web标准
- **CSS3**: 响应式设计
- **JavaScript**: 原生JavaScript
- **Socket.IO**: 实时通信

## 安装要求

### 系统要求
- Python 3.7+
- macOS (推荐) 或 Linux

### Android设备支持
- 安装 Android SDK Platform Tools
- 确保 `adb` 命令可用
- 设备开启USB调试模式

### iOS设备支持
- 安装 libimobiledevice:
  ```bash
  brew install libimobiledevice
  ```
- 确保 `idevicesyslog` 命令可用

### HarmonyOS设备支持

#### 方案1: 系统安装（推荐）
- 下载并安装 HarmonyOS SDK
- 确保 `hdc` (HarmonyOS Device Connector) 命令可用
- 设备开启开发者模式和USB调试

#### 方案2: 本地工具预制
- 运行自动安装脚本：
  ```bash
  ./tools/setup_hdc.sh
  ```
- 或手动复制hdc工具到tools目录：
  ```bash
  cp /path/to/hdc tools/
  chmod +x tools/hdc
  ```
- 设备开启开发者模式和USB调试

## 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd macos_clean
```

### 2. 安装Python依赖
```bash
pip3 install -r requirements.txt
```

### 3. 启动服务器
```bash
python3 server.py
```

### 4. 访问Web界面
打开浏览器访问: http://localhost:3000

## 使用说明

### 基本操作

1. **选择平台**: 在下拉菜单中选择 Android、iOS 或 HarmonyOS
2. **设置过滤标签** (可选): 在标签输入框中输入要过滤的关键词，支持特殊字符和表情符号
3. **开始日志收集**: 点击 "Start Logging" 按钮
4. **查看日志**: 实时日志将显示在左侧窗口，多行日志会自动合并为完整条目
5. **查看行为触发**: 检测到的行为将显示在右侧窗口，包含提取的数据和验证结果
6. **停止日志收集**: 点击 "Stop Logging" 按钮
7. **清理日志**: 点击 "Clear Logs" 按钮一键清理所有日志窗口内容
8. **查看状态**: 顶部状态栏实时显示日志收集状态

### 配置管理

1. **打开配置管理**: 点击 "Manage Config" 按钮
2. **编辑配置**: 在弹出的文本框中编辑JSON配置，支持实时语法验证
3. **查看验证结果**: 配置错误会实时显示在编辑器下方，包含详细错误信息
4. **保存配置**: 点击 "Save Configuration" 保存更改（仅在配置有效时可保存）
5. **重新加载配置**: 点击 "Reload Config" 重新加载配置文件

### JSON Schema验证错误提示

1. **错误高亮显示**: JSON Schema验证失败的行为日志会以红色边框高亮显示
2. **详细错误信息**: 验证失败的具体原因会在行为日志中清晰显示
3. **字段类型错误**: 当字段类型与Schema不匹配时（如app_id应为数字但提供了字符串），会显示具体的类型错误
4. **错误定位**: 错误信息会指明具体的字段路径和期望的数据类型
5. **视觉区分**: 验证错误消息使用特殊样式，便于与正常日志区分



### 配置文件格式

```json
{
  "behaviors": [
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
    },
    {
      "name": "性能指标",
      "description": "检测性能相关的数值数据",
      "level": "warn",
      "pattern": ".*performance.*fps:\\s*(\\d+)",
      "dataType": "number",
      "validation": {
        "numberRange": {
          "min": 0,
          "max": 120
        }
      },
      "extractors": [
        {
          "name": "fpsValue",
          "pattern": "fps:\\s*(\\d+)",
          "dataType": "number"
        }
      ],
      "enabled": true,
      "priority": 7
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

#### 配置字段说明
- `name`: 行为名称
- `pattern`: 正则表达式模式
- `description`: 行为描述
- `level`: 行为级别 (如: critical, warning, info)
- `dataType`: 数据类型 (text, json, number, boolean)
- `validation`: 数据验证规则
  - `jsonSchema`: JSON Schema验证规则
  - `numberRange`: 数字范围验证
  - `stringLength`: 字符串长度验证
- `extractors`: 数据提取器配置
  - `name`: 提取器名称
  - `pattern`: 提取正则表达式
  - `dataType`: 提取数据类型
- `enabled`: 是否启用该行为
- `priority`: 行为优先级 (1-10)
- `globalSettings`: 全局设置
  - `maxLogHistory`: 最大日志历史记录数
  - `enableRealTimeValidation`: 启用实时验证
  - `validationTimeout`: 验证超时时间
- `event_order`: 事件顺序规则数组，每个子数组定义一个必须按顺序触发的事件序列

## API接口

### WebSocket 事件

- `log_data`: 接收实时日志数据（包含合并后的完整日志条目）
- `behavior_triggered`: 接收行为触发事件（包含提取的数据和验证结果）
- `status_update`: 接收状态更新
- `validation_result`: 接收数据验证结果
- `event_order_violation`: 接收事件顺序违规通知（包含当前事件、缺失事件和预期顺序）

### HTTP 接口

#### 日志管理
- `POST /start_log`: 开始日志收集
  - 参数: `platform` (android/ios/harmonyos), `tag` (可选过滤标签)
- `POST /stop_log`: 停止日志收集

#### 配置管理
- `GET /config`: 获取当前配置
- `POST /config`: 更新配置（包含实时验证）
- `POST /reload_config`: 重新加载配置文件
- `POST /validate_config`: 验证配置格式和内容

#### 数据处理
- `POST /extract_data`: 手动触发数据提取
- `POST /validate_data`: 验证提取的数据



## 项目结构

```
real-time-log-collecter/
├── server.py              # Flask后端服务器（包含多行日志合并、数据验证等功能）
├── config.json            # 行为配置文件（支持数据提取和验证规则）
├── public/
│   ├── index.html         # 前端页面（双窗口布局、状态指示）
│   ├── main.js            # 前端JavaScript逻辑（实时验证、日志清理等）
│   └── style.css          # 样式文件
├── docs/                  # 文档目录
│   ├── API.md            # API接口文档
│   ├── CONFIG.md         # 配置说明文档
│   └── CHANGELOG.md      # 更新日志
├── requirements.txt       # Python依赖
└── README.md             # 项目文档（本文件）
```

## 故障排除

### 常见问题

1. **Android设备无法连接**
   - 确保设备已开启USB调试
   - 检查 `adb devices` 命令是否能看到设备
   - 尝试重新连接USB线

2. **iOS设备无法连接**
   - 确保已安装 libimobiledevice
   - 检查 `idevicesyslog` 命令是否可用
   - 确保设备已信任计算机

3. **配置保存失败**
   - 检查JSON格式是否正确
   - 确保配置文件有写入权限

4. **WebSocket连接失败**
   - 检查防火墙设置
   - 确认端口3000未被占用
   - 尝试刷新浏览器页面

## 开发说明

### 开发环境设置
```bash
# 安装开发依赖
pip3 install -r requirements.txt

# 启动开发服务器
python3 server.py
```

### 代码结构
- `server.py`: 主服务器逻辑，包含所有API端点和WebSocket处理
- `public/main.js`: 前端JavaScript，处理用户交互和WebSocket通信
- `public/style.css`: 界面样式，包含响应式设计

### JSON Schema验证实现

#### 后端实现

1. **验证库**: 使用`jsonschema`库进行JSON Schema验证
2. **Schema定义**: 在行为配置中定义每个事件的JSON Schema
3. **验证过程**: 当接收到行为日志时，根据事件类型选择对应的Schema进行验证
4. **错误处理**: 捕获验证异常，格式化错误信息并发送到前端

#### 前端实现

1. **错误显示**: 在行为日志面板中显示验证错误信息
2. **样式处理**: 使用CSS为验证失败的日志添加特殊样式
3. **用户交互**: 点击验证失败的日志可查看详细错误信息

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 技术栈

### 后端
- **Python 3.x**: 主要编程语言
- **Flask**: Web框架
- **Flask-SocketIO**: WebSocket实时通信
- **正则表达式**: 日志模式匹配和数据提取
- **JSON Schema**: 配置和数据验证

### 前端
- **HTML5**: 页面结构
- **CSS3**: 样式设计
- **JavaScript (ES6+)**: 交互逻辑
- **Socket.IO**: 客户端WebSocket通信


### 外部工具
- **adb**: Android调试桥（Android日志收集）
- **idevicesyslog**: iOS设备日志收集
- **hdc**: HarmonyOS调试工具
- **grep**: 日志过滤（支持固定字符串匹配）

## 系统要求

- Python 3.7+
- 对应平台的调试工具：
  - Android: Android SDK (adb)
  - iOS: libimobiledevice (idevicesyslog)
  - HarmonyOS: DevEco Studio (hdc)

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

### 开发指南
1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 更新 README.md（如有新功能）
5. 创建 Pull Request

## 许可证

MIT License

## 更新日志

### v2.0.0 (2024-12-XX)
- ✨ **多行日志合并**: 智能识别和合并Android多行日志条目
- ✨ **特殊字符过滤**: 支持表情符号和特殊字符的精确匹配过滤
- ✨ **数据提取和验证**: 支持JSON、数字、布尔值等数据类型的提取和验证
- ✨ **验证错误提示**: 在行为日志中直观显示JSON Schema验证失败信息
- ✨ **实时配置验证**: JSON配置实时语法检查和错误提示
- ✨ **日志清理功能**: 一键清理所有日志窗口内容
- ✨ **事件顺序检查**: 监控并验证事件触发顺序，确保符合预定义规则

- ✨ **状态指示器**: 实时显示日志收集状态
- 🔧 **优化**: 改进WebSocket通信性能和稳定性
- 🔧 **优化**: 增强用户界面交互体验

### v1.0.0 (2024-01-XX)
- 🎉 初始版本发布
- ✅ 支持 Android、iOS、HarmonyOS 日志收集
- ✅ 基本的行为检测功能
- ✅ Web 界面管理
- ✅ 配置文件管理
- ✅ 实时日志显示