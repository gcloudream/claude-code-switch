# Claude Relay Station 配置指南

## 架构说明

```
Claude Code 用户 → 中转站 (Relay Station) → Anthropic API
     ↑                ↑                      ↑
使用中转站密钥    替换为真实密钥      真实 Anthropic 服务
```

## 一、中转站服务器配置

### 1. 复制环境变量模板
```bash
cp .env.example .env
```

### 2. 编辑 `.env` 文件

```env
# ========== 核心配置 ==========

# 第三方 API 配置（你的真实 Anthropic API）
UPSTREAM_API_URL=https://api.anthropic.com/v1
UPSTREAM_API_KEY=sk-ant-api03-xxxxx  # 👈 你的真实 Anthropic API Key

# 管理员账号（用于管理中转站）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password-here  # 👈 设置一个强密码

# 安全密钥（JWT签名用）
SECRET_KEY=生成的32位hex字符串  # 👈 运行: openssl rand -hex 32

# ========== 数据库配置 ==========
DATABASE_URL=postgresql+asyncpg://relay_user:relay_password@localhost:5432/relay_station

# ========== Redis配置 ==========
REDIS_URL=redis://localhost:6379/0
```

### 3. 也可以通过 `config.yaml` 配置

```yaml
# config.yaml
upstream:
  primary:
    name: "Anthropic Claude API"
    url: "${UPSTREAM_API_URL}"  # 从环境变量读取
    api_key: "${UPSTREAM_API_KEY}"  # 从环境变量读取
    timeout: 60
    max_retries: 3

# 如果你有多个上游 API，可以配置备用
# secondary:
#   name: "Alternative API"
#   url: "https://api.alternative.com/v1"
#   api_key: "${ALT_API_KEY}"
```

## 二、启动中转站

### 使用 Docker Compose（推荐）
```bash
# 确保 .env 配置正确后
docker-compose up -d

# 运行数据库迁移
docker-compose exec relay-station alembic upgrade head
```

### 或手动启动
```bash
# 安装依赖
pip install -r requirements.txt

# 运行迁移
alembic upgrade head

# 启动服务
python run.py
```

## 三、创建中转站密钥

### 1. 管理员登录
```bash
# 获取管理员 token
curl -X POST http://localhost:8000/admin/login \
  -u admin:your-password

# 响应示例：
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### 2. 创建用户密钥
```bash
curl -X POST http://localhost:8000/admin/api-keys \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User Alice",
    "description": "Alice 的密钥",
    "token_limit": 1000000,
    "rate_limit_tier": "basic"
  }'

# 响应示例：
{
  "id": "uuid-xxx",
  "api_key": "sk-proxy-AbCdEfGhIjKlMnOpQrStUvWxYz123456",  # 👈 这是给用户的密钥
  "name": "User Alice",
  ...
}
```

## 四、用户使用配置

### 方式 1：环境变量（Claude Code）

用户在自己的 Claude Code 中设置：

```bash
# Linux/Mac
export ANTHROPIC_API_KEY="sk-proxy-AbCdEfGhIjKlMnOpQrStUvWxYz123456"  # 中转站密钥
export ANTHROPIC_BASE_URL="http://your-relay-station.com:8000"  # 中转站地址

# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-proxy-AbCdEfGhIjKlMnOpQrStUvWxYz123456"
$env:ANTHROPIC_BASE_URL="http://your-relay-station.com:8000"
```

### 方式 2：代码中配置

```python
# Python 示例
from anthropic import Anthropic

client = Anthropic(
    api_key="sk-proxy-AbCdEfGhIjKlMnOpQrStUvWxYz123456",  # 中转站密钥
    base_url="http://your-relay-station.com:8000"  # 中转站地址
)
```

```javascript
// JavaScript 示例
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({
  apiKey: 'sk-proxy-AbCdEfGhIjKlMnOpQrStUvWxYz123456',  // 中转站密钥
  baseURL: 'http://your-relay-station.com:8000'  // 中转站地址
});
```

## 五、验证配置

### 1. 测试中转站健康状态
```bash
curl http://localhost:8000/health
# 应返回: {"status": "healthy", ...}
```

### 2. 测试用户密钥
```bash
# 查询配额状态
curl http://localhost:8000/api/usage/quota \
  -H "Authorization: Bearer sk-proxy-AbCdEfGhIjKlMnOpQrStUvWxYz123456"

# 应返回配额信息
```

### 3. 测试 API 调用
```bash
curl http://localhost:8000/v1/messages \
  -H "Authorization: Bearer sk-proxy-AbCdEfGhIjKlMnOpQrStUvWxYz123456" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-sonnet-20240229",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

## 六、常见问题

### Q: UPSTREAM_API_KEY 和用户的 API key 有什么区别？

- **UPSTREAM_API_KEY**: 你的真实 Anthropic API 密钥，配置在中转站服务器上
- **sk-proxy-xxx**: 中转站生成的密钥，分发给用户使用

### Q: 用户如何查询自己的使用量？

```bash
# 查询使用统计
curl http://your-relay-station.com:8000/api/usage \
  -H "Authorization: Bearer sk-proxy-xxx"

# 查询每日使用量
curl http://your-relay-station.com:8000/api/usage/daily \
  -H "Authorization: Bearer sk-proxy-xxx"
```

### Q: 如何限制用户的使用量？

创建密钥时设置 `token_limit`：
```json
{
  "name": "Limited User",
  "token_limit": 100000,  // 限制 10 万 tokens
  "rate_limit_tier": "basic"  // 速率限制层级
}
```

### Q: 如何配置多个上游 API？

目前代码主要支持单个上游 API，但架构已预留扩展接口。可以在 `config.yaml` 中配置多个上游，然后修改 `proxy_service.py` 实现负载均衡或故障转移。

## 七、安全建议

1. **生产环境必须使用 HTTPS**
   - 使用 Nginx 反向代理添加 SSL
   - 或使用 Cloudflare 等 CDN 服务

2. **定期轮换密钥**
   - 定期更换 SECRET_KEY
   - 定期审查和轮换用户密钥

3. **监控异常使用**
   - 设置 Prometheus + Grafana 监控
   - 配置使用量告警

4. **限制访问**
   - 使用防火墙限制管理端口访问
   - 配置 IP 白名单（如需要）