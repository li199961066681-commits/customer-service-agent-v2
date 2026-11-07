# Prompt 设计文档

## 1. 三个 Prompt 的角色分工

| Prompt | 用途 | 输出 |
| --- | --- | --- |
| CLASSIFY_SYSTEM | 意图分类（few-shot） | `{intent, confidence, missing_slots}` |
| RESPOND_SYSTEM | 回答合成 + 护栏 | 带【资料N】引用的回答文本 |
| SELF_CHECK_SYSTEM | 质检拟回复是否 grounded | `{self_check, reason}` |

设计原则：**每个 Prompt 只干一件事**，分类/生成/质检分离，互不污染。

## 2. CLASSIFY_SYSTEM（意图分类）

五类意图与业务优先级（由真实 LLM 结构化输出）：

| 优先级 | 意图 | 触发特征 | 动作 |
| --- | --- | --- | --- |
| 1 | human | 投诉/骗子/曝光/垃圾 + 情绪词 | 无条件转人工 |
| 2 | faq | 退款/物流/发票/保修/退货 等知识词 | RAG 检索回答 |
| 3 | clarify | 意图明确但缺槽位（如"我要退款"无订单号） | 反问补槽位 |
| 4 | action | 查/建/改工单 + 工单号或订单号 | 调用工具 |
| 5 | other | 天气/闲聊/写诗 等无关内容 | 兜底引导 |

few-shot 示例（真实 LLM 版提示词骨架）：

```
你是电商客服意图分类器。请判断用户意图，输出 JSON：
{"intent": "faq|action|clarify|human|other", "confidence": 0-1, "missing_slots": []}
示例：
用户：订单超过7天没收到货 → {"intent":"faq","confidence":0.9,"missing_slots":[]}
用户：我要退款 → {"intent":"clarify","confidence":0.8,"missing_slots":["order_id"]}
```

## 3. RESPOND_SYSTEM（回答合成护栏）

硬约束：

1. **只准用检索资料回答**：不得编造资料外的信息
2. **必须带引用**：每条依据标注【资料N】，N 对应检索命中的序号
3. **不确定就说不知道**：资料不足时明说「暂时无法确认」，绝不硬答
4. **友好收尾**：结尾提供进一步帮助入口

## 4. SELF_CHECK_SYSTEM（质检）

对拟回复做二次校验，回答两个问题：

- 回复是否引用了检索资料（【资料N】）？
- 回复内容是否都在资料范围内（无幻觉）？

输出 `{"self_check": "OK"}` 或 `{"self_check": "NOT_OK", "reason": ...}`。
NOT_OK 触发升级转人工——把「LLM 可能说错」这一不确定性交给产品兜底。

## 5. 真实 LLM 的实现

- `OpenAICompatLLM` 使用 `json_object` 模式 + 宽容量解析（兼容模型输出多余文字），再用 Pydantic 校验
- 未配置 `LLM_API_KEY` 时构造抛 `ValueError`，CLI 直接提示配置错误
- 没有 Mock 切换；测试中没有 Key 时跳过需要真实模型的端到端用例
