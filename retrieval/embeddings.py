# -*- coding: utf-8 -*-
"""Embedding 提供者：把文本转成向量。

- MockEmbedding：基于客服领域词表的 TF 向量（256 维），余弦相似度真实可用、
  可离线演示、可被评测用例复现——这是「语义检索」的零成本实现。
- BGE-M3（API）：配置 EMBED_API_KEY 后启用真实 embedding，代码路径已留好。

为什么用词表 TF 而不是随机哈希：
随机哈希向量之间余弦≈0，检索结果不可解释；词表 TF 让「退款/退货」与
「退款/物流」这类词面重叠可被度量，接近真实 embedding 的行为。
"""

import math
import re
from collections import Counter

# 客服领域 256 维固定词表（覆盖知识库与常见问法）
VOCAB = ("退款 退货 物流 发货 送达 时效 快递 运费 运费险 发票 保修 维修 账号 密码 登录 盗 "
         "投诉 升级 客服 订单 商品 签收 七天 无理由 凭证 上门取件 赔付 保险 赔付金额 电子 "
         "纸质 邮箱 家电 整机 部件 冻结 申诉 损失 处理 电话 48小时 24小时 72小时 工作 原路 "
         "返还 银行 到账 偏远 新疆 西藏 催 收货 取消 换货 补偿 差价 优惠券 红包 赠品 缺货 "
         "多久 几天 怎么 如何 为什么 能不能 可以 规则 流程 政策 请问 你好 谢谢 在吗 再见 "
         "帮我 查一下 查询 看看 申请 提交 审核 通过 失败 异常 信息 情况 尽快 加急 专员 "
         "不满意 骗子 诈骗 威胁 报警 起诉 曝光 差评 垃圾 道歉 要求 责任 赔偿 标准 依据 "
         "证据 截图 电话 隐私 安全 风险 冻结 封号 恢复 解封 修改 密码 验证码 手机号 绑定 "
         "收到 未收到 没收到 超过 承诺 卡住 停 催促 进度 更新 查询进度").split()


class MockEmbedding:
    """词表 TF 向量 + L2 归一化（余弦 = 点积）。"""

    DIM = len(VOCAB)
    INDEX = {w: i for i, w in enumerate(VOCAB)}

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.DIM
        for token in _tokenize(text):
            idx = self.INDEX.get(token)
            if idx is not None:
                vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class BgeM3Embedding:
    """BGE-M3 真实 embedding（OpenAI 兼容协议）。

    TODO: 配置 EMBED_API_KEY 后启用；当前仅声明接口，未配置时上层使用 Mock。"""

    def embed(self, text: str) -> list[float]:
        from config import EMBED_API_KEY
        if not EMBED_API_KEY:
            raise RuntimeError("EMBED_API_KEY 未配置，请使用 MockEmbedding 或填写 Key")
        from openai import OpenAI
        client = OpenAI(api_key=EMBED_API_KEY)
        resp = client.embeddings.create(model="BAAI/bge-m3", input=text)
        return resp.data[0].embedding


def _tokenize(text: str) -> list[str]:
    """极简中文切词：优先命中词表多字词，再按单字兜底。"""
    tokens = []
    rest = text
    while rest:
        matched = None
        for w in sorted(VOCAB, key=len, reverse=True):
            if rest.startswith(w):
                matched = w
                break
        if matched:
            tokens.append(matched)
            rest = rest[len(matched):]
        else:
            rest = rest[1:]  # 跳过无法匹配的单字（避免噪音）
    return tokens


def cosine(a: list[float], b: list[float]) -> float:
    """两个归一化向量的余弦相似度（点积）。"""
    return sum(x * y for x, y in zip(a, b))
