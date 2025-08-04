# HarmonyOS 工具目录

此目录用于存放HarmonyOS开发所需的工具，特别是hdc（HarmonyOS Device Connector）工具。

## 如何添加hdc工具

### 方法1: 使用自动安装脚本（推荐）
```bash
./setup_hdc.sh
```

### 方法2: 手动复制toolchains目录
1. 从HarmonyOS SDK中获取完整的toolchains目录
   - 通常位于DevEco Studio安装目录下的SDK文件夹中
   - 例如：`/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains`
   - 或：`~/Library/Huawei/Sdk/openharmony/[version]/toolchains`

2. 复制整个toolchains目录到此目录
   ```bash
   cp -r /path/to/toolchains ./
   ```

3. 确保hdc文件有执行权限
   ```bash
   chmod +x ./toolchains/hdc
   ```

### 为什么需要整个toolchains目录？
- hdc工具依赖其他库文件（如libusb_shared.dylib）
- 完整的toolchains目录确保所有依赖都可用
- 避免运行时的链接错误

## 支持的平台

请确保添加对应操作系统的hdc版本：

- **macOS**: 复制macOS版本的hdc
- **Linux**: 复制Linux版本的hdc
- **Windows**: 复制Windows版本的hdc.exe

## 验证

添加完成后，可以通过以下命令验证工具是否正常工作：

```bash
./hdc --version
```

## 注意事项

- hdc工具版本应与目标HarmonyOS设备兼容
- 不同操作系统需要使用对应的二进制版本
- 此目录中的工具仅用于开发和测试，不应包含在生产环境中