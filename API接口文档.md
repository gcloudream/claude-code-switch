# Claude API 中转站 - 详细API接口文档

## 📋 API 概览

### 服务信息
- **基础URL**: `http://117.72.196.48:8000`
- **API版本**: v0.1.0
- **数据格式**: JSON
- **字符编码**: UTF-8

### 认证方式
- **管理员认证**: Basic Auth + JWT Token
- **用户认证**: API Key (Bearer Token)

### 通用响应格式
```json
{
  "success": true,
  "data": {},
  "message": "操作成功"
}
```

### 错误响应格式
```json
{
  "detail": "错误信息描述"
}
```

---

## 🔐 认证流程

### 管理员认证流程

1. **Basic Auth 登录**
```bash
curl -X POST http://117.72.196.48:8000/admin/login \
  -u admin:chen
```

2. **获取JWT Token**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer", 
  "expires_in": 86400
}
```

3. **使用JWT Token**
```bash
curl -H "Authorization: Bearer <access_token>" \
  http://117.72.196.48:8000/admin/api-keys
```

### 用户认证流程

1. **获取API密钥** (通过管理员创建)
2. **使用API密钥**
```bash
curl -H "Authorization: Bearer sk-proxy-xxx..." \
  http://117.72.196.48:8000/api/usage
```

---

## 👑 管理员 API

### 1. 管理员登录
**POST** `/admin/login`

获取管理员JWT令牌，用于后续管理操作。

#### 认证方式
- Basic Auth (用户名: admin, 密码: chen)

#### 请求示例
```bash
curl -X POST http://117.72.196.48:8000/admin/login \
  -u admin:chen
```

#### 响应示例
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6ImFkbWluIiwidHlwZSI6ImFkbWluIiwiZXhwIjoxNjk0NTIwMDAwfQ.xxx",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### 错误响应
- **401**: `管理员凭据无效`

---

### 2. 创建API密钥
**POST** `/admin/api-keys`

创建新的API密钥供用户使用。

#### 认证方式
- JWT Token (管理员)

#### 请求参数
```json
{
  "name": "string",                    // 必填，密钥名称 (1-255字符)
  "description": "string",             // 可选，密钥描述 (最多1000字符)
  "token_limit": 1000000,             // 可选，令牌限制 (默认100万)
  "rate_limit_tier": "basic",         // 可选，限速层级 (basic/premium/unlimited)
  "expires_in_days": 30,              // 可选，过期天数 (1-365天)
  "allowed_ips": ["192.168.1.1"],    // 可选，允许的IP列表
  "allowed_origins": ["*.example.com"], // 可选，允许的域名列表
  "metadata": {}                      // 可选，附加元数据
}
```

#### 请求示例
```bash
curl -X POST http://117.72.196.48:8000/admin/api-keys \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试用户密钥",
    "description": "用于测试Claude API的密钥",
    "token_limit": 1000000,
    "rate_limit_tier": "basic",
    "expires_in_days": 30
  }'
```

#### 响应示例
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "api_key": "sk-proxy-abc123def456...",
  "name": "测试用户密钥",
  "description": "用于测试Claude API的密钥",
  "token_limit": 1000000,
  "rate_limit_tier": "basic",
  "expires_at": "2025-09-21T13:00:00Z",
  "created_at": "2025-08-22T13:00:00Z"
}
```

#### 字段说明
- `api_key`: **仅在创建时返回一次**，请妥善保存
- `rate_limit_tier`: 支持 `basic`(100req/min), `premium`(1000req/min), `unlimited`

---

### 3. 查看所有API密钥
**GET** `/admin/api-keys`

获取所有API密钥的列表信息。

#### 认证方式
- JWT Token (管理员)

#### 查询参数
- `skip`: 跳过数量 (默认0)
- `limit`: 返回数量 (默认100, 最大1000)
- `active_only`: 仅显示激活的密钥 (true/false)

#### 请求示例
```bash
curl -X GET "http://117.72.196.48:8000/admin/api-keys?limit=10&active_only=true" \
  -H "Authorization: Bearer <admin-token>"
```

#### 响应示例
```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "测试用户密钥",
      "description": "用于测试Claude API的密钥",
      "key_prefix": "sk-proxy-abc123...",
      "token_limit": 1000000,
      "token_used": 50000,
      "token_remaining": 950000,
      "usage_percentage": 5.0,
      "rate_limit_tier": "basic",
      "request_count": 125,
      "error_count": 2,
      "is_active": true,
      "created_at": "2025-08-22T13:00:00Z",
      "updated_at": "2025-08-22T14:30:00Z",
      "last_used_at": "2025-08-22T14:25:00Z",
      "expires_at": "2025-09-21T13:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 10
}
```

---

### 4. 查看单个API密钥详情
**GET** `/admin/api-keys/{api_key_id}`

获取指定API密钥的详细信息。

#### 认证方式
- JWT Token (管理员)

#### 路径参数
- `api_key_id`: API密钥的UUID

#### 请求示例
```bash
curl -X GET http://117.72.196.48:8000/admin/api-keys/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer <admin-token>"
```

#### 响应示例
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "测试用户密钥",
  "description": "用于测试Claude API的密钥",
  "key_prefix": "sk-proxy-abc123...",
  "token_limit": 1000000,
  "token_used": 50000,
  "token_remaining": 950000,
  "usage_percentage": 5.0,
  "rate_limit_tier": "basic",
  "request_count": 125,
  "error_count": 2,
  "is_active": true,
  "created_at": "2025-08-22T13:00:00Z",
  "updated_at": "2025-08-22T14:30:00Z",
  "last_used_at": "2025-08-22T14:25:00Z",
  "expires_at": "2025-09-21T13:00:00Z"
}
```

#### 错误响应
- **404**: `API密钥未找到`

---

### 5. 获取API密钥统计
**GET** `/admin/api-keys/{api_key_id}/stats`

获取指定API密钥的详细使用统计。

#### 认证方式
- JWT Token (管理员)

#### 请求示例
```bash
curl -X GET http://117.72.196.48:8000/admin/api-keys/123e4567-e89b-12d3-a456-426614174000/stats \
  -H "Authorization: Bearer <admin-token>"
```

#### 响应示例
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "测试用户密钥",
  "created_at": "2025-08-22T13:00:00Z",
  "last_used_at": "2025-08-22T14:25:00Z",
  "token_limit": 1000000,
  "token_used": 50000,
  "token_remaining": 950000,
  "usage_percentage": 5.0,
  "request_count": 125,
  "error_count": 2,
  "is_active": true,
  "is_expired": false,
  "expires_at": "2025-09-21T13:00:00Z"
}
```

---

### 6. 禁用API密钥
**POST** `/admin/api-keys/{api_key_id}/disable`

禁用指定的API密钥，禁用后该密钥无法使用。

#### 认证方式
- JWT Token (管理员)

#### 请求示例
```bash
curl -X POST http://117.72.196.48:8000/admin/api-keys/123e4567-e89b-12d3-a456-426614174000/disable \
  -H "Authorization: Bearer <admin-token>"
```

#### 响应示例
```json
{
  "message": "API密钥已成功禁用"
}
```

---

### 7. 启用API密钥
**POST** `/admin/api-keys/{api_key_id}/enable`

启用指定的API密钥，启用后密钥恢复正常使用。

#### 认证方式
- JWT Token (管理员)

#### 请求示例
```bash
curl -X POST http://117.72.196.48:8000/admin/api-keys/123e4567-e89b-12d3-a456-426614174000/enable \
  -H "Authorization: Bearer <admin-token>"
```

#### 响应示例
```json
{
  "message": "API密钥已成功启用"
}
```

---

### 8. 删除API密钥
**DELETE** `/admin/api-keys/{api_key_id}`

删除指定的API密钥。支持软删除和硬删除。

#### 认证方式
- JWT Token (管理员)

#### 查询参数
- `hard_delete`: 是否硬删除 (true/false, 默认false)

#### 请求示例
```bash
# 软删除 (可恢复)
curl -X DELETE http://117.72.196.48:8000/admin/api-keys/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer <admin-token>"

# 硬删除 (不可恢复)  
curl -X DELETE "http://117.72.196.48:8000/admin/api-keys/123e4567-e89b-12d3-a456-426614174000?hard_delete=true" \
  -H "Authorization: Bearer <admin-token>"
```

#### 响应示例
```json
{
  "message": "API密钥已成功软删除"
}
```

---

## 👤 用户 API

### 1. 获取使用统计
**GET** `/api/usage`

获取API密钥的总体使用统计信息。

#### 认证方式
- API Key (Bearer Token)

#### 查询参数
- `start_date`: 筛选开始日期 (ISO格式，可选)
- `end_date`: 筛选结束日期 (ISO格式，可选)

#### 请求示例
```bash
curl -X GET "http://117.72.196.48:8000/api/usage?start_date=2025-08-01T00:00:00Z&end_date=2025-08-22T23:59:59Z" \
  -H "Authorization: Bearer sk-proxy-abc123..."
```

#### 响应示例
```json
{
  "total_requests": 125,
  "total_tokens": 50000,
  "total_prompt_tokens": 30000,
  "total_completion_tokens": 20000,
  "total_cost": 1.25,
  "avg_response_time_ms": 1250.5,
  "error_count": 2,
  "error_rate": 1.6,
  "model_usage": [
    {
      "model": "claude-3-sonnet-20240229",
      "request_count": 100,
      "total_tokens": 40000
    },
    {
      "model": "claude-3-haiku-20240307", 
      "request_count": 25,
      "total_tokens": 10000
    }
  ],
  "error_breakdown": [
    {
      "error_code": "rate_limit_exceeded",
      "count": 2
    }
  ]
}
```

---

### 2. 获取每日使用量
**GET** `/api/usage/daily`

获取API密钥的每日使用量统计。

#### 认证方式
- API Key (Bearer Token)

#### 查询参数
- `days`: 检索天数 (1-365，默认30)

#### 请求示例
```bash
curl -X GET "http://117.72.196.48:8000/api/usage/daily?days=7" \
  -H "Authorization: Bearer sk-proxy-abc123..."
```

#### 响应示例
```json
[
  {
    "date": "2025-08-22",
    "requests": 45,
    "tokens": 18000,
    "cost": 0.54,
    "errors": 1
  },
  {
    "date": "2025-08-21", 
    "requests": 32,
    "tokens": 12800,
    "cost": 0.38,
    "errors": 0
  }
]
```

---

### 3. 获取使用日志
**GET** `/api/usage/logs`

获取API密钥的详细使用日志记录。

#### 认证方式
- API Key (Bearer Token)

#### 查询参数
- `start_date`: 筛选开始日期 (ISO格式，可选)
- `end_date`: 筛选结束日期 (ISO格式，可选)
- `skip`: 跳过项目数 (默认0)
- `limit`: 返回最大项目数 (1-1000，默认100)

#### 请求示例
```bash
curl -X GET "http://117.72.196.48:8000/api/usage/logs?limit=5&skip=0" \
  -H "Authorization: Bearer sk-proxy-abc123..."
```

#### 响应示例
```json
[
  {
    "id": "log-uuid-1",
    "api_key_id": "123e4567-e89b-12d3-a456-426614174000",
    "request_id": "req-abc123",
    "request_method": "POST",
    "request_path": "/v1/messages",
    "request_size": 1024,
    "response_status": 200,
    "response_size": 2048,
    "response_time_ms": 1250.5,
    "prompt_tokens": 150,
    "completion_tokens": 75,
    "total_tokens": 225,
    "model": "claude-3-sonnet-20240229",
    "is_error": false,
    "error_message": null,
    "error_code": null,
    "total_cost": 0.0075,
    "created_at": "2025-08-22T14:25:30Z"
  }
]
```

---

### 4. 获取配额状态
**GET** `/api/usage/quota`

获取API密钥的当前配额使用状态。

#### 认证方式
- API Key (Bearer Token)

#### 请求示例
```bash
curl -X GET http://117.72.196.48:8000/api/usage/quota \
  -H "Authorization: Bearer sk-proxy-abc123..."
```

#### 响应示例
```json
{
  "token_limit": 1000000,
  "token_used": 50000,
  "token_remaining": 950000,
  "usage_percentage": 5.0,
  "is_quota_exceeded": false,
  "rate_limit_tier": "basic",
  "is_active": true,
  "expires_at": "2025-09-21T13:00:00Z",
  "is_expired": false
}
```

---

## 🔄 代理 API

### Claude API 转发
**任意方法** `/*`

将所有Claude API请求转发到上游服务。

#### 认证方式
- API Key (Bearer Token)

#### 支持的Claude API端点
- `POST /v1/messages` - 消息对话
- `GET /v1/models` - 获取模型列表
- 以及所有其他Claude API路径

#### 请求示例
```bash
# Claude消息API
curl -X POST http://117.72.196.48:8000/v1/messages \
  -H "Authorization: Bearer sk-proxy-abc123..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 1024,
    "messages": [
      {
        "role": "user",
        "content": "你好，请介绍一下Claude API"
      }
    ]
  }'
```

#### 响应示例
响应格式与原始Claude API完全相同：
```json
{
  "id": "msg_01ABC123",
  "type": "message", 
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "你好！Claude API是Anthropic开发的..."
    }
  ],
  "model": "claude-3-sonnet-20240229",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 15,
    "output_tokens": 45
  }
}
```

---

## 🔍 公共端点

### 1. 服务状态
**GET** `/`

获取服务基本状态信息。

#### 请求示例
```bash
curl http://117.72.196.48:8000/
```

#### 响应示例
```json
{
  "service": "Claude API 中转站",
  "version": "0.1.0", 
  "status": "运行中",
  "documentation": "/admin/docs"
}
```

---

### 2. 健康检查
**GET** `/health`

获取服务健康状态。

#### 请求示例
```bash
curl http://117.72.196.48:8000/health
```

#### 响应示例
```json
{
  "status": "健康",
  "service": "claude-api-中转站",
  "version": "0.1.0",
  "environment": "development"
}
```

---

### 3. Prometheus指标
**GET** `/metrics`

获取Prometheus格式的监控指标。

#### 请求示例
```bash
curl http://117.72.196.48:8000/metrics
```

#### 响应示例
```
# HELP relay_requests_total Total number of relay requests
# TYPE relay_requests_total counter
relay_requests_total{method="POST",status="200"} 125

# HELP proxy_duration_seconds Time spent on proxy requests
# TYPE proxy_duration_seconds histogram
proxy_duration_seconds_bucket{le="1.0"} 100
proxy_duration_seconds_bucket{le="2.0"} 120
proxy_duration_seconds_bucket{le="+Inf"} 125
```

---

## 📊 数据模型

### API密钥创建请求
```typescript
interface APIKeyCreateRequest {
  name: string;                    // 必填，密钥名称
  description?: string;            // 可选，描述
  token_limit?: number;           // 可选，令牌限制 (默认1000000)
  rate_limit_tier?: string;       // 可选，限速层级 (默认"basic")
  expires_in_days?: number;       // 可选，过期天数
  allowed_ips?: string[];         // 可选，允许的IP列表
  allowed_origins?: string[];     // 可选，允许的域名列表
  metadata?: Record<string, any>; // 可选，元数据
}
```

### API密钥响应
```typescript
interface APIKeyResponse {
  id: string;                     // UUID
  name: string;                   // 密钥名称
  description?: string;           // 描述
  key_prefix: string;            // 密钥前缀 (sk-proxy-xxx...)
  token_limit: number;           // 令牌限制
  token_used: number;            // 已使用令牌
  token_remaining: number;       // 剩余令牌
  usage_percentage: number;      // 使用率百分比
  rate_limit_tier: string;       // 限速层级
  request_count: number;         // 请求次数
  error_count: number;           // 错误次数
  is_active: boolean;            // 是否激活
  created_at: string;            // 创建时间 (ISO格式)
  updated_at: string;            // 更新时间
  last_used_at?: string;         // 最后使用时间
  expires_at?: string;           // 过期时间
}
```

### 使用统计响应
```typescript
interface UsageStatisticsResponse {
  total_requests: number;        // 总请求数
  total_tokens: number;          // 总令牌数
  total_prompt_tokens: number;   // 输入令牌数
  total_completion_tokens: number; // 输出令牌数
  total_cost: number;            // 总费用
  avg_response_time_ms: number;  // 平均响应时间(毫秒)
  error_count: number;           // 错误数量
  error_rate: number;            // 错误率百分比
  model_usage: ModelUsage[];     // 模型使用统计
  error_breakdown: ErrorBreakdown[]; // 错误分类统计
}
```

---

## ⚠️ 错误码说明

### HTTP状态码
- **200**: 请求成功
- **401**: 身份验证失败
  - `需要管理员身份验证`
  - `需要API密钥` 
  - `无效的管理员令牌`
  - `无效的API密钥`
- **403**: 权限不足
- **404**: 资源未找到
  - `API密钥未找到`
  - `未找到`
- **422**: 请求参数验证失败
- **429**: 请求频率超限
- **500**: 服务器内部错误

### 业务错误码
响应中的`detail`字段包含具体错误信息：

#### 认证相关
- `管理员凭据无效` - 管理员用户名或密码错误
- `需要管理员身份验证` - 缺少管理员认证
- `无效的管理员令牌` - JWT令牌无效或过期
- `需要API密钥` - 缺少API密钥
- `无效的API密钥` - API密钥格式错误或不存在

#### 资源相关
- `API密钥未找到` - 指定的API密钥ID不存在
- `未找到` - 请求的资源不存在

#### 业务逻辑
- `配额已用尽` - API密钥令牌用量超过限制
- `密钥已过期` - API密钥已超过有效期
- `密钥已禁用` - API密钥已被管理员禁用
- `请求频率过高` - 超过速率限制

---

## 🛠️ Python SDK 示例

### 管理员操作示例
```python
import requests
import base64

class ClaudeRelayAdmin:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
    
    def login(self):
        """管理员登录"""
        auth_str = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        headers = {"Authorization": f"Basic {auth_str}"}
        
        response = requests.post(f"{self.base_url}/admin/login", headers=headers)
        response.raise_for_status()
        
        data = response.json()
        self.token = data["access_token"]
        return data
    
    def create_api_key(self, name, description=None, token_limit=1000000):
        """创建API密钥"""
        if not self.token:
            self.login()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "name": name,
            "description": description,
            "token_limit": token_limit,
            "rate_limit_tier": "basic"
        }
        
        response = requests.post(f"{self.base_url}/admin/api-keys", 
                               json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def list_api_keys(self):
        """获取所有API密钥"""
        if not self.token:
            self.login()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{self.base_url}/admin/api-keys", headers=headers)
        response.raise_for_status()
        return response.json()

# 使用示例
admin = ClaudeRelayAdmin("http://117.72.196.48:8000", "admin", "chen")

# 创建API密钥
api_key_info = admin.create_api_key(
    name="Python SDK测试", 
    description="通过Python SDK创建的测试密钥",
    token_limit=500000
)
print(f"新密钥: {api_key_info['api_key']}")

# 获取所有密钥
keys = admin.list_api_keys()
print(f"总共 {keys['total']} 个密钥")
```

### 用户操作示例
```python
import requests

class ClaudeRelayClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
    
    def get_usage_stats(self):
        """获取使用统计"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(f"{self.base_url}/api/usage", headers=headers)
        response.raise_for_status()
        return response.json()
    
    def get_quota_status(self):
        """获取配额状态"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(f"{self.base_url}/api/usage/quota", headers=headers)
        response.raise_for_status()
        return response.json()
    
    def send_message(self, message, model="claude-3-sonnet-20240229"):
        """发送消息到Claude"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": message}]
        }
        
        response = requests.post(f"{self.base_url}/v1/messages", 
                               json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

# 使用示例  
client = ClaudeRelayClient("http://117.72.196.48:8000", "sk-proxy-abc123...")

# 检查配额
quota = client.get_quota_status()
print(f"剩余令牌: {quota['token_remaining']}")

# 发送消息
response = client.send_message("你好，请介绍一下你自己")
print(f"Claude回复: {response['content'][0]['text']}")

# 查看使用统计
stats = client.get_usage_stats()
print(f"总请求数: {stats['total_requests']}")
print(f"总花费: ${stats['total_cost']:.4f}")
```

---

## 🔗 相关链接

- **服务地址**: http://117.72.196.48:8000/
- **Swagger UI**: http://117.72.196.48:8000/admin/docs
- **健康检查**: http://117.72.196.48:8000/health
- **监控指标**: http://117.72.196.48:8000/metrics

## 📞 技术支持

如有问题，请通过以下方式获取帮助：
1. 查看 Swagger UI 文档
2. 检查服务日志
3. 提交 GitHub Issue

---

*Claude API 中转站 API文档 v0.1.0 - 最后更新: 2025-08-22*