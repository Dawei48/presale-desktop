"""
登录窗口 - 首次打开注册管理员，之后登录
"""
import os
import customtkinter as ctk
from ui.styles import Colors, Fonts, Spacing, Radius
from config import BASE_DIR

from config import _find_resource
LOGO_PATH = _find_resource("assets/logo.png")


def _load_logo():
    """加载 logo 返回 CTkImage 或 None"""
    if not os.path.exists(LOGO_PATH):
        return None
    try:
        from PIL import Image
        from customtkinter import CTkImage
        img = Image.open(LOGO_PATH)
        img.thumbnail((90, 90))
        return CTkImage(light_image=img, dark_image=img, size=img.size)
    except Exception:
        return None


class SetupWindow(ctk.CTkFrame):
    """首次使用 - 创建管理员账号"""

    def __init__(self, parent, on_done, db=None, mode_label=""):
        super().__init__(parent, fg_color=Colors.BG_MAIN)
        self.on_done = on_done
        self._db = db

        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Radius.XL,
                            border_width=1, border_color=Colors.BORDER,
                            width=380, height=540)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        logo = _load_logo()
        if logo:
            ctk.CTkLabel(card, image=logo, text="").pack(pady=(20, 4))
        else:
            ctk.CTkLabel(card, text="📦", font=(Fonts.FAMILY, 36)).pack(pady=(24, 4))
        ctk.CTkLabel(card, text="欢迎使用 放心预", font=Fonts.H1,
                     text_color=Colors.TEXT_PRIMARY).pack()
        ctk.CTkLabel(card, text="首次使用，请创建管理员账号", font=Fonts.SMALL,
                     text_color=Colors.TEXT_MUTED).pack(pady=(0, 20))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=32)

        ctk.CTkLabel(form, text="管理员用户名 *", font=Fonts.SMALL_B,
                     text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.entry_user = ctk.CTkEntry(form, placeholder_text="用于登录",
                                       font=Fonts.BODY, height=36,
                                       border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                                       corner_radius=Radius.SM)
        self.entry_user.pack(fill="x", pady=(4, 10))

        ctk.CTkLabel(form, text="显示名称 *", font=Fonts.SMALL_B,
                     text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.entry_name = ctk.CTkEntry(form, placeholder_text="你的名字",
                                       font=Fonts.BODY, height=36,
                                       border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                                       corner_radius=Radius.SM)
        self.entry_name.pack(fill="x", pady=(4, 10))

        ctk.CTkLabel(form, text="密码 *", font=Fonts.SMALL_B,
                     text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.entry_pass = ctk.CTkEntry(form, placeholder_text="请设置密码（至少4位）",
                                       font=Fonts.BODY, height=36,
                                       border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                                       corner_radius=Radius.SM, show="•")
        self.entry_pass.pack(fill="x", pady=(4, 16))

        # 回车键提交
        self.entry_pass.bind("<Return>", lambda e: self._do_setup())
        self.entry_user.bind("<Return>", lambda e: self.entry_name.focus())
        self.entry_name.bind("<Return>", lambda e: self.entry_pass.focus())

        self.lbl_error = ctk.CTkLabel(card, text="", font=Fonts.SMALL,
                                      text_color=Colors.DANGER)
        self.lbl_error.pack()

        ctk.CTkButton(form, text="创建管理员账号", font=Fonts.BODY_B, height=40,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.SM,
                      command=self._do_setup).pack(fill="x", pady=(0, 0))

        ctk.CTkLabel(card, text="", font=Fonts.SMALL, text_color=Colors.TEXT_MUTED).pack()
        ctk.CTkButton(card, text="已有账号？去登录", font=Fonts.SMALL,
                      fg_color=None, hover_color=None,
                      text_color=Colors.PRIMARY, height=28,
                      command=self._go_login).pack(pady=(4, 0))

    def _go_login(self):
        for w in self.master.winfo_children():
            w.destroy()
        LoginWindow(self.master, on_success=self.on_done, db=self._db, mode_label=self._mode_label).pack(fill="both", expand=True)

    def _do_setup(self):
        username = self.entry_user.get().strip()
        display_name = self.entry_name.get().strip()
        password = self.entry_pass.get().strip()

        if not username or not display_name:
            self.lbl_error.configure(text="请填写用户名和显示名称")
            return
        if len(password) < 4:
            self.lbl_error.configure(text="密码至少4位")
            return

        try:
            db = self._db
            if not db:
                self.lbl_error.configure(text="数据库未连接")
                return
            if db.user_exists(username):
                self.lbl_error.configure(text="用户名已存在")
                return
            db.add_user(username, password, display_name, "admin")
            db.log("系统初始化", f"创建管理员: {username}")
            user = db.login(username, password)
            self.on_done(user)
        except Exception as e:
            self.lbl_error.configure(text=f"创建失败: {e}")


class LoginWindow(ctk.CTkFrame):
    """正常登录"""

    def __init__(self, parent, on_success, db=None, mode_label=""):
        super().__init__(parent, fg_color=Colors.BG_MAIN)
        self.on_success = on_success
        self._db = db
        self._mode_label = mode_label

        card = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Radius.XL,
                            border_width=1, border_color=Colors.BORDER,
                            width=380, height=480)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        logo = _load_logo()
        if logo:
            ctk.CTkLabel(card, image=logo, text="").pack(pady=(20, 4))
        else:
            ctk.CTkLabel(card, text="📦", font=(Fonts.FAMILY, 36)).pack(pady=(28, 4))
        ctk.CTkLabel(card, text="放心预", font=Fonts.TITLE,
                     text_color=Colors.TEXT_PRIMARY).pack()
        ctk.CTkLabel(card, text="预售管理系统", font=Fonts.SMALL,
                     text_color=Colors.TEXT_MUTED).pack(pady=(0, 4))
        if self._mode_label:
            color = Colors.SUCCESS if "云端" in self._mode_label else Colors.WARNING
            ctk.CTkLabel(card, text=self._mode_label, font=Fonts.TINY,
                         text_color=color).pack(pady=(0, 16))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=32)

        ctk.CTkLabel(form, text="用户名", font=Fonts.SMALL_B,
                     text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.entry_user = ctk.CTkEntry(form, placeholder_text="请输入用户名",
                                       font=Fonts.BODY, height=38,
                                       border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                                       corner_radius=Radius.SM)
        self.entry_user.pack(fill="x", pady=(4, 12))

        ctk.CTkLabel(form, text="密码", font=Fonts.SMALL_B,
                     text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.entry_pass = ctk.CTkEntry(form, placeholder_text="请输入密码",
                                       font=Fonts.BODY, height=38,
                                       border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                                       corner_radius=Radius.SM, show="•")
        self.entry_pass.pack(fill="x", pady=(4, 16))

        # 回车键登录
        self.entry_pass.bind("<Return>", lambda e: self._do_login())
        self.entry_user.bind("<Return>", lambda e: self.entry_pass.focus())

        ctk.CTkButton(form, text="登 录", font=Fonts.H2, height=42,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.SM,
                      command=self._do_login).pack(fill="x")

        self.lbl_error = ctk.CTkLabel(card, text="", font=Fonts.SMALL,
                                      text_color=Colors.DANGER)
        self.lbl_error.pack(pady=(8, 0))

        ctk.CTkButton(card, text="还没有账号？去注册", font=Fonts.SMALL,
                      fg_color=None, hover_color=None,
                      text_color=Colors.PRIMARY, height=28,
                      command=self._go_setup).pack(pady=(4, 0))

    def _go_setup(self):
        for w in self.master.winfo_children():
            w.destroy()
        SetupWindow(self.master, on_done=self.on_success, db=self._db, mode_label=self._mode_label).pack(fill="both", expand=True)

    def _do_login(self):
        try:
            db = self._db
            if not db:
                self.lbl_error.configure(text="数据库未连接")
                return
            user = db.login(self.entry_user.get().strip(), self.entry_pass.get().strip())
            if user:
                db.log("登录系统", f"用户 {user['username']} 登录", user["id"], user["username"])
                self.on_success(user)
            else:
                self.lbl_error.configure(text="用户名或密码错误")
                self.entry_pass.delete(0, "end")
                self.entry_pass.focus()
        except Exception as e:
            self.lbl_error.configure(text=f"连接失败: {e}")
            self.entry_pass.delete(0, "end")
