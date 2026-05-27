"""
放心预 - 预售管理系统 v1.3.1
桌面版 · 云端/本地 SQLite · 品牌→产品→订单 · 团队协作 · Word 导出
"""
import sys
import os

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))


def get_database():
    """根据配置返回云端或本地数据库"""
    from config import USE_CLOUD
    if USE_CLOUD:
        try:
            from database_cloud import Database
            db = Database()
            # 测试连接
            db.has_users()
            print("✅ 已连接云端数据库")
            return db
        except Exception as e:
            print(f"⚠️ 云端连接失败({e})，回退到本地数据库")
            from database import Database
            return Database()
    else:
        from database import Database
        return Database()


def launch_app():
    import customtkinter as ctk
    from config import BASE_DIR

    db = get_database()
    root = ctk.CTk()
    root.title("放心预")
    root.geometry("440x640")
    root.resizable(False, False)

    # 窗口图标
    icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass

    def go_main(user_info):
        for w in root.winfo_children():
            w.destroy()
        root.geometry("1100x700")
        root.minsize(900, 600)
        root.resizable(True, True)
        from ui.main_window import MainWindow
        MainWindow(root, user_info, db=db)

    if db.has_users():
        from ui.login_window import LoginWindow
        LoginWindow(root, on_success=go_main, db=db).pack(fill="both", expand=True)
    else:
        from ui.login_window import SetupWindow
        SetupWindow(root, on_done=go_main, db=db).pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    launch_app()
