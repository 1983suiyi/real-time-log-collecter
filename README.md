# Real-time Log Viewer

一个实时的移动设备日志查看器，支持Android、iOS和HarmonyOS设备的日志收集、过滤和行为分析。

## 功能特性

### 📱 多平台支持
- **Android设备**: 通过 `adb logcat` 获取实时日志
- **iOS设备**: 通过 `idevicesyslog` 获取实时日志
- **HarmonyOS设备**: 通过 `hdc hilog` 获取实时日志

### 🔍 日志过滤
- **标签过滤**: 支持按指定标签过滤日志内容
- **模糊匹配**: 使用grep进行灵活的日志内容匹配
- **实时过滤**: 在日志收集过程中实时应用过滤规则

### 🎯 行为分析
- **配置化规则**: 通过JSON配置文件定义监控行为
- **正则表达式**: 支持复杂的日志模式匹配
- **实时触发**: 当检测到指定行为时立即通知
- **行为分类**: 支持不同级别的行为分类（如critical、info等）

### 🌐 Web界面
- **实时显示**: 通过WebSocket实时显示日志内容
- **双窗口布局**: 分别显示原始日志和触发的行为
- **配置管理**: 通过Web界面直接编辑和管理行为配置
- **滚动控制**: 智能的自动滚动和手动滚动控制

### ⚙️ 配置管理
- **Web配置**: 通过浏览器界面管理配置
- **实时更新**: 配置更改立即生效，无需重启服务
- **JSON格式**: 直观的JSON配置格式
- **配置验证**: 自动验证配置格式的正确性

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
2. **设置过滤标签** (可选): 在标签输入框中输入要过滤的关键词
3. **开始日志收集**: 点击 "Start Logging" 按钮
4. **查看日志**: 实时日志将显示在左侧窗口
5. **查看行为触发**: 检测到的行为将显示在右侧窗口
6. **停止日志收集**: 点击 "Stop Logging" 按钮

### 配置管理

1. **打开配置管理**: 点击 "Manage Config" 按钮
2. **编辑配置**: 在弹出的文本框中编辑JSON配置
3. **保存配置**: 点击 "Save Configuration" 保存更改
4. **重新加载配置**: 点击 "Reload Config" 重新加载配置文件

### 配置文件格式

```json
{
  "behaviors": [
    {
      "name": "Application Crash",
      "pattern": "fatal|exception|error",
      "description": "检测应用程序崩溃或严重错误",
      "level": "critical"
    },
    {
      "name": "User Login",
      "pattern": "User successfully logged in",
      "description": "跟踪用户登录事件",
      "level": "info"
    }
  ]
}
```

#### 配置字段说明
- `name`: 行为名称
- `pattern`: 正则表达式模式
- `description`: 行为描述
- `level`: 行为级别 (如: critical, warning, info)

## API接口

### 日志控制
- `POST /start-log`: 开始日志收集
  ```json
  {
    "platform": "android|ios|harmonyos",
    "tag": "optional_filter_tag"
  }
  ```

- `POST /stop-log`: 停止日志收集

### 配置管理
- `GET /config`: 获取当前配置
- `POST /config`: 更新配置
- `POST /reload-config`: 重新加载配置文件

### WebSocket事件
- `log`: 接收日志消息
- `behavior_triggered`: 接收行为触发通知

## 项目结构

```
macos_clean/
├── server.py              # Python服务器主文件
├── server.js              # Node.js服务器 (已弃用)
├── requirements.txt       # Python依赖
├── config.json           # 行为配置文件
├── public/               # 前端文件
│   ├── index.html        # 主页面
│   ├── main.js          # JavaScript逻辑
│   └── style.css        # 样式文件
└── README.md            # 项目文档
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

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

## 更新日志

### v2.0.0
- 重构服务器端为Python
- 添加配置管理Web界面
- 改进行为分析功能
- 优化WebSocket通信

### v1.0.0
- 初始版本
- 支持Android、iOS和HarmonyOS日志收集
- 基本的标签过滤功能
- 简单的Web界面