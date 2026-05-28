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
            db.has_users()
            print("✅ 已连接云端数据库")
            return db, None
        except Exception as e:
            import traceback
            err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            print(f"⚠️ 云端连接失败: {err}")
            # 写到文件方便排查
            try:
                with open("cloud_error.log", "w", encoding="utf-8") as f:
                    f.write(err)
            except Exception:
                pass
            from database import Database
            return Database(), err
    else:
        from database import Database
        return Database(), None


def launch_app():
    import customtkinter as ctk
    from config import BASE_DIR

    db, cloud_error = get_database()
    root = ctk.CTk()
    root.title("放心预")
    root.geometry("520x720")
    root.resizable(False, False)

    # 窗口图标
    from config import _find_resource
    icon_path = _find_resource("assets/icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception:
            pass

    def go_main(user_info):
        for w in root.winfo_children():
            w.destroy()
        root.geometry("1280x800")
        root.minsize(1000, 650)
        root.resizable(True, True)
        from ui.main_window import MainWindow
        MainWindow(root, user_info, db=db)

    # 云端连接状态
    mode_label = "🌐 云端模式" if cloud_error is None else "⚠️ 本地模式（云端连接失败）"

    if db.has_users():
        # 尝试自动登录
        auto_logged_in = False
        try:
            from ui.login_window import load_saved_login
            saved = load_saved_login()
            if saved:
                username, password = saved
                user = db.login(username, password)
                if user:
                    db.log("自动登录", f"用户 {user['username']} 自动登录", user["id"], user["username"])
                    go_main(user)
                    auto_logged_in = True
        except Exception:
            pass
        if not auto_logged_in:
            from ui.login_window import LoginWindow
            LoginWindow(root, on_success=go_main, db=db, mode_label=mode_label).pack(fill="both", expand=True)
    else:
        from ui.login_window import SetupWindow
        SetupWindow(root, on_done=go_main, db=db, mode_label=mode_label).pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    launch_app()
