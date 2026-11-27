"""
预售管理系统 - 全局配置

只留新架构（pywebview）真正用到的东西。旧的 CustomTkinter 界面、
云端 Supabase 分支已移除，见 tag archive/legacy-ctk。
"""
import os
import sys

APP_NAME = "放心预"
APP_VERSION = "2.0.1"

if getattr(sys, "frozen", False):
    BUNDLE_DIR = sys._MEIPASS                       # PyInstaller 解压目录
    BASE_DIR = os.path.dirname(sys.executable)      # exe 所在目录
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = BUNDLE_DIR


def _find_resource(relative_path):
    """资源文件优先从打包目录找，找不到从 exe 目录找。"""
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

# ── AI 解析（可选）─────────────────────────────
# key 优先级：环境变量 > data/ai_key.txt（.gitignore 已排除）
# 仓库里不放任何 key。
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
if not DEEPSEEK_API_KEY:
    _ai_key_file = os.path.join(DATA_DIR, "ai_key.txt")
    if os.path.exists(_ai_key_file):
        try:
            with open(_ai_key_file, "r", encoding="utf-8") as f:
                DEEPSEEK_API_KEY = f.read().strip()
        except OSError:
            pass

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


def ai_enabled():
    """AI 解析是否可用。"""
    return bool(DEEPSEEK_API_KEY)
