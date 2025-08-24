# Claude Relay Station 项目结构与配置指南

## 📁 完整项目结构

```
claude-relay-station/
│
├── app/                          # 应用主目录
│   ├── __init__.py              # 包初始化
│   ├── main.py                  # FastAPI 主应用入口
│   │
│   ├── api/                     # API 端点
│   │   ├── __init__.py
│   │   ├── admin.py             # 管理员端点（密钥管理）
│   │   ├── usage.py             # 用户使用量查询端点
│   │   ├── proxy.py             # 代理转发端点
│   │   └── deps.py              # 依赖注入（认证、授权）
│   │
│   ├── core/                    # 核心功能
│   │   ├── __init__.py
│   │   ├── config.py            # 环境变量配置（Pydantic）
│   │   ├── yaml_config.py       # YAML 配置加载器
│   │   ├── security.py          # 安全工具（密钥哈希、JWT）
│   │   ├── logging.py           # 结构化日志（structlog）
│   │   └── metrics.py           # Prometheus 指标定义
│   │
│   ├── db/                      # 数据库
│   │   ├── __init__.py
│   │   └── base.py              # 数据库连接和会话管理
│   │
│   ├── models/                  # 数据模型（SQLAlchemy）
│   │   ├── __init__.py
│   │   ├── api_key.py           # API 密钥模型
│   │   └── usage_log.py         # 使用日志模型
│   │
│   ├── schemas/                 # Pydantic 模式（请求/响应验证）
│   │   ├── __init__.py
│   │   ├── api_key.py           # API 密钥相关模式
│   │   └── usage.py             # 使用量相关模式
│   │
│   ├── services/                # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── api_key_service.py   # API 密钥管理服务
│   │   ├── usage_log_service.py # 使用日志服务
│   │   ├── proxy_service.py     # 核心代理转发服务
│   │   └── token_counter.py     # 令牌计数服务
│   │
│   └── middleware/              # 中间件
│       ├── __init__.py
│       └── metrics.py           # 指标收集中间件
│
├── alembic/                     # 数据库迁移
│   ├── versions/                # 迁移版本文件
│   ├── env.py                   # Alembic 环境配置
│   └── script.py.mako           # 迁移脚本模板
│
├── logs/                        # 日志文件目录（运行时生成）
│
├── tests/                       # 测试文件（待实现）
│   ├── __init__.py
│   ├── test_api/
│   ├── test_services/
│   └── test_models/
│
├── .env                         # 环境变量（从 .env.example 复制）
├── .env.example                 # 环境变量模板
├── .gitignore                   # Git 忽略文件
├── alembic.ini                  # Alembic 配置
├── config.yaml                  # 应用配置文件
├── docker-compose.yml           # Docker Compose 编排
├── Dockerfile                   # Docker 镜像定义
├── prometheus.yml               # Prometheus 配置
├── pyproject.toml              # Python 项目配置
├── requirements.txt            # Python 依赖
├── run.py                      # 启动脚本
├── deploy.sh                   # 部署脚本
├── README.md                   # 项目说明文档
├── SETUP_GUIDE.md             # 配置指南
└── PROJECT_STRUCTURE.md       # 项目结构文档（本文件）
```

## 🔧 配置指南

### 1. 环境准备

#### 系统要求
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Docker & Docker Compose（可选但推荐）

#### 克隆项目
```bash
git clone <repository-url>
cd claude-relay-station
```

### 2. 配置文件说明

#### `.env` 文件（主要配置）

```env
# ==================== 核心配置 ====================

# 应用设置
APP_NAME=claude-relay-station
APP_ENV=development              # development | staging | production
DEBUG=true                       # 生产环境设为 false
LOG_LEVEL=INFO                   # DEBUG | INFO | WARNING | ERROR

# 服务器设置
HOST=0.0.0.0
PORT=8000

# ==================== 第三方 API 配置 ====================
# 这是你的真实 Anthropic API 配置
UPSTREAM_API_URL=https://api.anthropic.com/v1
UPSTREAM_API_KEY=sk-ant-api03-xxxxx  # ⚠️ 替换为你的真实 Anthropic API Key

# ==================== 数据库配置 ====================
DATABASE_URL=postgresql+asyncpg://relay_user:relay_password@localhost:5432/relay_station
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# ==================== Redis 配置 ====================
REDIS_URL=redis://localhost:6379/0
REDIS_POOL_SIZE=10

# ==================== 管理员配置 ====================
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password  # ⚠️ 设置强密码

# ==================== 安全配置 ====================
SECRET_KEY=your-secret-key-here     # ⚠️ 运行 openssl rand -hex 32 生成
TOKEN_EXPIRE_MINUTES=30

# ==================== 监控配置 ====================
ENABLE_METRICS=true
METRICS_PORT=9090
```

#### `config.yaml` 文件（高级配置）

```yaml
# 应用信息
app:
  name: claude-relay-station
  version: 0.1.0
  description: Claude Code API Relay Station

# 上游 API 配置
upstream:
  primary:
    name: "Anthropic Claude API"
    url: "${UPSTREAM_API_URL}"        # 从环境变量读取
    api_key: "${UPSTREAM_API_KEY}"    # 从环境变量读取
    timeout: 60                       # 超时时间（秒）
    max_retries: 3                    # 最大重试次数

# 管理员账号
admin:
  username: "${ADMIN_USERNAME}"
  password: "${ADMIN_PASSWORD}"

# API 密钥设置
api_keys:
  prefix: "sk-proxy-"                 # 密钥前缀
  default_limit: 1000000              # 默认 100 万 tokens
  warning_threshold: 0.8              # 80% 使用率警告

# 速率限制配置
rate_limit:
  default:
    requests: 100
    period: 60
  by_tier:
    basic:
      requests: 100
      period: 60
    premium:
      requests: 1000
      period: 60
    unlimited:
      requests: -1                    # 无限制
      period: 60

# 日志配置
logging:
  level: "${LOG_LEVEL}"
  format: "json"                      # json | text
  outputs:
    - console
    - file
  file:
    path: "logs/relay.log"
    rotation: "daily"
    retention: 7                      # 保留天数

# 功能开关
features:
  token_counting: true                # 启用令牌计数
  request_logging: true               # 启用请求日志
  response_caching: false             # 响应缓存（未实现）
  auto_retry: true                    # 自动重试
```

### 3. 部署配置

#### 使用 Docker Compose（推荐）

##### 步骤 1：配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
# 或
vim .env
```

##### 步骤 2：生成密钥
```bash
# 生成 SECRET_KEY
openssl rand -hex 32
# 将输出复制到 .env 的 SECRET_KEY
```

##### 步骤 3：启动服务
```bash
# 使用部署脚本（自动检查配置）
chmod +x deploy.sh
./deploy.sh

# 或手动启动
docker-compose up -d

# 查看日志
docker-compose logs -f relay-station
```

##### 步骤 4：运行数据库迁移
```bash
docker-compose exec relay-station alembic upgrade head
```

#### 手动部署

##### 步骤 1：创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

##### 步骤 2：安装依赖
```bash
pip install -r requirements.txt
```

##### 步骤 3：配置数据库
```bash
# 确保 PostgreSQL 和 Redis 正在运行

# 创建数据库
psql -U postgres
CREATE DATABASE relay_station;
CREATE USER relay_user WITH PASSWORD 'relay_password';
GRANT ALL PRIVILEGES ON DATABASE relay_station TO relay_user;
\q
```

##### 步骤 4：运行迁移
```bash
alembic upgrade head
```

##### 步骤 5：启动应用
```bash
python run.py
```

### 4. 配置验证

#### 检查服务状态
```bash
# 健康检查
curl http://localhost:8000/health

# 应返回
{
  "status": "healthy",
  "service": "claude-relay-station",
  "version": "0.1.0",
  "environment": "development"
}
```

#### 管理员登录测试
```bash
# 获取管理员 token
curl -X POST http://localhost:8000/admin/login \
  -u admin:your-password

# 应返回 JWT token
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 5. 用户配置

#### 创建用户密钥
```bash
# 使用管理员 token 创建密钥
curl -X POST http://localhost:8000/admin/api-keys \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "description": "测试用户密钥",
    "token_limit": 1000000,
    "rate_limit_tier": "basic",
    "expires_in_days": 30
  }'

# 返回密钥（仅显示一次）
{
  "id": "uuid...",
  "api_key": "sk-proxy-AbCdEfGhIjKlMnOp...",  # 保存此密钥
  "name": "Test User",
  ...
}
```

#### 用户使用配置

用户在 Claude Code 中配置：

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY="sk-proxy-AbCdEfGhIjKlMnOp..."
export ANTHROPIC_BASE_URL="http://your-relay-station:8000"
```

**Windows PowerShell:**
```powershell
$env:ANTHROPIC_API_KEY="sk-proxy-AbCdEfGhIjKlMnOp..."
$env:ANTHROPIC_BASE_URL="http://your-relay-station:8000"
```

**Windows CMD:**
```cmd
set ANTHROPIC_API_KEY=sk-proxy-AbCdEfGhIjKlMnOp...
set ANTHROPIC_BASE_URL=http://your-relay-station:8000
```

### 6. 生产环境配置

#### 使用 Nginx 反向代理（HTTPS）

```nginx
server {
    listen 443 ssl http2;
    server_name relay.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

#### 环境变量调整

生产环境 `.env`:
```env
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING

# 使用更强的密钥
SECRET_KEY=<64位随机字符串>

# 数据库连接池优化
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20

# 关闭开发特性
DATABASE_ECHO=false
```

### 7. 监控配置

#### Prometheus 指标
访问 `http://localhost:8000/metrics` 查看指标

#### Grafana 仪表板
1. 访问 `http://localhost:3000`
2. 默认账号：admin/admin
3. 添加 Prometheus 数据源：`http://prometheus:9090`
4. 导入仪表板模板

### 8. 故障排查

#### 日志位置
- Docker: `docker-compose logs relay-station`
- 手动部署: `logs/relay.log`

#### 常见问题

**Q: 数据库连接失败**
```bash
# 检查 PostgreSQL 状态
docker-compose ps postgres
# 或
systemctl status postgresql

# 测试连接
psql -h localhost -U relay_user -d relay_station
```

**Q: Redis 连接失败**
```bash
# 检查 Redis 状态
docker-compose ps redis
# 或
redis-cli ping
```

**Q: 上游 API 错误**
- 检查 `UPSTREAM_API_KEY` 是否正确
- 确认网络可以访问 `api.anthropic.com`
- 查看详细错误日志

## 📚 模块说明

### API 层 (`app/api/`)
- **admin.py**: 管理员功能，包括登录、密钥管理
- **usage.py**: 用户查询自己的使用量、配额状态
- **proxy.py**: 核心代理端点，转发所有请求到上游
- **deps.py**: 依赖注入，处理认证和授权

### 核心层 (`app/core/`)
- **config.py**: 使用 Pydantic 管理环境变量配置
- **yaml_config.py**: 加载和解析 YAML 配置文件
- **security.py**: 密钥哈希、JWT 生成和验证
- **logging.py**: 结构化日志配置
- **metrics.py**: Prometheus 监控指标定义

### 服务层 (`app/services/`)
- **api_key_service.py**: API 密钥的 CRUD 操作
- **usage_log_service.py**: 使用日志的记录和查询
- **proxy_service.py**: 请求转发、重试、令牌计数
- **token_counter.py**: 使用 tiktoken 计算令牌数量

### 数据层 (`app/models/`)
- **api_key.py**: API 密钥数据模型
- **usage_log.py**: 使用日志数据模型

### 中间件 (`app/middleware/`)
- **metrics.py**: 收集请求指标

## 🚀 快速开始命令汇总

```bash
# 1. 准备环境
cp .env.example .env
vim .env  # 配置必要的环境变量

# 2. 生成密钥
openssl rand -hex 32  # 复制到 SECRET_KEY

# 3. Docker 部署
docker-compose up -d
docker-compose exec relay-station alembic upgrade head

# 4. 创建管理员 token
TOKEN=$(curl -s -X POST http://localhost:8000/admin/login \
  -u admin:your-password | jq -r '.access_token')

# 5. 创建用户密钥
curl -X POST http://localhost:8000/admin/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "token_limit": 1000000}'

# 6. 测试代理
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer sk-proxy-xxx"
```

## 📖 相关文档

- [README.md](README.md) - 项目概述和基本使用
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - 详细配置指南
- [计划文档.md](计划文档.md) - 开发计划和设计文档

## 🔒 安全注意事项

1. **密钥安全**：
   - 永远不要提交 `.env` 文件到版本控制
   - 定期轮换 `SECRET_KEY`
   - 使用强密码

2. **网络安全**：
   - 生产环境必须使用 HTTPS
   - 配置防火墙规则
   - 限制管理端点访问

3. **数据安全**：
   - 定期备份数据库
   - 启用数据库 SSL
   - 限制数据库访问权限

这个项目结构清晰地分离了各个功能模块，配置灵活，支持多种部署方式。按照配置指南可以快速搭建起中转站服务。