# 配置验证功能说明

## 功能概述

本项目已升级支持对JSON格式的行为数据进行格式验证，提供了完整的配置验证体系，包括：

- ✅ 多种数据类型支持（text, json, number, boolean, regex）
- ✅ JSON Schema 验证
- ✅ 实时配置验证
- ✅ 前后端双重验证
- ✅ 详细的错误提示

## 新增功能

### 1. 数据类型支持

现在支持以下数据类型：

- **text**: 文本类型（默认）
- **json**: JSON格式数据，支持Schema验证
- **number**: 数字类型，支持范围验证
- **boolean**: 布尔类型
- **regex**: 正则表达式类型

### 2. JSON Schema 验证

对于 `dataType: "json"` 的行为，可以定义详细的JSON Schema进行数据验证：

```json
{
  "name": "用户行为数据",
  "dataType": "json",
  "validation": {
    "schema": {
      "type": "object",
      "properties": {
        "action": {
          "type": "string",
          "enum": ["click", "scroll", "input"]
        },
        "timestamp": {
          "type": "number"
        }
      },
      "required": ["action", "timestamp"]
    }
  }
}
```

### 3. 实时配置验证

前端配置编辑器现在支持：

- 🔴 **红色边框**: 配置验证失败
- 🟠 **橙色边框**: JSON语法错误
- 🟢 **绿色边框**: 配置验证通过
- 📝 **错误提示**: 详细的验证错误信息

### 4. 数据提取和验证

支持从日志中提取结构化数据并进行验证：

```json
{
  "extractors": [
    {
      "name": "userData",
      "pattern": "UserData: (\\{.*\\})",
      "group": 1,
      "dataType": "json"
    }
  ]
}
```

## 使用方法

### 1. 配置行为数据类型

在行为配置中添加 `dataType` 字段：

```json
{
  "name": "API响应",
  "pattern": "API Response: (\\{.*\\})",
  "dataType": "json",
  "validation": {
    "schema": {
      "type": "object",
      "properties": {
        "status": {"type": "string"},
        "code": {"type": "number"}
      }
    }
  }
}
```

### 2. 配置数字验证

```json
{
  "name": "CPU使用率",
  "pattern": "CPU: (\\d+)%",
  "dataType": "number",
  "validation": {
    "min": 0,
    "max": 100
  }
}
```

### 3. 配置文本长度验证

```json
{
  "name": "用户名",
  "pattern": "Username: (\\w+)",
  "dataType": "text",
  "validation": {
    "minLength": 3,
    "maxLength": 20
  }
}
```

## 验证流程

### 前端验证

1. **实时语法检查**: 输入时检查JSON语法
2. **结构验证**: 检查配置结构完整性
3. **字段验证**: 验证必需字段和数据类型
4. **正则表达式验证**: 检查正则表达式语法

### 后端验证

1. **配置保存验证**: 保存时进行完整验证
2. **Schema验证**: 根据config_schema.json验证
3. **运行时验证**: 日志处理时验证提取的数据
4. **错误报告**: 详细的验证错误信息

## 错误处理

### 配置错误

- 显示具体的错误位置和原因
- 提供修复建议
- 阻止保存无效配置

### 运行时错误

- 记录验证失败的日志
- 继续处理其他有效配置
- 通过WebSocket发送错误通知

## 配置文件结构

```
├── config.json              # 主配置文件
├── config_schema.json       # 配置Schema定义
├── config_examples.md       # 配置示例文档
└── CONFIG_VALIDATION.md     # 本说明文档
```

## API 变更

### 新增响应字段

`behavior_triggered` 事件现在包含：

```json
{
  "behavior": {...},
  "log": "原始日志消息",
  "extractedData": {
    "fieldName": {
      "raw": "原始值",
      "parsed": "解析后的值"
    }
  },
  "validationResults": {
    "isValid": true,
    "parsedData": {...},
    "error": null,
    "dataType": "json"
  },
  "platform": "android",
  "timestamp": 1234567890
}
```

## 依赖更新

### Python依赖

```bash
pip install jsonschema
```

### 新增文件

- `config_schema.json`: 配置Schema定义
- `config_examples.md`: 配置示例和文档
- `CONFIG_VALIDATION.md`: 功能说明文档

## 兼容性

- ✅ 向后兼容现有配置
- ✅ 新字段为可选字段
- ✅ 默认行为保持不变
- ✅ 渐进式升级支持

## 测试建议

1. **基础功能测试**: 确保现有配置正常工作
2. **JSON验证测试**: 测试JSON Schema验证功能
3. **错误处理测试**: 测试各种错误情况
4. **性能测试**: 验证验证功能对性能的影响

## 故障排除

### 常见问题

1. **配置保存失败**
   - 检查JSON语法
   - 验证必需字段
   - 查看错误提示

2. **验证不生效**
   - 确认dataType字段设置
   - 检查validation规则
   - 查看系统日志

3. **正则表达式错误**
   - 注意转义字符
   - 使用在线工具测试
   - 参考示例配置

### 调试模式

启用详细日志记录：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 更新历史

- **v2.0.0**: 初始版本，支持基础JSON验证
- **v2.1.0**: 添加多种数据类型支持
- **v2.2.0**: 增加实时验证功能
- **v2.3.0**: 完善错误处理和文档