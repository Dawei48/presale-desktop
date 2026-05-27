"""
预售管理系统 - 全局配置
"""
import os
import sys

APP_NAME = "放心预"
APP_VERSION = "1.3.1"
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
