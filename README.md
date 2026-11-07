# 客服工单处理 Agent（LangGraph 状态机 · Web UI + 真实 LLM）

基于 **LangGraph 状态机** 的客服工单处理 Agent：意图分类 → 条件路由 → RAG 检索 / 工具调用 / 澄清追问 → 三层防御升级判定 → 回答合成。

**主入口是浏览器 Web UI**；CLI 只保留给开发和调试。实训单允许“本地 CLI / Web UI / 部署链接”三选一，本项目选 **Web UI（Streamlit）**。

## 两种启动方式（都支持双击）

| 启动方式 | 双击文件 | 打开后 |
| --- | --- | --- |
| Web UI（推荐演示） | `启动网页.vbs` | 自动打开浏览器 `http://localhost:8501`，在页面输入框对话 |
| CLI（调试看轨迹） | `启动命令行.bat` | 打开命令行交互模式，输入问题看每轮节点轨迹 |
| 页面卡住时 | `重启网页.bat` | 停止旧 Web 进程 → 重新启动 → 打开浏览器 |

启动前确认项目根目录 `.env` 里有你自己的 DeepSeek Key：

```ini
LLM_API_KEY=sk-你的Key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

没有 Key 时：两个启动脚本都会打开 `.env` 让你填写并退出；Web 页面本身也会阻断对话，不会输出假回答。

## 手动启动（可选）

```powershell
streamlit run streamlit_app.py
```

浏览器打开终端提示的地址（默认 `http://localhost:8501`）。

## CLI（可选，仅调试）

```powershell
python main.py --chat "退款规则是什么"
python main.py --interactive
python main.py --eval
python main.py --queue
python main.py --trace
```

> `--chat` 适合快速看节点轨迹；正式演示用浏览器。

## 运行前必须配置

复制 `.env.example` 为 `.env`（如果还没有），填写你自己的 DeepSeek Key：

```powershell
Copy-Item .env.example .env
notepad .env
```

`.env` 已在 `.gitignore` 中，不会被提交。没有 Key 时不会启动对话。

## 上传 GitHub 前检查

- 本仓库**不包含 `.env`**，只提交 `.env.example`；克隆后复制为 `.env` 再填自己的 Key。
- 不提交 `venv/`、`data/tickets.db`、`data/trace_log.jsonl`、`data/chroma/`、日志和缓存。
- `data/kb.json` 必须提交（知识库本体）。
- `日报/`、`docs/` 是交付物，正常提交。

首次上传：

```powershell
git add .
git commit -m "feat: 客服工单处理 Agent（LangGraph + Web UI + 真实 LLM）"
git remote add origin https://github.com/你的用户名/仓库名.git
git push -u origin main
```

## 可选增强（都不是跑通的前提）

| 组件 | 作用 | 不配置时 |
| --- | --- | --- |
| Redis | 短期记忆跨进程持久化 | 自动降级为进程内 dict |
| Chroma | 向量库持久化 | 自动降级为 numpy 内存向量 |
| Langfuse | 云端 Trace | 自动降级为 `data/trace_log.jsonl` |
| BGE-M3 | 真实语义 embedding | 当前使用本地词表向量（接口预留） |
| Docker | 打包运行环境 | 本地启动不需要 |

## Docker（可选，Web）

```powershell
docker compose up --build
# 打开 http://localhost:8501
```

Compose 会先等待 Redis 健康检查通过，再启动 Web 应用；`data/kb.json` 会保留，`venv/`、`data/tickets.db`、`data/chroma/` 不会打进镜像。

## 目录结构

```
├── streamlit_app.py    # Web UI 主入口（浏览器对话）
├── 启动网页.vbs         # 双击启动：检查 Key -> 后台启动 Web -> 开浏览器
├── app/                # 状态机：graph.py 组装节点 + runner.py 单次执行 + nodes/ 各节点 + safety.py
├── llm/                # LLM 层：base 抽象 / openai_compat 真实 DeepSeek
├── tools/              # 4 个工具 + Tool 类 + JSON Schema 参数规范
├── memory/             # 短期记忆（Redis，降级内存）+ 长期记忆（SQLite）
├── retrieval/          # 知识库 + 本地词表向量（BGE-M3 接口预留）+ Chroma/内存向量库
├── observable/         # Langfuse v5 Trace（未配置降级本地 JSONL）
├── eval/               # 12 条评测用例 + 阈值标定实验
├── tests/              # 18 条 pytest 单测（无 Key 时跳过 8 条 LLM 用例）
└── docs/               # 架构设计 / 工具接口 / Prompt 设计 / 评测记录 / 实训报告
```

## 页面能看到什么

- 对话区：用户/客服消息
- 侧边栏：模型、Redis 状态、session、清空会话
- 每轮可展开：节点轨迹、意图/置信度、检索命中、升级原因

## 验证结果

- 未配置 `LLM_API_KEY`：`pytest` 10 passed、8 skipped；Web 阻断对话
- 配置 `LLM_API_KEY`：18 条测试全部执行（其中 8 条真实调用 DeepSeek）
- 评测：`python main.py --eval` 需要真实 Key，通过率取决于模型表现
- 阈值：`GROUNDED_THRESHOLD=0.25`

## 常见运行问题

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| 双击后提示“需要配置 Key” | `.env` 里 `LLM_API_KEY` 为空 | 在打开的记事本里填写 Key，保存后重新双击 |
| 页面显示“未配置 LLM_API_KEY” | 同上，或保存后没重启 | 关闭启动窗口，重新双击 |
| `401` / `AuthenticationError` | Key 错误/过期/无余额 | 去 DeepSeek 重新创建 Key 或充值 |
| `Connection error` / `timeout` | 网络连不上 | 检查网络/代理 |
| `Redis 在线: False` | 没启动 Redis | 正常降级为内存记忆，不影响对话 |
| 页面一直转圈/半天没回答 | 旧 Streamlit 进程卡住，或模型请求超时 | **双击 `重启网页.bat`**；客户端已设 45 秒超时 |
| 端口 8501 被占用 | 已有 Streamlit 在跑 | 先双击 `停止网页.bat`，再启动 |
