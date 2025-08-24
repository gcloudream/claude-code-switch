# Claude API 中转站

一个高性能的 Claude API 代理服务，提供 API 密钥管理、使用量跟踪、配额控制和请求转发功能。

## 功能特性

### 核心功能
- 🔑 **API 密钥管理**：创建和管理代理 API 密钥，独立计费
- 🔄 **请求转发**：无缝代理到 Anthropic Claude API，带重试机制
- 📊 **使用量跟踪**：全面的 token 使用量监控和请求日志
- 🎯 **配额控制**：每个密钥的 token 限制和可配置等级的速率限制
- 🔒 **安全性**：哈希存储 API 密钥，支持 IP/域名白名单
- 📈 **监控**：导出 Prometheus 指标供 Grafana 可视化

### 管理员功能
- 基于 JWT 的管理员认证
- 创建、禁用和删除 API 密钥
- 查看所有密钥的使用统计
- 配置速率限制等级

### 用户功能
- 查询个人 API 密钥使用统计
- 获取每日使用量明细
- 访问详细的请求日志
- 实时配额状态监控

## 快速开始

### 环境要求
- Python 3.11+
- PostgreSQL 14+
- Redis 6+（可选）
- Docker & Docker Compose（可选）

### 安装部署

#### Docker 部署（推荐）

1. 克隆并配置：
```bash
git clone <repository-url>
cd claude-code-switch
cp .env.example .env
# 编辑 .env 文件，配置必要的环境变量
```

2. 使用自动化脚本部署：
```bash
chmod +x deploy.sh
./deploy.sh
```

3. 或者手动使用 Docker Compose：
```bash
docker-compose up -d
docker-compose exec relay-station alembic upgrade head
```

#### 手动安装

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境：
```bash
cp .env.example .env
# 编辑 .env 文件，配置你的设置
```

3. 运行数据库迁移：
```bash
alembic upgrade head
```

4. 启动服务器：
```bash
python run.py
```

## 配置说明

### 环境变量

在 `.env` 文件中配置以下关键变量：

```env
# 核心配置
UPSTREAM_API_KEY=你的-anthropic-api-密钥
ADMIN_PASSWORD=你的安全密码
SECRET_KEY=你的-jwt-密钥

# 数据库
DATABASE_URL=postgresql://postgres:postgres@localhost:15432/relay_station

# Redis（可选）
REDIS_URL=redis://localhost:16379/0

# 外部服务（Docker）
# PostgreSQL: localhost:15432 (用户: postgres, 密码: postgres)
# Redis: localhost:16379 (密码: 123456)
```

### 密钥生成

生成安全的 JWT 密钥：
```bash
openssl rand -hex 32
```

### 高级配置

编辑 `config.yaml` 进行详细设置：

```yaml
upstream:
  primary:
    url: "https://api.anthropic.com/v1"
    api_key: "${UPSTREAM_API_KEY}"
    timeout: 60
    max_retries: 3

rate_limit:
  by_tier:
    basic:
      requests: 100
      period: 60
    premium:
      requests: 1000
      period: 60
```

## 使用指南

### 管理员操作

1. **登录获取管理员令牌**：
```bash
curl -X POST http://localhost:8000/admin/login \
  -u admin:你的管理员密码
```

2. **为用户创建 API 密钥**：
```bash
curl -X POST http://localhost:8000/admin/api-keys \
  -H "Authorization: Bearer <管理员令牌>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "用户名称",
    "description": "描述",
    "token_limit": 1000000,
    "rate_limit_tier": "basic"
  }'
```

响应包含生成的 API 密钥（仅显示一次）：
```json
{
  "id": "uuid",
  "api_key": "sk-proxy-xxx...",
  "name": "用户名称",
  "token_limit": 1000000,
  "tokens_used": 0,
  "is_active": true
}
```

### 客户端配置

**对于 Claude Code 用户**，配置环境变量：
```bash
export ANTHROPIC_API_KEY="sk-proxy-xxx..."  # 你的中转站生成的密钥
export ANTHROPIC_BASE_URL="http://localhost:8000"  # 中转站 URL
```

### 用户 API 操作

1. **查看使用统计**：
```bash
curl -X GET http://localhost:8000/api/usage \
  -H "Authorization: Bearer sk-proxy-xxx..."
```

2. **检查配额状态**：
```bash
curl -X GET http://localhost:8000/api/usage/quota \
  -H "Authorization: Bearer sk-proxy-xxx..."
```

3. **获取每日使用明细**：
```bash
curl -X GET http://localhost:8000/api/usage/daily \
  -H "Authorization: Bearer sk-proxy-xxx..."
```

## API 接口

### 管理员接口（需要管理员认证）
- `POST /admin/login` - 管理员登录
- `POST /admin/api-keys` - 创建 API 密钥
- `GET /admin/api-keys` - 列出所有密钥
- `GET /admin/api-keys/{id}` - 获取密钥详情
- `POST /admin/api-keys/{id}/disable` - 禁用密钥
- `POST /admin/api-keys/{id}/enable` - 启用密钥
- `DELETE /admin/api-keys/{id}` - 删除密钥

### 用户接口（需要 API 密钥）
- `GET /api/usage` - 获取使用统计
- `GET /api/usage/daily` - 获取每日使用明细
- `GET /api/usage/logs` - 获取使用日志
- `GET /api/usage/quota` - 获取配额状态

### 代理接口
- `/*` - 所有其他请求转发到上游 API

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Claude Code   │───▶│     中转代理     │───▶│  Anthropic API  │
│      客户端      │    │      服务       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   PostgreSQL    │
                       │     数据库       │
                       └─────────────────┘
```

### 核心组件

- **API 层** (`app/api/`)：管理和代理操作的 REST 接口
- **服务层** (`app/services/`)：API 密钥、使用跟踪和代理的业务逻辑
- **数据层** (`app/models/`)：数据库实体的 SQLAlchemy 模型
- **核心层** (`app/core/`)：配置、安全、日志和指标

### 关键特性

1. **代理服务** (`app/services/proxy_service.py`)：
   - 将用户的代理密钥替换为真实的 Anthropic API 密钥
   - 实现指数退避的重试逻辑
   - 从 API 响应中提取 token 使用量
   - 在需要时回退到 tiktoken 估算

2. **Token 管理**：
   - 使用 tiktoken 进行精确的 token 计数
   - 跟踪 prompt_tokens、completion_tokens、total_tokens
   - 执行每个密钥的配额和速率限制

3. **安全性**：
   - 使用 bcrypt 哈希存储 API 密钥
   - JWT 令牌用于管理员认证
   - 请求/响应过滤以防止数据泄露

## 监控与指标

### Prometheus 指标
服务导出以下指标：
- `relay_requests_total` - 请求总数
- `proxy_duration_seconds` - 代理请求延迟
- `tokens_used_total` - 消耗的 token 总数
- `token_quota_usage_ratio` - 配额使用比例

访问指标：`http://localhost:8000/metrics`

### 健康检查
监控服务健康状态：
```bash
curl http://localhost:8000/health
```

## 安全最佳实践

### 生产环境配置
- 使用强密码和复杂的 SECRET_KEY
- 通过反向代理（Nginx/Apache）启用 HTTPS
- 通过 IP 限制管理员接口访问
- 设置适当的防火墙规则

### API 密钥管理
- 定期轮换管理员密码
- 为不同应用创建独立的 API 密钥
- 设置合理的 token 限制和过期时间
- 监控异常使用模式

### 监控与告警
- 设置配额使用告警
- 监控可疑请求模式
- 定期审计使用日志
- 跟踪认证失败尝试

## 故障排除

### 常见问题

**数据库连接失败**：
- 验证 PostgreSQL 是否运行
- 检查 DATABASE_URL 配置
- 确保数据库用户有正确的权限

**上游 API 超时**：
- 验证 UPSTREAM_API_KEY 是否有效
- 检查网络连通性
- 在 config.yaml 中调整超时配置

**Token 计数不准确**：
- 确保 tiktoken 已安装：`pip install tiktoken`
- 验证模型名称是否正确识别

## 开发指南

### 测试
```bash
# 运行测试
pytest tests/

# 带覆盖率运行
pytest --cov=app tests/
```

### 代码质量
```bash
# 格式化代码
black app/

# 代码检查
flake8 app/

# 类型检查
mypy app/
```

### 数据库操作
```bash
# 创建新迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 贡献

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature-name`
3. 进行你的修改
4. 运行测试和代码检查
5. 提交 Pull Request

## 许可证

MIT 许可证 - 详见 LICENSE 文件。

## 支持

如有问题和疑问：
- 在仓库中创建 issue
- 查看现有文档
- 联系维护者