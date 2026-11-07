# -*- coding: utf-8 -*-
"""CLI 入口（真实 LLM）。

运行前需要在 .env 配置 LLM_API_KEY。

用法：
  python main.py --chat "订单超过7天没收到货怎么办"   # 单轮处理（带节点轨迹）
  python main.py --interactive                       # 多轮对话
  python main.py --eval                              # 跑评测并生成 docs/评测记录.md
  python main.py --queue                             # 查看坐席队列（转人工记录）
  python main.py --trace                             # 查看最近 Trace
"""

import argparse
import json
import uuid

from app.runner import run_agent
from app.state import AgentState
from memory.long_term import TicketStore
from memory.short_term import ShortTermMemory


def run_once(text: str, session_id: str = "cli", memory: ShortTermMemory | None = None,
             verbose: bool = True) -> AgentState:
    """执行一轮：读历史 → 写当前用户消息 → 走一次状态机 → 写回复，全程记录 Trace。"""
    from observable.langfuse import create_trace

    # 先取历史（不含本轮输入），再写入本轮用户消息，避免重复
    history = memory.history(session_id) if memory else []
    if memory:
        memory.add_user(session_id, text)

    state = AgentState(
        user_input=text,
        session_id=session_id,
        messages=history,
        turn=len(history) // 2 + 1,
    )

    trace = create_trace("客服对话", session_id)
    try:
        final, node_trace = run_agent(state, trace)
    finally:
        trace.end()

    if memory:
        memory.add_assistant(session_id, final.reply or "")
    if verbose:
        print("节点轨迹:", " → ".join(node_trace))
    return final


def cmd_chat(args) -> None:
    mem = ShortTermMemory()
    print(f"[短期记忆] Redis 在线: {mem.using_redis}")
    # 单轮模式用一次性 session_id，避免把上次 --chat 的历史带进来
    final = run_once(args.chat, session_id=f"cli-{uuid.uuid4().hex[:8]}", memory=mem)
    print(f"[意图] {final.intent.intent if final.intent else '-'} "
          f"(置信度 {final.intent.confidence if final.intent else '-'})")
    if final.escalation and final.escalation.escalated:
        print(f"[升级] 层={final.escalation.layer} 原因={final.escalation.reason}")
    if final.kb_results:
        print("[检索] " + ", ".join(f"{h.id}({h.score})" for h in final.kb_results))
    print(f"\n客服回复：{final.reply}")


def cmd_interactive(args) -> None:
    mem = ShortTermMemory()
    session_id = f"interactive-{uuid.uuid4().hex[:8]}"
    print(f"[短期记忆] Redis 在线: {mem.using_redis}，session={session_id}，输入 exit 退出\n")
    while True:
        text = input("你 > ").strip()
        if text.lower() in ("exit", "quit", "退出"):
            break
        final = run_once(text, session_id=session_id, memory=mem)
        print(f"\n客服 > {final.reply}\n")


def cmd_eval(args) -> None:
    from config import LLM_READY

    if not LLM_READY:
        print("评测需要真实 LLM：请先在 .env 配置 LLM_API_KEY。")
        return
    from eval.runner import run_evaluation
    report = run_evaluation()
    print(json.dumps(report, ensure_ascii=False, indent=2))


def cmd_queue(args) -> None:
    store = TicketStore()
    rows = store.list_queue()
    print(f"坐席队列共 {len(rows)} 条：")
    for r in rows:
        print(f"  #{r['id']} {r['created_at']} 原因: {r['reason'][:50]}")


def cmd_trace(args) -> None:
    import os
    from config import TRACE_LOG_PATH
    if not os.path.exists(TRACE_LOG_PATH):
        print("暂无 Trace 记录（先运行一次 --chat 或 --eval）")
        return
    with open(TRACE_LOG_PATH, encoding="utf-8") as f:
        lines = f.readlines()
    print(f"最近 {min(3, len(lines))} 条 Trace：")
    for line in lines[-3:]:
        t = json.loads(line)
        print(f"  trace={t['trace_id']} name={t['name']} 耗时={t['duration_s']}s "
              f"节点数={len(t['events'])}")


def _clean_text(text: str) -> str:
    """清洗命令行输入：去掉首尾空白与误粘贴的直引号/弯引号。"""
    text = text.strip()
    for ch in ('"', "'", "“", "”", "‘", "’"):
        if text.startswith(ch) and text.endswith(ch):
            text = text[1:-1].strip()
    return text


def main() -> None:
    p = argparse.ArgumentParser(description="客服工单处理 Agent（LangGraph 状态机版）")
    p.add_argument("--chat", metavar="文本", nargs="+", help="单轮处理一条消息（可不用引号，多词自动拼接）")
    p.add_argument("--interactive", action="store_true", help="多轮对话模式")
    p.add_argument("--eval", action="store_true", help="运行评测并生成记录")
    p.add_argument("--queue", action="store_true", help="查看坐席队列")
    p.add_argument("--trace", action="store_true", help="查看最近 Trace")
    args = p.parse_args()

    if args.chat:
        args.chat = _clean_text(" ".join(args.chat))
        cmd_chat(args)
    elif args.interactive:
        cmd_interactive(args)
    elif args.eval:
        cmd_eval(args)
    elif args.queue:
        cmd_queue(args)
    elif args.trace:
        cmd_trace(args)
    else:
        p.print_help()
        print("\n示例：")
        print('  python main.py --chat 订单超过7天没收到货怎么办')
        print('  python main.py --interactive')
        print('  python main.py --eval')


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"\n缺少依赖：{e}\n请先执行：python -m pip install -r requirements.txt")
        raise SystemExit(1)
    except (RuntimeError, ValueError) as e:
        print(f"\n配置错误：{e}")
        raise SystemExit(1)
    except Exception as e:
        import traceback
        print(f"\n运行出错：{e}")
        traceback.print_exc()
        print("若为首次使用，请先执行：python -m pip install -r requirements.txt")
        raise SystemExit(1)
