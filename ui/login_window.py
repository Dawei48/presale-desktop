"""
登录窗口 - 分栏式：左侧品牌展示区 + 右侧登录/注册表单
"""
import os
import json
import hashlib
import customtkinter as ctk
from ui.styles import Colors, Fonts, Spacing, Radius
from config import BASE_DIR

_LOGIN_FILE = os.path.join(BASE_DIR, "data", ".last_login.json")


def _save_login(username, password):
    """保存登录凭据到本地文件"""
    try:
        os.makedirs(os.path.dirname(_LOGIN_FILE), exist_ok=True)
        data = {"username": username, "password": password}
        with open(_LOGIN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def load_saved_login():
    """读取保存的登录凭据，返回 (username, password) 或 None"""
    try:
        if os.path.exists(_LOGIN_FILE):
            with open(_LOGIN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("username"), data.get("password")
    except Exception:
        pass
    return None


def clear_saved_login():
    """清除保存的登录凭据（退出登录时调用）"""
    try:
        if os.path.exists(_LOGIN_FILE):
            os.remove(_LOGIN_FILE)
    except Exception:
        pass


from config import _find_resource
LOGO_PATH = _find_resource("assets/logo.png")


def _load_logo(size=72):
    """加载 logo 返回 CTkImage 或 None"""
    if not os.path.exists(LOGO_PATH):
        return None
    try:
        from PIL import Image
        from customtkinter import CTkImage
        img = Image.open(LOGO_PATH)
        img.thumbnail((size, size))
        return CTkImage(light_image=img, dark_image=img, size=img.size)
    except Exception:
        return None


# ── 品牌展示区（左栏，登录/注册共用）────────────────
BRAND_SLOGAN = "让预售管理\n简单到只剩专注"
BRAND_SUB = "面向陶瓷电商的 AI 预售管理工具"
BRAND_FEATURES = [
    ("🤖", "AI 智能导入", "各平台订单 CSV 一键识别"),
    ("☁️", "云端多机同步", "团队协作数据实时共享"),
    ("📄", "导出对接工厂", "Word 订单表自动生成"),
]


def _build_brand_panel(parent):
    """构建左侧品牌展示区"""
    panel = ctk.CTkFrame(parent, fg_color=Colors.SIDEBAR_BG, width=360, corner_radius=0)
    panel.pack(side="left", fill="y")
    panel.pack_propagate(False)

    # 顶部 logo + 应用名
    top = ctk.CTkFrame(panel, fg_color="transparent")
    top.pack(fill="x", padx=40, pady=(44, 0))
    logo = _load_logo(56)
    if logo:
        ctk.CTkLabel(top, image=logo, text="").pack(side="left")
    else:
        ctk.CTkLabel(top, text="🏺", font=(Fonts.FAMILY, 36)).pack(side="left")
    name_box = ctk.CTkFrame(top, fg_color="transparent")
    name_box.pack(side="left", padx=(12, 0))
    ctk.CTkLabel(name_box, text="放心预", font=(Fonts.FAMILY, 20, "bold"),
                 text_color=Colors.SIDEBAR_TEXT_HI).pack(anchor="w")
    ctk.CTkLabel(name_box, text="预售管理系统", font=Fonts.TINY,
                 text_color=Colors.SIDEBAR_TEXT).pack(anchor="w")

    # 中部 slogan
    mid = ctk.CTkFrame(panel, fg_color="transparent")
    mid.pack(fill="x", padx=40, pady=(72, 0))
    ctk.CTkLabel(mid, text=BRAND_SLOGAN, font=(Fonts.FAMILY, 26, "bold"),
                 text_color=Colors.SIDEBAR_TEXT_HI, justify="left").pack(anchor="w")
    ctk.CTkLabel(mid, text=BRAND_SUB, font=Fonts.SMALL,
                 text_color=Colors.SIDEBAR_TEXT).pack(anchor="w", pady=(12, 0))

    # 底部产品亮点
    feat = ctk.CTkFrame(panel, fg_color="transparent")
    feat.pack(side="bottom", fill="x", padx=40, pady=(0, 40))
    for icon, title, desc in BRAND_FEATURES:
        row = ctk.CTkFrame(feat, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkLabel(row, text=icon, font=(Fonts.FAMILY, 18)).pack(side="left")
        box = ctk.CTkFrame(row, fg_color="transparent")
        box.pack(side="left", padx=(10, 0))
        ctk.CTkLabel(box, text=title, font=Fonts.SMALL_B,
                     text_color=Colors.SIDEBAR_TEXT_HI).pack(anchor="w")
        ctk.CTkLabel(box, text=desc, font=Fonts.TINY,
                     text_color=Colors.SIDEBAR_TEXT).pack(anchor="w")

    return panel


def _make_entry(parent, placeholder, show=None):
    """创建带 focus 高亮的输入框"""
    entry = ctk.CTkEntry(parent, placeholder_text=placeholder,
                         font=Fonts.BODY, height=44,
                         border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                         corner_radius=Radius.MD, show=show)
    entry.bind("<FocusIn>", lambda e: entry.configure(border_color=Colors.PRIMARY, border_width=2))
    entry.bind("<FocusOut>", lambda e: entry.configure(border_color=Colors.BORDER, border_width=1))
    return entry


class SetupWindow(ctk.CTkFrame):
    """首次使用 - 创建管理员账号"""

    def __init__(self, parent, on_done, db=None, mode_label=""):
        super().__init__(parent, fg_color=Colors.BG_MAIN)
        self.on_done = on_done
        self._db = db
        self._mode_label = mode_label

        _build_brand_panel(self)

        # 右侧表单
        right = ctk.CTkFrame(self, fg_color=Colors.BG_MAIN, corner_radius=0)
        right.pack(side="right", fill="both", expand=True)
        form = ctk.CTkFrame(right, fg_color="transparent", width=360)
        form.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(form, text="创建管理员账号", font=Fonts.TITLE,
                     text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(form, text="首次使用，请设置管理员信息", font=Fonts.SMALL,
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", pady=(4, 28))

        ctk.CTkLabel(form, text="管理员用户名", font=Fonts.SMALL_B,
                     text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.entry_user = _make_entry(form, "用于登录")
        self.entry_user.pack(fill="x", pady=(6, 14))

        ctk.CTkLabel(form, text="显示名称", font=Fonts.SMALL_B,
                     text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.entry_name = _make_entry(form, "你的名字")
        self.entry_name.pack(fill="x", pady=(6, 14))

        ctk.CTkLabel(form, text="密码", font=Fonts.SMALL_B,
                     text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.entry_pass = _make_entry(form, "至少 4 位", show="•")
        self.entry_pass.pack(fill="x", pady=(6, 20))

        self.entry_pass.bind("<Return>", lambda e: self._do_setup())
        self.entry_user.bind("<Return>", lambda e: self.entry_name.focus())
        self.entry_name.bind("<Return>", lambda e: self.entry_pass.focus())

        self.lbl_error = ctk.CTkLabel(form, text="", font=Fonts.SMALL, text_color=Colors.DANGER)
        self.lbl_error.pack(anchor="w")

        ctk.CTkButton(form, text="创建管理员账号", font=Fonts.BODY_B, height=44,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.MD, command=self._do_setup).pack(fill="x", pady=(12, 16))

        ctk.CTkButton(form, text="已有账号？去登录", font=Fonts.SMALL,
                      fg_color="transparent", hover_color=Colors.BG_HOVER,
                      text_color=Colors.PRIMARY, height=28,
                      command=self._go_login).pack()

    def _go_login(self):
        for w in self.master.winfo_children():
            w.destroy()
        LoginWindow(self.master, on_success=self.on_done, db=self._db,
                    mode_label=self._mode_label).pack(fill="both", expand=True)

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

        _build_brand_panel(self)

        # 右侧表单
        right = ctk.CTkFrame(self, fg_color=Colors.BG_MAIN, corner_radius=0)
        right.pack(side="right", fill="both", expand=True)
        form = ctk.CTkFrame(right, fg_color="transparent", width=360)
        form.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(form, text="欢迎回来", font=Fonts.TITLE,
                     text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(form, text="登录放心预，继续管理你的预售订单", font=Fonts.SMALL,
                     text_color=Colors.TEXT_MUTED).pack(anchor="w", pady=(4, 28))

        ctk.CTkLabel(form, text="用户名", font=Fonts.SMALL_B,
                     text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.entry_user = _make_entry(form, "请输入用户名")
        self.entry_user.pack(fill="x", pady=(6, 14))

        ctk.CTkLabel(form, text="密码", font=Fonts.SMALL_B,
                     text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.entry_pass = _make_entry(form, "请输入密码", show="•")
        self.entry_pass.pack(fill="x", pady=(6, 20))

        self.entry_pass.bind("<Return>", lambda e: self._do_login())
        self.entry_user.bind("<Return>", lambda e: self.entry_pass.focus())

        if self._mode_label:
            color = Colors.SUCCESS if "云端" in self._mode_label else Colors.WARNING
            ctk.CTkLabel(form, text=self._mode_label, font=Fonts.TINY,
                         text_color=color).pack(anchor="w", pady=(0, 8))

        self.lbl_error = ctk.CTkLabel(form, text="", font=Fonts.SMALL, text_color=Colors.DANGER)
        self.lbl_error.pack(anchor="w")

        ctk.CTkButton(form, text="登 录", font=Fonts.H2, height=44,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.MD, command=self._do_login).pack(fill="x", pady=(12, 16))

        ctk.CTkButton(form, text="还没有账号？去注册", font=Fonts.SMALL,
                      fg_color="transparent", hover_color=Colors.BG_HOVER,
                      text_color=Colors.PRIMARY, height=28,
                      command=self._go_setup).pack()

    def _go_setup(self):
        for w in self.master.winfo_children():
            w.destroy()
        SetupWindow(self.master, on_done=self.on_success, db=self._db,
                    mode_label=self._mode_label).pack(fill="both", expand=True)

    def _do_login(self):
        try:
            db = self._db
            if not db:
                self.lbl_error.configure(text="数据库未连接")
                return
            user = db.login(self.entry_user.get().strip(), self.entry_pass.get().strip())
            if user:
                db.log("登录系统", f"用户 {user['username']} 登录", user["id"], user["username"])
                _save_login(self.entry_user.get().strip(), self.entry_pass.get().strip())
                self.on_success(user)
            else:
                self.lbl_error.configure(text="用户名或密码错误")
                self.entry_pass.delete(0, "end")
                self.entry_pass.focus()
        except Exception as e:
            self.lbl_error.configure(text=f"连接失败: {e}")
            self.entry_pass.delete(0, "end")
