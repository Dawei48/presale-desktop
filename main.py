"""
放心预 - 预售管理系统 v1.0.0
桌面版 · 本地 SQLite · 品牌→产品→订单 · 团队协作 · Word 导出
"""
import sys
import os

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))


def launch_app():
    from database import Database
    import customtkinter as ctk

    db = Database()
    root = ctk.CTk()
    root.title("放心预")
    root.geometry("440x640")
    root.resizable(False, False)

    def go_main(user_info):
        for w in root.winfo_children():
            w.destroy()
        root.geometry("1100x700")
        root.minsize(900, 600)
        root.resizable(True, True)
        from ui.main_window import MainWindow
        MainWindow(root, user_info)

    if db.has_users():
        from ui.login_window import LoginWindow
        LoginWindow(root, on_success=go_main).pack(fill="both", expand=True)
    else:
        from ui.login_window import SetupWindow
        SetupWindow(root, on_done=go_main).pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    launch_app()
