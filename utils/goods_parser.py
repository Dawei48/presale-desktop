"""
商品名拆解 - 把陶瓷商品名拆成 工艺/画片/器型/窑口
词表驱动（data/category_words.json，可随时补词），最长词优先匹配
"""
import json
import os

_WORDS_CACHE = None


def load_words():
    """加载词表（带缓存）"""
    global _WORDS_CACHE
    if _WORDS_CACHE is not None:
        return _WORDS_CACHE
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "category_words.json")
    words = {"工艺": [], "画片": [], "器型": [], "后缀": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k in words:
                words[k] = data.get(k, [])
    except Exception:
        pass
    _WORDS_CACHE = words
    return words


def parse_goods_name(name, words=None):
    """拆解商品名 → {工艺, 画片, 器型, 窑口, 原始}

    例: "XX窑 青花釉里红 缠枝金刚莲 盖碗 景德镇纯手工手绘茶具瓷器"
      → 工艺=青花釉里红, 画片=缠枝金刚莲(若词表含), 器型=盖碗, 窑口=XX窑
    """
    if words is None:
        words = load_words()
    name = (name or "").strip()
    result = {"工艺": "", "画片": "", "器型": "", "窑口": "", "原始": name}
    if not name:
        return result

    s = name
    # 1. 剥营销后缀
    for suf in sorted(words.get("后缀", []), key=len, reverse=True):
        s = s.replace(suf, "")
    s = s.strip(" ·、，,。_- ")

    # 2. 最长词优先，依次提取 工艺 → 器型 → 画片
    for field in ("工艺", "器型", "画片"):
        for w in sorted(words.get(field, []), key=len, reverse=True):
            if w in s:
                result[field] = w
                s = s.replace(w, "", 1)
                break

    # 3. 剩下的当作窑口（清理空白与标点）
    result["窑口"] = s.strip(" ·、，,。_- ")
    return result


def merge_key(parsed):
    """生成合并键：工艺|画片|器型|窑口（相同才合并）"""
    return "|".join([
        parsed.get("工艺", ""),
        parsed.get("画片", ""),
        parsed.get("器型", ""),
        parsed.get("窑口", ""),
    ])
