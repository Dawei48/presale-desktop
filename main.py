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
    from ui.main_window import MainWindow
    import customtkinter as ctk

    db = Database()
    root = ctk.CTk()
    root.withdraw()  # 隐藏主窗口，只用来承载子窗口

    def go_main(user_info):
        for w in root.winfo_children():
            w.destroy()
        root.deiconify()
        MainWindow(root, user_info)

    if db.has_users():
        # 已有用户 → 登录
        from ui.login_window import LoginWindow
        LoginWindow(root, on_success=go_main)
    else:
        # 首次使用 → 注册管理员
        from ui.login_window import SetupWindow
        SetupWindow(root, on_done=go_main)

    root.mainloop()


if __name__ == "__main__":
    launch_app()
