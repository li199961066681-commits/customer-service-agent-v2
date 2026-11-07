# -*- coding: utf-8 -*-
"""生成 v2 架构图：LangGraph 8 执行节点 + 2 处条件路由 + 支撑层（PIL 白底分层框图）。

运行：python scripts/gen_arch_png.py
输出：docs/架构图.png
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "架构图.png"

W, H = 1500, 920
BG = (255, 255, 255)
BOX = (240, 248, 255)          # 浅蓝
BOX2 = (255, 250, 240)         # 浅橙（防御/支撑）
LINE = (70, 70, 70)
ACCENT = (31, 96, 196)
RED = (196, 43, 43)
GRAY = (120, 120, 120)

FONT_T = "C:/Windows/Fonts/simhei.ttf"
FONT_S = "C:/Windows/Fonts/msyh.ttc"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_T if bold else FONT_S, size)


def center_text(d: ImageDraw.ImageDraw, xy, text: str, fnt, fill=LINE) -> None:
    bbox = d.textbbox((0, 0), text, font=fnt)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    d.text((xy[0] - w / 2, xy[1] - h / 2), text, font=fnt, fill=fill)


def box(d: ImageDraw.ImageDraw, x, y, w, h, text: str, fill=BOX,
        outline=ACCENT, size=17, bold=False, tcolor=(20, 20, 20)) -> tuple:
    d.rectangle([x, y, x + w, y + h], fill=fill, outline=outline, width=2)
    center_text(d, (x + w / 2, y + h / 2), text, font(size, bold), tcolor)
    return (x, y, x + w, y + h)


def arrow(d: ImageDraw.ImageDraw, x1, y1, x2, y2, color=GRAY) -> None:
    d.line([x1, y1, x2, y2], fill=color, width=2)
    # 箭头三角（指向 (x2,y2)）
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    L = 10
    for da in (2.6, -2.6):
        px = x2 - L * math.cos(ang + da)
        py = y2 - L * math.sin(ang + da)
        d.line([x2, y2, px, py], fill=color, width=2)


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # ---- 顶部：用户输入 → 意图分类 ----
    box(d, 40, 30, 260, 54, "用户输入（Streamlit / CLI）", size=17, bold=True)
    box(d, 420, 30, 300, 54, "① classify_intent\nLLM 结构化输出决策", size=15, bold=True)
    arrow(d, 300, 57, 420, 57)
    arrow(d, 720, 57, 800, 57)

    # ---- 条件路由 ----
    box(d, 800, 30, 320, 54, "② conditional_edges 条件路由", size=16, bold=True, fill=BOX2)

    # ---- 五个分支（左→右）----
    bx, by, bw, bh = 40, 150, 240, 60
    box(d, bx, by, bw, bh, "faq → ③ rag_search\n知识库 Top-3 检索", size=14)
    box(d, bx, by + 120, bw, bh, "faq 回答\n⑦ respond（带【资料N】）", size=14)
    box(d, bx, by + 240, bw, bh, "⑥ escalate_check\n三层防御质检", size=14, fill=BOX2, outline=RED)

    box(d, 360, by, bw, bh, "action → ④ tool_call\n选工具 + 传参执行", size=14)
    box(d, 360, by + 120, bw, bh, "action 回答\n工具结果转用户话术", size=14)
    box(d, 360, by + 240, bw, bh, "⑥ escalate_check\n（action 也过敏感词层）", size=13, fill=BOX2, outline=RED)

    box(d, 680, by, bw, bh, "clarify → ⑤ clarify\n追问缺失槽位", size=14)
    box(d, 680, by + 120, bw, bh, "END\n（等用户补充）", size=14)

    box(d, 1000, by, bw, bh, "human → ⑧ escalate_human\n打包上下文写坐席队列", size=13, fill=BOX2, outline=RED)
    box(d, 1000, by + 120, bw, bh, "END", size=16, bold=True)

    box(d, 680, by + 260, bw, bh, "other → ⑨ fallback\n礼貌引导回业务", size=14)

    # ---- 连线：路由 → 分支 ----
    for yy in (by + 30, by + 150, by + 270):
        arrow(d, 1120, 84, 1120, yy + 0, color=GRAY)
    # 简化：画主竖线 + 各分支横线
    d.line([1120, 84, 1120, by + 320], fill=GRAY, width=2)
    for xx, yy in ((160, by + 30), (480, by + 30), (800, by + 30), (1120, by + 30), (800, by + 290)):
        d.line([1120, yy, xx, yy], fill=GRAY, width=2)
        arrow(d, xx, yy, xx, yy + 0, color=GRAY) if False else None
    # 分支起点箭头
    for xx, yy in ((160, by + 30), (480, by + 30), (800, by + 30), (1120, by + 30), (800, by + 290)):
        arrow(d, 1120, yy, xx, yy)

    # ---- faq 链路 ----
    arrow(d, 160, by + bh, 160, by + 120)
    arrow(d, 160, by + 180, 160, by + 240)
    arrow(d, 160, by + 300, 160, 620, color=RED)
    # action 链路
    arrow(d, 480, by + bh, 480, by + 120)
    arrow(d, 480, by + 180, 480, by + 240)
    arrow(d, 480, by + 300, 480, 620, color=RED)

    # ---- 升级判定 → END / 转人工 ----
    d.text((40, 630), "升级（confidence / self_check / sensitive）→ ⑧ 转人工", font=font(15, True), fill=RED)
    d.text((40, 660), "通过 → END（写记忆 + Trace）", font=font(15, True), fill=LINE)

    # ---- 右侧：支撑层 ----
    sx = 1280
    d.text((sx, 150), "支撑层（可插拔）", font=font(16, True), fill=LINE)
    layers = [
        ("LLM 决策", "DeepSeek 结构化输出"),
        ("4 个 Tool", "rag / query / create / update"),
        ("两层存储", "Redis 短期 + SQLite 长期"),
        ("知识库检索", "Chroma + 本地词表向量"),
        ("可观测 Trace", "Langfuse / 本地 JSONL"),
    ]
    yy = 185
    for t, s in layers:
        d.rectangle([sx, yy, sx + 190, yy + 52], fill=(245, 245, 245), outline=GRAY, width=1)
        center_text(d, (sx + 95, yy + 17), t, font(14, True), ACCENT)
        center_text(d, (sx + 95, yy + 36), s, font(11), GRAY)
        yy += 62

    # ---- 主标题 ----
    d.text((40, 700), "客服工单处理 Agent · LangGraph 状态机架构（示意）", font=font(26, True), fill=(0, 0, 0))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
