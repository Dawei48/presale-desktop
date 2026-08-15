"""
UI 主题 & 样式常量
「青花瓷」主题 —— 景德镇陶瓷 × 现代工具
暖灰中性 + 青花钴蓝主色 + 釉色语义色
设计依据：ui-ux-pro-max skill（配色 token 化、字号 ≥12px、4/8 间距节奏、暖灰中性）
"""
import customtkinter as ctk

# ── 主题设置 ──────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── 配色板 ────────────────────────────────────
class Colors:
    # 主色（青花钴蓝）
    PRIMARY       = "#2D5AA8"
    PRIMARY_HOVER = "#23478A"
    PRIMARY_LIGHT = "#EDF3FB"
    PRIMARY_DIM   = "#DCE8F7"

    # 语义色（陶瓷釉色）
    SUCCESS       = "#1F9D6E"   # 青釉绿
    SUCCESS_LIGHT = "#E2F5EC"
    SUCCESS_HOVER = "#177A55"
    WARNING       = "#C98A2E"   # 窑变黄
    WARNING_LIGHT = "#F8EFDD"
    WARNING_HOVER = "#A97024"
    DANGER        = "#D9544D"   # 朱砂红
    DANGER_LIGHT  = "#FBE8E6"
    DANGER_HOVER  = "#B93F38"
    DANGER_LIGHT_HOVER = "#F5D7D4"
    INFO          = "#4F6FA8"   # 靛青
    INFO_LIGHT    = "#E7EDF7"

    # 侧边栏（深青花藏青）
    SIDEBAR_BG      = "#1B2A44"
    SIDEBAR_HOVER   = "#243654"
    SIDEBAR_ACTIVE  = "#2D5AA8"
    SIDEBAR_TEXT    = "#A8B6CE"
    SIDEBAR_TEXT_HI = "#F5F7FA"

    # 背景（暖灰，呼应陶土质感）
    BG_MAIN   = "#F7F5F1"
    BG_CARD   = "#FFFFFF"
    BG_INPUT  = "#F3F1EC"
    BG_HOVER  = "#F0EEE9"

    # 文字（暖黑 / 暖灰）
    TEXT_PRIMARY   = "#2B2A26"
    TEXT_SECONDARY = "#5C5A54"
    TEXT_MUTED     = "#9A968E"
    TEXT_WHITE     = "#FFFFFF"

    # 边框（暖灰）
    BORDER       = "#E4E1DA"
    BORDER_FOCUS = "#2D5AA8"
    BORDER_LIGHT = "#F0EEE9"

# ── 字体 ──────────────────────────────────────
class Fonts:
    FAMILY  = "Microsoft YaHei"
    TITLE   = (FAMILY, 20, "bold")
    H1      = (FAMILY, 17, "bold")
    H2      = (FAMILY, 15, "bold")
    BODY    = (FAMILY, 14)
    BODY_B  = (FAMILY, 14, "bold")
    SMALL   = (FAMILY, 12)
    SMALL_B = (FAMILY, 12, "bold")
    TINY    = (FAMILY, 11)
    NUM     = (FAMILY, 24, "bold")   # 统计数字

# ── 间距（4/8 节奏）────────────────────────────
class Spacing:
    XS   = 4
    SM   = 8
    MD   = 12
    LG   = 16
    XL   = 24
    XXL  = 32
    XXXL = 48

# ── 圆角 ──────────────────────────────────────
class Radius:
    SM   = 8
    MD   = 10
    LG   = 14
    XL   = 18
    FULL = 999
