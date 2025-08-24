#!/bin/bash
# 启动服务器脚本

# 设置环境变量
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "启动Claude Relay Station服务器..."
echo "服务器地址: http://localhost:${PORT:-8000}"
echo "管理面板: http://localhost:${PORT:-8000}/admin"
echo "按 Ctrl+C 停止服务器"
echo "=========================================="

# 启动服务器
python3 run.py