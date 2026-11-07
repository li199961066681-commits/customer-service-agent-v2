# -*- coding: utf-8 -*-
"""生成 v2《实训报告.docx》：八章结构 + 架构图 + 评测/阈值标定表。

排版规范（word skill 学习总结场景 + 通用规则）：
- 黑体 Title 18pt 居中加粗 / H1 14pt / H2 12pt；宋体正文 12pt，1.5 倍行距，首行缩进 2 字符
- A4，上下左右 2.5cm；页脚居中 PAGE 域；阿拉伯小数层级编号
- 表格：浅灰表头 D9D9D9，cantSplit + tblHeader，单元格垂直居中，表内零缩进 10.5pt
- 字体 Theme 遮蔽修复（删除 asciiTheme/eastAsiaTheme 再设 ascii/eastAsia）
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DOCS = ROOT / "docs"

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

TITLE_FONT = "黑体"
BODY_FONT = "宋体"
ASCII_FONT = "Times New Roman"
HEADER_BG = "D9D9D9"
BLACK = RGBColor(0, 0, 0)


# ---------- 底层工具 ----------
def _set_run(run, east, size, bold=False, color=BLACK, ascii_f=ASCII_FONT):
    run.font.name = ascii_f
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rPr = run._element.get_or_add_rPr()
    for tag in ("a:asciiTheme", "a:eastAsiaTheme", "a:hAnsiTheme", "a:cstheme"):
        for el in rPr.findall(qn(tag)):
            rPr.remove(el)
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), ascii_f)
    rFonts.set(qn("w:hAnsi"), ascii_f)
    rFonts.set(qn("w:eastAsia"), east)


def _para(doc, text, size=12, bold=False, align=None, indent_chars=2,
          space_after=0, keep_next=False, east=BODY_FONT):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.5
    pf.space_before = Pt(0)
    pf.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    if indent_chars:
        pPr = p._p.get_or_add_pPr()
        ind = pPr.find(qn("w:ind"))
        if ind is None:
            ind = OxmlElement("w:ind")
            pPr.append(ind)
        ind.set(qn("w:firstLineChars"), str(indent_chars * 100))
        ind.set(qn("w:firstLine"), str(int(indent_chars * 24)))
    if keep_next:
        pf.keep_with_next = True
    run = p.add_run(text)
    _set_run(run, east, size, bold)
    return p


def _heading(doc, text, level=1):
    sizes = {0: 18, 1: 14, 2: 12}
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.5
    pf.space_before = Pt(14 if level == 1 else 8)
    pf.space_after = Pt(6 if level == 1 else 4)
    pf.keep_with_next = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if level == 0 else WD_ALIGN_PARAGRAPH.LEFT
    run = p.add_run(text)
    _set_run(run, TITLE_FONT, sizes.get(level, 12), bold=True)
    return p


def _table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # 表头
    hdr = t.rows[0]
    trPr = hdr._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), HEADER_BG)
        cell._tc.get_or_add_tcPr().append(shd)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run(h)
        _set_run(run, BODY_FONT, 10.5, bold=True)
    # 数据行
    for row in rows:
        r = t.add_row()
        trPr = r._tr.get_or_add_trPr()
        cantSplit = OxmlElement("w:cantSplit")
        trPr.append(cantSplit)
        for i, val in enumerate(row):
            cell = r.cells[i]
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(str(val))
            _set_run(run, BODY_FONT, 10.5)
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    return t


def _caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.0
    run = p.add_run(text)
    _set_run(run, BODY_FONT, 10.5)


def _figure(doc, path, caption):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(path), width=Cm(15))
    _caption(doc, caption)


def _setup_footer(doc):
    for section in doc.sections:
        footer = section.footer
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        _set_run(run, BODY_FONT, 9)
        fld1 = OxmlElement("w:fldChar")
        fld1.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.text = "PAGE"
        fld2 = OxmlElement("w:fldChar")
        fld2.set(qn("w:fldCharType"), "end")
        run._r.append(fld1)
        run._r.append(instr)
        run._r.append(fld2)


def _setup_page(doc):
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.5)
    sec.bottom_margin = Cm(2.5)
    sec.left_margin = Cm(2.5)
    sec.right_margin = Cm(2.5)


def main() -> None:
    doc = Document()
    _setup_page(doc)
    _setup_footer(doc)

    # ---------- 封面标题 ----------
    _heading(doc, "客服工单处理 Agent 项目实训报告", 0)
    _para(doc, "（C 题 · LangGraph 状态机架构 · Web UI + CLI · 方案一 Python 生态）", 12,
          align=WD_ALIGN_PARAGRAPH.CENTER, indent_chars=0, space_after=6)
    _para(doc, "开发人：黎尚高    学号：240200163    班级：24软件2", 12,
          align=WD_ALIGN_PARAGRAPH.CENTER, indent_chars=0, space_after=2)
    _para(doc, "完成日期：2026-11-07", 12,
          align=WD_ALIGN_PARAGRAPH.CENTER, indent_chars=0, space_after=12)
    doc.add_paragraph()

    # ---------- 1 实训概述 ----------
    _heading(doc, "1 实训概述", 1)
    _heading(doc, "1.1 实训目的", 2)
    _para(doc, "本实训围绕 C 题「客服工单处理 Agent」展开，目标是用 LangGraph 状态机搭建一个“知道自己不知道”的客服 Agent：以 LLM 为决策者（意图分类、工具选择、质检），以工具为执行者（知识检索、工单增改查），以两层存储维持记忆，以 Trace 保障可观测，并配置三层防御兜底，完整复现工业级客服 Agent 的核心链路。")
    _heading(doc, "1.2 开发环境", 2)
    _table(doc, ["项目", "选型"], [
        ["语言/运行时", "Python 3.13"],
        ["状态机编排", "LangGraph（StateGraph + 条件路由）"],
        ["数据校验", "Pydantic 2.14（AgentState 状态模型 + 结构化输出）"],
        ["知识库检索", "Chroma（自定义中文 embedding 函数）+ 本地词表向量降级"],
        ["长期存储", "SQLite（工单表 + 坐席队列表）"],
        ["短期记忆", "Redis（未配置时降级进程内 dict）"],
        ["LLM 接入", "DeepSeek（OpenAI 兼容协议，必须配置 LLM_API_KEY）"],
        ["可观测", "Langfuse（未配置时降级本地 Trace JSONL）"],
        ["演示界面", "Streamlit / CLI 双入口"],
    ])
    _heading(doc, "1.3 交付内容", 2)
    _para(doc, "本项目交付：完整可运行代码（8 个执行节点 + 2 处条件路由、4 个工具、两层存储、检索与观测层）、12 条评测用例与阈值标定实验、18 项单元测试、Web UI 与 CLI 演示、本实训报告与《零基础项目精读报告》。")

    # ---------- 2 需求分析 ----------
    _heading(doc, "2 需求分析", 1)
    _heading(doc, "2.1 功能需求", 2)
    _table(doc, ["编号", "需求", "说明"], [
        ["F1", "意图分类", "faq / action / clarify / human / other 五类，输出结构化结果与置信度"],
        ["F2", "条件路由", "按意图分流到检索、工具、追问、转人工、兜底五条链路"],
        ["F3", "知识库问答", "Top-3 检索 + grounded 阈值判定，回答强制带【资料N】引用"],
        ["F4", "工单操作", "查询 / 创建 / 更新工单状态，参数化 SQL 防注入"],
        ["F5", "澄清追问", "意图明确但缺订单号等槽位时反问，不瞎猜"],
        ["F6", "三层防御", "检索置信度 / LLM self-check / 敏感词拦截，不达标转人工"],
        ["F7", "转人工", "打包上下文写入坐席队列，生成体面转人工话术"],
        ["F8", "可观测", "全链路 Trace：输入、决策、工具、耗时"],
    ])
    _heading(doc, "2.2 非功能需求", 2)
    _para(doc, "必须配置 LLM_API_KEY 调用真实 DeepSeek；Redis/Chroma/Langfuse 均为可选增强，缺失时自动降级；评测可一键自动化，阈值有实验依据。")

    # ---------- 3 总体设计 ----------
    _heading(doc, "3 总体设计", 1)
    _heading(doc, "3.1 设计哲学", 2)
    _para(doc, "项目遵循三条设计哲学：一是 LLM 是决策者而不是回答机，每一步分类、路由、质检都是决策；二是每个动作都是工具，Agent 只负责“调哪个工具、传什么参数”，工具独立封装可测可换；三是兜底能力等于产品思维，客服错答代价极高，敢说“我不知道”并主动转人工的客服才是好客服。")
    _heading(doc, "3.2 系统架构", 2)
    _figure(doc, DOCS / "架构图.png", "图1  客服工单处理 Agent 状态机架构（示意）")
    _para(doc, "系统由一个 LangGraph 状态机（8 个执行节点 + 2 处条件路由）与四个支撑层组成：LLM 层（决策）、工具层（执行）、存储层（记忆与持久化）、观测层（留证）。全部节点共享同一个 Pydantic 状态对象 AgentState，节点之间只读状态、只写增量，天然解耦。")
    _heading(doc, "3.3 八节点 + 条件路由清单", 2)
    _table(doc, ["序号", "节点", "职责", "关键实现"], [
        ["1", "classify_intent", "五类意图分类，输出置信度", "LLM 结构化输出 + Pydantic 校验"],
        ["2", "conditional_edges", "按意图分流", "LangGraph add_conditional_edges"],
        ["3", "rag_search", "知识库 Top-3 检索 + grounded 标记", "向量库 + GROUNDED_THRESHOLD=0.25"],
        ["4", "tool_call", "选工具、传参、执行", "结构化输出 + Tool 注册表"],
        ["5", "clarify", "缺失槽位反问", "槽位列表 + 追问话术"],
        ["6", "escalate_check", "三层防御升级判定", "置信度 / self-check / 敏感词"],
        ["7", "respond", "回答合成（faq 走 LLM，action 走工具话术）", "Prompt 护栏 + _humanize_tool_result"],
        ["8", "escalate_human", "打包上下文写坐席队列", "SQLite queue 表"],
        ["9", "fallback", "无关话题兜底", "固定话术"],
    ])
    _heading(doc, "3.4 技术选型对照", 2)
    _table(doc, ["技术", "角色", "为什么选它（替代方案及理由）"], [
        ["LangGraph", "状态机编排", "单 Agent 多分支场景最贴合；手写循环分支难维护，CrewAI/AutoGen 是多 Agent 协作框架，LangChain Chain 表达不了循环分支"],
        ["Pydantic", "状态模型 + 结构化输出", "类型安全、fail fast；结构化输出是 LLM 决策格式化的基础"],
        ["Chroma", "知识库向量检索", "pip 零部署、可持久化；FAISS 默认不持久化，Milvus 需单独部署"],
        ["SQLite", "工单与队列持久化", "Python 内置零安装，单机实训足够；MySQL 属过度设计"],
        ["Redis", "短期会话记忆", "独立进程，Streamlit 刷新不丢状态；连不上自动降级"],
        ["Langfuse", "全链路 Trace", "开源可自托管；LangSmith 服务器在国外访问不稳"],
        ["DeepSeek", "LLM 决策", "真实模型负责分类/选工具/质检；Key 必填，没有离线规则 Mock"],
    ])

    # ---------- 4 详细设计与实现 ----------
    _heading(doc, "4 详细设计与实现", 1)
    _heading(doc, "4.1 LLM 层（决策者）", 2)
    _para(doc, "LLMClient 抽象基类（ABC）只暴露 chat() 与 structured() 两个接口：前者用于回答合成，后者强制 LLM 返回符合 Pydantic schema 的 JSON。OpenAICompatLLM 通过 json_object 模式加宽容量解析实现真实 DeepSeek 接入；没有规则 Mock；分类、选工具、质检全部由真实 DeepSeek 完成。结构化输出是“LLM 当决策者”的技术基石：分类结果必须形如 {\"intent\": \"faq\", \"confidence\": 0.9, \"missing_slots\": []}，非法 JSON 在入口即被拦截。")
    _heading(doc, "4.2 检索层（知识）", 2)
    _para(doc, "本地词表向量用客服领域词表 TF + L2 归一化实现可复现的中文相似度；ChromaBackend 注入自定义中文 embedding 函数，替换默认英文 MiniLM 模型，避免中文向量污染；未装 Chroma 时自动降级 numpy 内存后端。检索结果含 score 与 grounded 标记，由 GROUNDED_THRESHOLD=0.25 判定“是否有依据可作答”，不再使用 0.65 死配置。")
    _heading(doc, "4.3 工具层（执行者）", 2)
    _para(doc, "Tool 类统一封装函数、功能描述与 JSON Schema 参数规范，__call__ 返回 JSON 字符串。四个工具分别为 rag_search（知识检索）、query_ticket（查工单）、create_ticket（建工单）、update_ticket_status（改状态），底层全部参数化 SQL。tool_call 节点由 LLM 结构化输出选择工具与参数，respond 节点把工具 JSON 转成用户话术。")
    _heading(doc, "4.4 存储层（记忆）", 2)
    _para(doc, "ShortTermMemory 门面优先使用 Redis 保存最近 10 轮对话，连接失败自动降级进程内 dict（using_redis 属性可观测）；TicketStore 以 SQLite 维护工单表与坐席队列表，预置 TK001/TK002 种子工单，让 action 分支开箱可演示。")
    _heading(doc, "4.5 观测层（留证）", 2)
    _para(doc, "create_trace 工厂按配置选择 Langfuse 或本地 LocalTrace，后者把输入、节点决策、工具调用与耗时写入 data/trace_log.jsonl，CLI 以 --trace 查看。Trace 是回答“这个回复是怎么来的”的唯一证据链。")
    _heading(doc, "4.6 三层防御实现", 2)
    _para(doc, "escalate_check 为独立质检节点：层1 检索置信度，faq 分支无 grounded 命中即拒答转人工；层2 LLM self-check，仅对 faq 分支校验拟回复是否带【资料N】引用（action 回复来自工具天然有据）；层3 敏感词拦截，全分支扫描用户输入，投诉与愤怒情绪无条件转人工。三层分别管理知识缺口、LLM 幻觉与产品边界三类风险。")

    # ---------- 5 系统测试与结果 ----------
    _heading(doc, "5 系统测试与结果", 1)
    _heading(doc, "5.1 单元测试", 2)
    _para(doc, "编写 18 项 pytest 用例，覆盖五类路由、三层防御（含 self-check 直接构造状态）、4 个工具调用、SQLite 增改查与队列、检索排序与 grounded、短期记忆、真实 LLM 路由。有 Key 时 18 passed；无 Key 时 10 passed / 8 skipped。")
    _heading(doc, "5.2 端到端评测", 2)
    _para(doc, "12 条评测用例（E01~E12）覆盖五类意图与边界场景，每条断言路由正确性、回复关键内容与升级层正确性。评测结果：12/12 通过（100%），平均单轮耗时 2232.0ms（真实模型，2026-11-07）。")
    _table(doc, ["用例", "输入", "期望路由", "结果"], [
        ["E01~E04", "订单超时/退款规则/发票/退货", "faq（回答带【资料N】）", "通过"],
        ["E05~E07", "查/改/建工单", "action（工具执行）", "通过"],
        ["E08", "我要退款（缺订单号）", "clarify（追问）", "通过"],
        ["E09", "骗子投诉曝光", "human（转人工）", "通过"],
        ["E10", "今天天气", "other（兜底）", "通过"],
        ["E11", "你们支持货到付款吗（知识库未覆盖）", "层1 confidence 转人工", "通过"],
        ["E12", "太垃圾了要差评（情绪）", "转人工", "通过"],
    ])
    _heading(doc, "5.3 阈值标定实验", 2)
    _para(doc, "本地词表 TF 向量稀疏，相似度天然偏低。对 4 条 faq 用例扫描检索门槛：0.10~0.30 区间全部可作答，0.35 起开始漏答，故选 GROUNDED_THRESHOLD=0.25；旧版 0.65 死配置已删除。")
    _table(doc, ["阈值", "4 条 faq 用例可作答数", "结论"], [
        ["0.10", "4/4", "可作答"],
        ["0.15", "4/4", "可作答"],
        ["0.20", "4/4", "可作答"],
        ["0.25（当前）", "4/4", "可作答 + 挡住无关题"],
        ["0.30", "4/4", "可作答"],
        ["0.35", "3/4", "漏答"],
    ])

    # ---------- 6 遇到的问题与解决 ----------
    _heading(doc, "6 遇到的问题与解决", 1)
    _table(doc, ["序号", "问题", "根因", "解决方案"], [
        ["1", "self-check 报 KeyError", "Prompt 花括号被 format() 当占位符", "双花括号转义 {{ }}"],
        ["2", "invoke 返回 dict 无法点取字段", "LangGraph 内部以 dict 存状态", "AgentState.model_validate() 包装"],
        ["3", "Chroma 中文检索命中混乱", "默认英文 MiniLM embedding 对中文产生随机相似度", "注入自定义中文 embedding 函数并清库重建"],
        ["4", "能答的题被误推人工", "稀疏 TF 相似度达不到 0.65 阈值", "分离 GROUNDED_THRESHOLD=0.25，实验标定"],
        ["5", "正常回答被敏感词误伤", "扫描了回复文本（含 KB 原文的“投诉”）", "层3 只扫描 user_input"],
        ["6", "escalate_check 报 UnboundLocalError", "draft 变量定义位置丢失", "函数开头统一 draft = state.draft_reply or \"\""],
        ["7", "action 回复被 self-check 误杀", "工具话术无【资料N】引用", "self-check 仅 faq 分支执行"],
        ["8", "Trace 写入崩溃", "span 内 KbHit 列表不可 JSON 序列化", "递归 _to_jsonable 转 dict"],
    ])

    # ---------- 7 实训总结与收获 ----------
    _heading(doc, "7 实训总结与收获", 1)
    _para(doc, "本实训完整实现了一个以 LangGraph 状态机为核心的客服工单处理 Agent。与第一版手写 ReAct 循环相比，状态机方案把流程显式化为 8 个执行节点 + 2 处条件路由：分支逻辑不再藏在 if/else 里，节点各自独立可测，状态以单一 Pydantic 对象流转，新增能力只需注册新节点与新工具。")
    _para(doc, "收获集中在四个方面：一是理解了状态机编排 Agent 的价值，LLM 决策与代码执行分离；二是掌握了结构化输出、Prompt 护栏、self-check 质检等 LLM 工程关键手段；三是学会用实验说话——阈值标定、评测自动化、Trace 留证；四是积累了真实踩坑经验，包括中文 embedding 污染、提示词转义、类型转换等，每个问题都有根因与修复。")
    _para(doc, "后续改进方向：接入真实 DeepSeek 与 BGE-M3 做语义一致性回归、用 Langfuse 管理评测集、增加多轮槽位填充与更多工具（物流查询、优惠券等）。")

    # ---------- 8 附录 ----------
    _heading(doc, "8 附录", 1)
    _heading(doc, "8.1 运行说明", 2)
    _para(doc, "安装依赖后，双击 启动网页.vbs 在浏览器打开 Web UI；双击 启动命令行.bat 进入 CLI。也可执行 python main.py --chat \"问题\" 单轮处理、--interactive 多轮对话、--eval 跑评测、--queue 查看坐席队列、--trace 查看 Trace。复制 .env.example 为 .env 并配置 LLM_API_KEY；未配置 Key 时 Web/CLI 会阻断，不输出假回答。")
    _heading(doc, "8.2 目录结构", 2)
    _table(doc, ["目录/文件", "说明"], [
        ["app/", "状态机：graph.py 组装 8 执行节点 + 2 条件路由，nodes/ 各节点实现"],
        ["llm/", "base 抽象 / openai_compat 真实 DeepSeek 接入"],
        ["tools/", "Tool 类 + 4 工具注册表 + JSON Schema"],
        ["memory/", "短期记忆门面（Redis/内存）+ 长期记忆（SQLite）"],
        ["retrieval/", "本地词表向量 + Chroma/内存向量库 + 检索"],
        ["observable/", "Langfuse / 本地 Trace 工厂"],
        ["eval/", "12 条评测用例 + 阈值标定实验"],
        ["tests/", "18 项 pytest 单测"],
        ["main.py / streamlit_app.py", "CLI 与 Web UI 入口"],
    ])

    out = DOCS / "实训报告.docx"
    doc.save(out)
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
