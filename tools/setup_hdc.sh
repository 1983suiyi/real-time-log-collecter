#!/bin/bash

# HarmonyOS hdc工具安装脚本
# 此脚本帮助用户将hdc工具复制到项目的tools目录中

set -e

echo "=== HarmonyOS hdc工具安装脚本 ==="
echo

# 获取当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="$SCRIPT_DIR"

# 常见的toolchains目录路径
POSSIBLE_PATHS=(
    "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains"
    "$HOME/Library/Huawei/Sdk/openharmony/*/toolchains"
    "/Applications/DevEco-Studio.app/Contents/sdk/openharmony/*/toolchains"
    "$HOME/harmonyos-sdk/*/toolchains"
    "/opt/harmonyos-sdk/*/toolchains"
)

echo "正在搜索toolchains目录..."
echo

TOOLCHAINS_FOUND=""

# 搜索toolchains目录
for pattern in "${POSSIBLE_PATHS[@]}"; do
    for path in $pattern; do
        if [[ -d "$path" && -f "$path/hdc" && -x "$path/hdc" ]]; then
            echo "找到toolchains目录: $path"
            TOOLCHAINS_FOUND="$path"
            break 2
        fi
    done
done

if [[ -z "$TOOLCHAINS_FOUND" ]]; then
    echo "❌ 未找到toolchains目录，请检查以下事项:"
    echo "   1. 是否已安装DevEco Studio或HarmonyOS SDK"
    echo "   2. SDK是否包含toolchains目录"
    echo "   3. 手动指定toolchains路径: $0 /path/to/toolchains"
    echo
    echo "如果您已安装SDK，请手动复制toolchains目录到tools目录:"
    echo "   cp -r /path/to/toolchains $TOOLS_DIR/"
    exit 1
fi

# 如果用户提供了自定义路径
if [[ $# -gt 0 ]]; then
    if [[ -d "$1" && -f "$1/hdc" && -x "$1/hdc" ]]; then
        TOOLCHAINS_FOUND="$1"
        echo "使用用户指定的toolchains路径: $TOOLCHAINS_FOUND"
    else
        echo "❌ 指定的路径无效或不包含可执行的hdc文件: $1"
        exit 1
    fi
fi

echo
echo "正在复制toolchains目录到tools目录..."

# 如果目标目录已存在，先删除
if [[ -d "$TOOLS_DIR/toolchains" ]]; then
    echo "删除现有的toolchains目录..."
    rm -rf "$TOOLS_DIR/toolchains"
fi

# 复制整个toolchains目录
cp -r "$TOOLCHAINS_FOUND" "$TOOLS_DIR/"

# 确保hdc可执行权限
chmod +x "$TOOLS_DIR/toolchains/hdc"

echo "✅ hdc工具安装完成!"
echo

# 验证安装
echo "验证安装..."
if "$TOOLS_DIR/toolchains/hdc" --version >/dev/null 2>&1; then
    echo "✅ hdc工具验证成功!"
    echo
    echo "版本信息:"
    "$TOOLS_DIR/toolchains/hdc" --version
else
    echo "❌ hdc工具验证失败，请检查工具是否正确"
    exit 1
fi

echo
echo "🎉 安装完成! 现在可以在日志查看器中使用HarmonyOS设备了。"
echo
echo "使用方法:"
echo "1. 连接HarmonyOS设备并开启USB调试"
echo "2. 在Web界面选择'HarmonyOS'平台"
echo "3. 点击'Start Logging'开始收集日志"