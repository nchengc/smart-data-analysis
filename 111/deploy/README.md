# Deploy 目录

Docker Compose 一键启动：

```bash
cd deploy
cp .env.example .env  # 填入 MINIMAX_API_KEY
docker compose up -d --build
```

访问：
- 前端： http://localhost:5173
- 后端： http://localhost:8000/docs
- 数据库： ./data/app.db（持久化到宿主机）

详见根目录 `DEPLOY.md`。
