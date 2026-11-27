"""
UI 主题 & 样式常量
「暗色 Linear 风格」—— 近黑背景 + 灰阶文字 + 单一靛蓝主色
设计依据：Linear / Midday 设计系统（popular-web-designs 模板）
配色哲学：几乎全灰阶 + 一个主色，不用花哨语义色
"""
import customtkinter as ctk

# ── 主题设置 ──────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── 配色板 ────────────────────────────────────
class Colors:
    # 主色（正蓝，唯一饱和色，克制使用）
    PRIMARY       = "#3b82f6"
    PRIMARY_HOVER = "#60a5fa"
    PRIMARY_LIGHT = "#14223a"   # 暗蓝底（次要蓝系元素背景）
    PRIMARY_DIM   = "#1a2c4a"   # 稍亮暗蓝（hover）

    # 语义色（暗色适配）
    SUCCESS       = "#10b981"   # 绿
    SUCCESS_LIGHT = "#0d2a1f"
    SUCCESS_HOVER = "#34d399"
    WARNING       = "#f59e0b"   # 琥珀（预存提示）
    WARNING_LIGHT = "#2a1f0d"
    WARNING_HOVER = "#fbbf24"
    DANGER        = "#f87171"   # 红
    DANGER_LIGHT  = "#2a1515"
    DANGER_HOVER  = "#fca5a5"
    DANGER_LIGHT_HOVER = "#3a1c1c"
    INFO          = "#60a5fa"   # 亮蓝
    INFO_LIGHT    = "#14223a"

    # 侧边栏
    SIDEBAR_BG      = "#0f1011"
    SIDEBAR_HOVER   = "#1a1b1d"
    SIDEBAR_ACTIVE  = "#232528"
    SIDEBAR_TEXT    = "#8a8f98"
    SIDEBAR_TEXT_HI = "#f7f8f8"

    # 背景（层级从深到浅）
    BG_MAIN   = "#08090a"   # 页面最深
    BG_CARD   = "#0f1011"   # 卡片/面板/侧边栏
    BG_INPUT  = "#1a1b1d"   # 输入框/次级
    BG_HOVER  = "#232528"   # 悬停

    # 文字（从亮到暗）
    TEXT_PRIMARY   = "#f7f8f8"
    TEXT_SECONDARY = "#d0d6e0"
    TEXT_MUTED     = "#8a8f98"
    TEXT_WHITE     = "#ffffff"

    # 边框
    BORDER       = "#232528"
    BORDER_FOCUS = "#3b82f6"
    BORDER_LIGHT = "#1a1b1d"

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
