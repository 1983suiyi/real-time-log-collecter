# Elasticsearch搜索集成测试指南

## 功能概述

已成功实现Elasticsearch日志搜索功能，包含以下特性：

### 1. 前端界面
- ✅ 在控制面板中添加了Elasticsearch搜索表单
- ✅ 包含索引名称、用户ID、开始时间、结束时间输入字段
- ✅ 搜索和停止按钮
- ✅ 默认时间范围设置为最近24小时

### 2. 后端API
- ✅ `/api/es/search` - 启动Elasticsearch搜索
- ✅ `/api/es/search/stop` - 停止搜索
- ✅ 参数验证和错误处理
- ✅ 调用Python搜索服务

### 3. Python搜索服务
- ✅ `es_search_service.py` - 核心搜索逻辑
- ✅ `es_search_cli.py` - 命令行接口
- ✅ 支持实时进度更新
- ✅ 行为分析集成

### 4. 实时通信
- ✅ WebSocket集成
- ✅ 搜索进度实时推送
- ✅ 搜索结果实时显示
- ✅ 系统消息推送

## 测试步骤

### 1. 启动服务器
```bash
npm start
```

### 2. 访问界面
打开浏览器访问: http://localhost:3000

### 3. 使用Elasticsearch搜索
1. 在"Elasticsearch搜索"部分填写搜索条件：
   - 索引名称: `app-logs-*` (或其他存在的索引)
   - 用户ID: 具体的用户ID
   - 开始时间: 选择开始时间
   - 结束时间: 选择结束时间

2. 点击"搜索日志"按钮

3. 观察日志容器中的搜索结果和行为分析

### 4. 命令行测试
```bash
# 测试CLI工具
python3 ep_py/es_search_cli.py --help

# 运行搜索测试 (需要实际的Elasticsearch服务)
python3 ep_py/es_search_cli.py \
  --index "app-logs-*" \
  --user_id "test_user" \
  --start_time "2024-01-01T00:00:00" \
  --end_time "2024-01-02T00:00:00" \
  --mode cli
```

## 配置说明

### Elasticsearch配置
配置文件: `config/es_search_config.yaml`
- 索引名称模式
- 查询参数配置
- 返回字段定义
- 搜索行为设置

### 行为分析配置
配置文件: `config.yaml`
- 行为规则定义
- 关键词匹配
- 模式识别逻辑

## 注意事项

1. **Elasticsearch连接**: 确保Elasticsearch服务可访问
2. **索引存在**: 确保指定的索引名称存在且有数据
3. **时间格式**: 使用ISO格式时间字符串
4. **用户ID**: 确保用户ID在日志中存在

## 错误处理

系统包含完整的错误处理机制：
- 参数验证错误
- Elasticsearch连接错误
- 查询构建错误
- 搜索结果解析错误

所有错误都会通过WebSocket实时推送到前端界面显示。