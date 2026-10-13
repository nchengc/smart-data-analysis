# 部署文档：Docker Compose + 阿里云 / 本地私有化

## 一、本地 Docker Compose（最简单）

### 1. 目录结构
```
deploy/
├─ docker-compose.yml
├─ backend.Dockerfile
├─ frontend.Dockerfile
└─ .env.example
```

### 2. `backend.Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 系统依赖（pytz etc 视情况）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc && rm -rf /var/lib/apt/lists/*

COPY ../backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../backend/app ./app
COPY ../backend/data ./data
COPY ../backend/tests ./tests
COPY ../backend/.env ./.env  # 首次手动 copy

EXPOSE 8000
CMD ["python", "run.py"]
```

### 3. `docker-compose.yml`
```yaml
version: '3.9'
services:
  backend:
    build: .
    container_name: sda-backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data    # 持久化 SQLite
    restart: unless-stopped

  frontend:
    image: node:20-alpine
    container_name: sda-frontend
    working_dir: /app
    volumes:
      - ../frontend:/app
    ports:
      - "5173:5173"
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
    depends_on:
      - backend
    restart: unless-stopped
```

### 4. 启动
```bash
cd deploy
cp .env.example .env       # 填入 MINIMAX_API_KEY 等
docker compose up -d --build
```

- 后端： http://localhost:8000/docs
- 前端： http://localhost:5173

---

## 二、阿里云 ECS 部署（公网可访问）

### 场景
- 个人/团队工具，需要给外部用户提供服务
- 已有阿里云账号 + ECS + 备案域名

### 步骤

#### 1. ECS 环境准备
```bash
# 1) 系统：Ubuntu 22.04 / 4核8G 起步
# 2) 安装 Docker & Docker Compose
curl -fsSL https://get.docker.com | bash
sudo usermod -aG docker $USER

# 3) 开放端口（安全组 → 入方向）
#    - 80 / 443 (Nginx)
#    - 8000 (后端，可选)
#    - 5173 (前端，可选，prod 不需要)
```

#### 2. 域名 + 反向代理
**域名解析**：`data.example.com → ECS 公网 IP`

**Nginx 配置**（推荐 HTTPS，Let's Encrypt 免费证书）：
```nginx
# /etc/nginx/sites-available/sda
server {
    listen 80;
    server_name data.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name data.example.com;

    # SSL 证书
    ssl_certificate /etc/letsencrypt/live/data.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/data.example.com/privkey.pem;

    # 前端（Vite 静态产物）
    location / {
        root /opt/sda/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反代
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        # SSE 必须关闭缓冲
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # Swagger
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/sda /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

#### 3. 前端生产构建
```bash
cd frontend
npm install
npm run build
# 产出 dist/，把整个 dist/ 上传到 /opt/sda/frontend/dist
```

修改 `frontend/vite.config.ts` 让生产构建也走 `/api` 前缀：
```ts
server: { proxy: { '/api': 'http://localhost:8000' } }
```

#### 4. 后端用 systemd 管理（比 Docker 更轻）
```ini
# /etc/systemd/system/sda-backend.service
[Unit]
Description=Smart Data Analysis Backend
After=network.target

[Service]
Type=simple
User=sda
WorkingDirectory=/opt/sda/backend
Environment="PATH=/opt/sda/backend/.venv/bin"
EnvironmentFile=/opt/sda/backend/.env
ExecStart=/opt/sda/backend/.venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sda-backend
sudo journalctl -u sda-backend -f
```

#### 5. 数据持久化
- SQLite 文件：`/opt/sda/backend/data/app.db`
- 建议每日 `sqlite3 app.db ".backup /backup/app-$(date +%F).db"` 备份到 OSS
- 或 `cron` + `ossutil` 自动上传

---

## 三、生产强化建议（可选）

### 1. 进程守护
- systemd（已在 #4 推荐）
- 或 supervisor

### 2. 监控
```bash
# 1) 健康检查 endpoint
curl -s http://127.0.0.1:8000/api/health

# 2) 接入阿里云云监控 / 阿里云日志服务 SLS
# 3) 简易：写个 bash 脚本每分钟 ping 一次，挂了 systemctl restart
```

### 3. 速率限制
```bash
pip install slowapi
# 在 FastAPI 添加：
# from slowapi import Limiter
# limiter = Limiter(key_func=lambda r: r.client.host)
# app.state.limiter = limiter
# @app.post("/api/chat/stream")
# @limiter.limit("10/minute")
# async def stream_chat(req: Request): ...
```

### 4. 数据库升级到 PostgreSQL（多用户/大数据量时）
```python
# app/db/engine.py 改用：
# engine = create_engine("postgresql+psycopg2://user:pass@host/sda")
```
注：SQLite 方言提示要相应改成 PostgreSQL 方言。

### 5. HTTPS 免费证书
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d data.example.com
# 自动续期已加在 cron
```

---

## 四、健康检查 + 故障排查

```bash
# 1) 后端是否在跑？
curl -sf http://127.0.0.1:8000/api/health || echo "后端宕了"

# 2) 前端 dist 是否完整？
ls /opt/sda/frontend/dist/
# 应该看到 index.html + assets/ 文件夹

# 3) 查看后端日志
sudo journalctl -u sda-backend -n 100

# 4) DB 是否写入？
sqlite3 /opt/sda/backend/data/app.db "SELECT COUNT(*) FROM messages"

# 5) LLM API key 是否有效？
curl -X POST $MINIMAX_BASE_URL/chat/completions \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -d '{"model":"MiniMax-Text-01","messages":[{"role":"user","content":"hi"}]}'
```

---

## 五、扩容路径

| 当前阶段 | 升级到 | 触发条件 |
|---|---|---|
| SQLite | PostgreSQL | 用户 > 10 / 数据 > 1GB |
| 单实例后端 | 多实例 + Redis session | 用户同时 > 50 |
| Vite 单页 | Vite + CDN + 静态资源 OSS | 流量 > 10 万 PV/月 |
| OpenAI-Compat LLM | LiteLLM 路由（多供应商）| 需要 A/B 测试多个 LLM |
| 本地 Ollama + Qwen | Qwen2.5-Coder 7B + LangChain | 离线场景 / 数据隐私 |
