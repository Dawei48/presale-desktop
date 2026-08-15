"""
预售管理系统 - 全局配置
"""
import os
import sys

APP_NAME = "放心预"
APP_VERSION = "1.6.0"
APP_SUBTITLE = "预售管理系统"

if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS  # PyInstaller解压目录
    BASE_DIR = os.path.dirname(sys.executable)  # exe所在目录
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = BUNDLE_DIR

# 资源文件优先从打包目录找，找不到从exe目录找
def _find_resource(relative_path):
    """在打包目录和exe目录中查找资源"""
    p1 = os.path.join(BUNDLE_DIR, relative_path)
    if os.path.exists(p1):
        return p1
    p2 = os.path.join(BASE_DIR, relative_path)
    if os.path.exists(p2):
        return p2
    return p1  # 返回默认路径（即使不存在）

DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "presale.db")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# ── 云端模式 ──────────────────────────────────
USE_CLOUD = True  # True=Supabase云端, False=本地SQLite

SUPABASE_URL = "https://xhcbsvfysuxqzfudkkwl.supabase.co"
SUPABASE_KEY = "sb_publishable_CqIEa-ijlbZ3SbbEYXrTsQ_ZRR91HtB"

DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "admin123"
DEFAULT_ADMIN_NAME = "管理员"

# 订单状态（对齐小程序）
ORDER_STATUSES = {
    "pending":   "未发货",
    "shipped":   "已发货",
    "completed": "已完成",
    "cancelled": "已取消",
}

STATUS_COLORS = {
    "pending":   "#F59E0B",
    "shipped":   "#3B82F6",
    "completed": "#10B981",
    "cancelled": "#EF4444",
}

FONT_FAMILY = "Microsoft YaHei"

# ── AI 解析配置 ──────────────────────────────
# AI key 优先级：环境变量 > 本地文件（data/ai_key.txt，已被 .gitignore 排除）
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
if not DEEPSEEK_API_KEY:
    _ai_key_file = os.path.join(DATA_DIR, "ai_key.txt")
    if os.path.exists(_ai_key_file):
        try:
            with open(_ai_key_file, "r", encoding="utf-8") as f:
                DEEPSEEK_API_KEY = f.read().strip()
        except Exception:
            pass

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ── 发货期限（天，订单级可单独覆盖）────────
# 订单超过自身发货期限仍未发货，会在列表中标红提示
SHIP_DEADLINE_DAYS = 30   # 默认发货期限（无平台信息时用）
SHIP_WARN_DAYS = 3        # 剩余 ≤3 天时黄色预警

# 各平台默认发货期限（导入 CSV 时按检测到的平台自动设置）
PLATFORM_SHIP_DAYS = {
    "taobao": 3,    # 淘宝默认 72 小时 ≈ 3 天
    "pdd": 3,       # 拼多多默认 72 小时
    "douyin": 2,    # 抖音 48 小时 = 2 天
    "unknown": 30,  # 未知平台/预售商品默认 30 天
}

def ai_enabled():
    """AI 解析是否可用"""
    return bool(DEEPSEEK_API_KEY)
