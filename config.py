# -*- coding: utf-8 -*-
"""全局配置：一切可调参数集中于此。

- 优先读取项目根目录 .env（若存在），否则使用下方默认值。
- LLM 使用真实 API（DeepSeek，OpenAI 兼容协议）；必须配置 LLM_API_KEY。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（本文件所在目录的上一级）
ROOT_DIR = Path(__file__).resolve().parent

# 自动加载 .env（存在才加载，不存在静默跳过）
load_dotenv(ROOT_DIR / ".env")


def _get(key: str, default: str = "") -> str:
    """读取环境变量，空值归一化为空字符串。"""
    val = os.getenv(key, default)
    return val if val is not None else ""


# ---------- LLM ----------
LLM_API_KEY = _get("LLM_API_KEY", "")
LLM_BASE_URL = _get("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = _get("LLM_MODEL", "deepseek-chat")
LLM_TEMPERATURE = float(_get("LLM_TEMPERATURE", "0.2"))

# ---------- Embedding（BGE-M3）----------
EMBED_API_KEY = _get("EMBED_API_KEY", "")
EMBED_BASE_URL = _get("EMBED_BASE_URL", "https://api.siliconflow.cn/v1")
EMBED_MODEL = _get("EMBED_MODEL", "BAAI/bge-m3")

# ---------- 短期记忆（Redis）----------
REDIS_URL = _get("REDIS_URL", "redis://localhost:6379/0")

# ---------- 可观测性（Langfuse）----------
LANGFUSE_PUBLIC_KEY = _get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = _get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = _get("LANGFUSE_HOST", "https://cloud.langfuse.com")

# ---------- 业务参数 ----------
# 检索 grounded 门槛：达到该相似度才认为「有依据可作答」。
# 稀疏 TF 向量的相似度天然偏低（≈0.25~0.8），标定实验见 docs/评测记录.md。
GROUNDED_THRESHOLD = float(_get("GROUNDED_THRESHOLD", "0.25"))
# 短期记忆保留最近 N 轮对话
MAX_CONTEXT_TURNS = int(_get("MAX_CONTEXT_TURNS", "10"))

# ---------- 路径 ----------
DATA_DIR = ROOT_DIR / "data"
KB_PATH = DATA_DIR / "kb.json"
TICKET_DB_PATH = DATA_DIR / "tickets.db"
TRACE_LOG_PATH = DATA_DIR / "trace_log.jsonl"

# 首次运行自动创建 data 目录（SQLite / Chroma / Trace 都依赖它）
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 判定 LLM 是否可用（必须配置 Key）
LLM_READY = bool(LLM_API_KEY)
EMBED_READY = bool(EMBED_API_KEY)
