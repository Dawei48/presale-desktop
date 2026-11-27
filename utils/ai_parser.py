"""
AI 列名智能解析 —— 调用 DeepSeek 识别各电商平台 CSV 列名
规则匹配搞不定的列名，交给 AI 语义识别
"""
import json
import urllib.request

# 标准字段定义（AI 返回的映射目标）
STANDARD_FIELDS = {
    "order_no":       "订单号/订单编号/交易号",
    "customer":       "客户姓名/收货人/收件人/买家昵称",
    "product":        "产品名称/商品标题/宝贝标题",
    "spec":           "规格/规格名称/款式/尺寸/SKU",
    "quantity":       "购买数量/件数",
    "created_at":     "下单时间/付款时间/成交时间",
    "notes":          "买家留言/备注",
    "receiver_phone": "收货手机/联系电话/手机号",
    "receiver_addr":  "收货地址/详细地址",
    "amount":         "实付金额/订单金额/应付金额",
}

# AI 提示词模板
_SYSTEM_PROMPT = """你是电商订单数据字段识别助手。用户给你一个 CSV 文件的列名列表，你需要判断每个列名对应哪个标准字段。

标准字段只有这 10 个（必须用这些 key）：
- order_no: 订单号、订单编号、交易号、订单ID
- customer: 客户姓名、收货人、收件人、买家昵称、用户名
- product: 产品名称、商品标题、宝贝标题、商品名称
- spec: 规格、规格名称、款式、尺寸、SKU、颜色分类
- quantity: 购买数量、件数、数量
- created_at: 下单时间、付款时间、成交时间、创建时间
- notes: 买家留言、备注、订单备注、买家备注
- receiver_phone: 收货手机、收货人电话、联系电话、手机号
- receiver_addr: 收货地址、详细地址、地址
- amount: 实付金额、订单金额、应付金额、商品金额、价格

规则：
1. 只返回 JSON 对象，键是标准字段名，值是原 CSV 列名，不要任何其他文字。
2. 只映射你确定能对应的列；无法对应的列不要出现在结果里。
3. 示例输入 ["订单编号","宝贝标题","买家昵称","购买数量","成交时间"] 应返回 {"order_no":"订单编号","product":"宝贝标题","customer":"买家昵称","quantity":"购买数量","created_at":"成交时间"}
"""


def parse_headers_with_ai(headers, api_key, api_url=None, model=None):
    """
    用 AI 把 CSV 列名映射到标准字段。
    返回 dict: {标准字段: 原列名}，失败返回 {}
    """
    if not api_key:
        return {}

    from config import DEEPSEEK_API_URL, DEEPSEEK_MODEL
    api_url = api_url or DEEPSEEK_API_URL
    model = model or DEEPSEEK_MODEL

    headers_text = json.dumps(headers, ensure_ascii=False)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": headers_text},
        ],
        "temperature": 0,
        "max_tokens": 300,
        "response_format": {"type": "json_object"},
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        # DeepSeek 返回的可能是纯 JSON 或带 ```json 包裹
        content = content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:]
        mapping = json.loads(content)
        # 只保留标准字段，且值必须在原列名里
        cleaned = {}
        for key in STANDARD_FIELDS:
            if key in mapping and mapping[key] in headers:
                cleaned[key] = mapping[key]
        return cleaned
    except Exception:
        return {}


def merge_mapping(rule_mapping, ai_mapping):
    """
    合并规则匹配和 AI 匹配结果。
    规则匹配优先（快、准、免费），AI 结果补充规则没匹配上的字段。
    """
    merged = dict(rule_mapping)
    for field, col in ai_mapping.items():
        if field not in merged:
            merged[field] = col
    return merged
