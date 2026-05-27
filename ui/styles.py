"""
UI 主题 & 样式常量
现代简约配色，参考 Linear / Notion 风格
"""
import customtkinter as ctk

# ── 主题设置 ──────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── 配色板 ────────────────────────────────────
class Colors:
    # 主色
    PRIMARY       = "#2563EB"
    PRIMARY_HOVER = "#1D4ED8"
    PRIMARY_LIGHT = "#EFF6FF"
    PRIMARY_DIM   = "#DBEAFE"

    # 语义色
    SUCCESS       = "#10B981"
    SUCCESS_LIGHT = "#D1FAE5"
    WARNING       = "#F59E0B"
    WARNING_LIGHT = "#FEF3C7"
    DANGER        = "#EF4444"
    DANGER_LIGHT  = "#FEE2E2"
    INFO          = "#6366F1"
    INFO_LIGHT    = "#E0E7FF"

    # 侧边栏
    SIDEBAR_BG    = "#0F172A"
    SIDEBAR_HOVER = "#1E293B"
    SIDEBAR_ACTIVE= "#1E40AF"
    SIDEBAR_TEXT  = "#CBD5E1"
    SIDEBAR_TEXT_HI = "#F1F5F9"

    # 背景
    BG_MAIN       = "#F8FAFC"
    BG_CARD       = "#FFFFFF"
    BG_INPUT      = "#F1F5F9"

    # 文字
    TEXT_PRIMARY   = "#0F172A"
    TEXT_SECONDARY = "#475569"
    TEXT_MUTED     = "#94A3B8"
    TEXT_WHITE     = "#FFFFFF"

    # 边框
    BORDER        = "#E2E8F0"
    BORDER_FOCUS  = "#2563EB"

# ── 字体 ──────────────────────────────────────
class Fonts:
    FAMILY = "Microsoft YaHei"
    TITLE   = (FAMILY, 20, "bold")
    H1      = (FAMILY, 16, "bold")
    H2      = (FAMILY, 14, "bold")
    BODY    = (FAMILY, 13)
    BODY_B  = (FAMILY, 13, "bold")
    SMALL   = (FAMILY, 11)
    SMALL_B = (FAMILY, 11, "bold")
    TINY    = (FAMILY, 10)

# ── 间距 ──────────────────────────────────────
class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32

# ── 圆角 ──────────────────────────────────────
class Radius:
    SM = 6
    MD = 8
    LG = 12
    XL = 16
    FULL = 999
