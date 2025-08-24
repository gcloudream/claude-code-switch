#!/bin/bash

# Claude Relay Station - 安装依赖并运行项目脚本
set -e  # 遇到错误立即退出

echo "============================================"
echo "Claude Relay Station - 安装与运行脚本"
echo "============================================"

# 检查Python版本
echo "检查Python版本..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3，请先安装Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ 发现Python版本: $PYTHON_VERSION"

# 检查pip
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "❌ 错误: 未找到pip，请先安装pip"
    exit 1
fi

# 创建虚拟环境（可选）
read -p "是否创建Python虚拟环境? (y/n): " create_venv
if [[ $create_venv == "y" || $create_venv == "Y" ]]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
fi

# 升级pip
echo "升级pip..."
python3 -m pip install --upgrade pip

# 安装依赖
echo "安装项目依赖..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ 依赖安装完成"
else
    echo "❌ 错误: 未找到requirements.txt文件"
    exit 1
fi

# 配置环境文件
echo "配置环境变量..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ 已复制.env.example到.env"
        echo "⚠️  请编辑.env文件，配置必要的环境变量:"
        echo "   - UPSTREAM_API_KEY: 你的Claude API密钥"
        echo "   - ADMIN_PASSWORD: 管理员密码"
        echo "   - SECRET_KEY: JWT密钥 (建议使用: openssl rand -hex 32)"
        echo "   - DATABASE_URL: PostgreSQL数据库连接"
        echo "   - REDIS_URL: Redis连接"
        read -p "按回车键继续..."
    else
        echo "❌ 错误: 未找到.env.example文件"
        exit 1
    fi
else
    echo "✅ .env文件已存在"
fi

# 检查数据库连接（可选）
echo "准备数据库..."
if command -v alembic &> /dev/null; then
    echo "运行数据库迁移..."
    alembic upgrade head
    echo "✅ 数据库迁移完成"
else
    echo "⚠️  警告: 未找到alembic，请确保已安装并配置数据库"
fi

# 创建启动脚本
cat > start.sh << 'EOF'
#!/bin/bash
# 启动服务器脚本

# 检查是否有虚拟环境
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

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
EOF

chmod +x start.sh

echo ""
echo "============================================"
echo "✅ 安装完成！"
echo "============================================"
echo ""
echo "快速启动:"
echo "  ./start.sh"
echo ""
echo "手动启动:"
echo "  python3 run.py"
echo ""
echo "开发模式启动:"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "服务地址:"
echo "  - 主页: http://localhost:8000"
echo "  - 管理面板: http://localhost:8000/admin"
echo "  - API文档: http://localhost:8000/docs"
echo "  - 健康检查: http://localhost:8000/health"
echo "  - 监控指标: http://localhost:8000/metrics"
echo ""
echo "重要提醒:"
echo "1. 请确保已配置.env文件中的必要参数"
echo "2. 确保PostgreSQL和Redis服务正在运行"
echo "3. 首次运行前请执行数据库迁移: alembic upgrade head"
echo ""

# 询问是否立即启动
read -p "是否立即启动服务? (y/n): " start_now
if [[ $start_now == "y" || $start_now == "Y" ]]; then
    echo "正在启动服务..."
    ./start.sh
fi