"""
主窗口 - 侧边栏导航 + 内容区
三级结构: 品牌 → 产品 → 订单
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ui.styles import Colors, Fonts, Spacing, Radius
from ui.dashboard import DashboardTab
from ui.brands_tab import BrandsTab
from ui.orders_tab import OrdersTab
from ui.search_tab import SearchTab
from ui.team_tab import TeamTab
from utils.docx_export import export_brand_orders_docx


class MainWindow(ctk.CTkFrame):
    def __init__(self, parent, user_info):
        super().__init__(parent, fg_color=Colors.BG_MAIN)
        self.master = parent
        self.user_info = user_info
        self.is_admin = user_info.get("role") == "admin"

        from database import Database
        self.db = Database()

        parent.title("放心预 - 预售管理系统")
        parent.geometry("1100x700")
        parent.minsize(900, 600)

        self._build_ui()
        self._switch_tab("dashboard")

    def _build_ui(self):
        self.pack(fill="both", expand=True)

        self.sidebar = ctk.CTkFrame(self, fg_color=Colors.SIDEBAR_BG, width=220, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        self.content = ctk.CTkFrame(self, fg_color=Colors.BG_MAIN, corner_radius=0)
        self.content.pack(side="right", fill="both", expand=True)

    def _build_sidebar(self):
        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.pack(fill="x", padx=Spacing.LG, pady=(Spacing.XL, Spacing.XL))
        ctk.CTkLabel(logo, text="📦", font=(Fonts.FAMILY, 28)).pack(anchor="w")
        ctk.CTkLabel(logo, text="放心预", font=Fonts.H1,
                     text_color=Colors.SIDEBAR_TEXT_HI).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(logo, text="预售管理系统", font=Fonts.TINY,
                     text_color=Colors.SIDEBAR_TEXT).pack(anchor="w")

        ctk.CTkFrame(self.sidebar, fg_color=Colors.SIDEBAR_HOVER, height=1).pack(
            fill="x", padx=Spacing.LG, pady=(0, Spacing.LG))

        self.nav_buttons = {}
        items = [
            ("dashboard", "🏠  仪表盘"),
            ("brands",    "🏷️  品牌管理"),
            ("orders",    "📋  全部订单"),
            ("search",    "🔍  全局搜索"),
        ]
        if self.is_admin:
            items.append(("team", "👥  团队管理"))

        for key, label in items:
            btn = ctk.CTkButton(self.sidebar, text=label, font=Fonts.BODY,
                                fg_color="transparent", hover_color=Colors.SIDEBAR_HOVER,
                                text_color=Colors.SIDEBAR_TEXT, anchor="w", height=40,
                                corner_radius=Radius.SM,
                                command=lambda k=key: self._switch_tab(k))
            btn.pack(fill="x", padx=Spacing.MD, pady=2)
            self.nav_buttons[key] = btn

        # 底部用户
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=Spacing.LG, pady=Spacing.LG)
        ctk.CTkFrame(bottom, fg_color=Colors.SIDEBAR_HOVER, height=1).pack(fill="x", pady=(0, Spacing.MD))
        uf = ctk.CTkFrame(bottom, fg_color="transparent")
        uf.pack(fill="x")
        role_text = "👑 管理员" if self.is_admin else "成员"
        ctk.CTkLabel(uf, text=self.user_info["display_name"], font=Fonts.BODY_B,
                     text_color=Colors.SIDEBAR_TEXT_HI).pack(anchor="w")
        ctk.CTkLabel(uf, text=role_text, font=Fonts.TINY,
                     text_color=Colors.SIDEBAR_TEXT).pack(anchor="w")
        ctk.CTkButton(uf, text="退出登录", font=Fonts.TINY, fg_color="transparent",
                      text_color=Colors.SIDEBAR_TEXT, hover_color=Colors.DANGER,
                      anchor="w", height=28, command=self._logout).pack(anchor="w", pady=(Spacing.SM, 0))

    def _switch_tab(self, tab_key):
        for key, btn in self.nav_buttons.items():
            if key == tab_key:
                btn.configure(fg_color=Colors.SIDEBAR_ACTIVE, text_color=Colors.SIDEBAR_TEXT_HI)
            else:
                btn.configure(fg_color="transparent", text_color=Colors.SIDEBAR_TEXT)

        for w in self.content.winfo_children():
            w.destroy()

        if tab_key == "dashboard":
            DashboardTab(self.content, self.db, self.user_info).pack(fill="both", expand=True)
        elif tab_key == "brands":
            BrandsTab(self.content, self.db, self.user_info,
                       on_brand_select=self._go_brand_products).pack(fill="both", expand=True)
        elif tab_key == "orders":
            self._show_all_orders()
        elif tab_key == "search":
            SearchTab(self.content, self.db, self.user_info).pack(fill="both", expand=True)
        elif tab_key == "team":
            TeamTab(self.content, self.db, self.user_info).pack(fill="both", expand=True)

    def _go_brand_products(self, brand):
        """从品牌列表进入产品列表"""
        from ui.products_tab import ProductsTab
        for w in self.content.winfo_children():
            w.destroy()
        ProductsTab(self.content, self.db, self.user_info, brand=brand,
                     on_back=lambda: self._switch_tab("brands")).pack(fill="both", expand=True)

    def _show_all_orders(self):
        """全部订单 + 导出按钮"""
        toolbar = ctk.CTkFrame(self.content, fg_color="transparent")
        toolbar.pack(fill="x", padx=Spacing.XL, pady=(Spacing.XL, 0))
        ctk.CTkButton(toolbar, text="📄 导出品牌订单", font=Fonts.BODY_B, height=36,
                      fg_color=Colors.SUCCESS, hover_color="#059669", corner_radius=Radius.SM,
                      command=self._export_by_brand).pack(side="right")
        OrdersTab(self.content, self.db, self.user_info).pack(fill="both", expand=True)

    def _export_by_brand(self):
        """按品牌导出"""
        brands = self.db.get_brands()
        if not brands:
            messagebox.showinfo("提示", "暂无品牌")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("导出品牌订单")
        dialog.geometry("380x200")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=Colors.BG_CARD)

        dialog.update_idletasks()
        px = self.winfo_rootx() + (self.winfo_width() - 380) // 2
        py = self.winfo_rooty() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"+{max(px,0)}+{max(py,0)}")

        inner = ctk.CTkFrame(dialog, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)

        ctk.CTkLabel(inner, text="📄 选择要导出的品牌", font=Fonts.H2,
                     text_color=Colors.TEXT_PRIMARY).pack(anchor="w", pady=(0, Spacing.LG))

        brand_names = [b["name"] for b in brands]
        brand_map = {b["name"]: b for b in brands}
        combo = ctk.CTkComboBox(inner, values=brand_names, font=Fonts.BODY, height=36,
                                border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                                button_color=Colors.PRIMARY, corner_radius=Radius.SM)
        combo.set(brand_names[0])
        combo.pack(anchor="w", pady=(0, Spacing.LG))

        def do_export():
            name = combo.get()
            b = brand_map.get(name)
            if not b:
                return
            orders = self.db.get_orders(brand_id=b["id"], status="pending")
            if not orders:
                messagebox.showinfo("提示", f"品牌「{name}」暂无未发货订单", parent=dialog)
                return
            filepath = filedialog.asksaveasfilename(
                parent=dialog, defaultextension=".docx",
                filetypes=[("Word 文档", "*.docx")],
                initialfile=f"{name}_预售订单_{__import__('datetime').datetime.now().strftime('%Y%m%d')}.docx")
            if filepath:
                export_brand_orders_docx(name, orders, filepath)
                dialog.destroy()
                # 统计产品数
                from collections import Counter
                product_count = len(set(o.get("product_name", "") for o in orders))
                if messagebox.askyesno("导出成功", f"已导出 {product_count} 个产品（未发货）到:\n{filepath}\n\n是否打开？"):
                    import os
                    os.startfile(filepath)

        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(fill="x")
        ctk.CTkButton(btn_frame, text="取消", font=Fonts.BODY, width=80, height=34,
                      fg_color=Colors.BG_INPUT, hover_color=Colors.BORDER,
                      text_color=Colors.TEXT_SECONDARY, corner_radius=Radius.SM,
                      command=dialog.destroy).pack(side="right", padx=(Spacing.SM, 0))
        ctk.CTkButton(btn_frame, text="导出", font=Fonts.BODY_B, width=100, height=34,
                      fg_color=Colors.SUCCESS, hover_color="#059669", corner_radius=Radius.SM,
                      command=do_export).pack(side="right")

    def _logout(self):
        from ui.components import ConfirmDialog
        d = ConfirmDialog(self, "确定要退出登录吗？")
        self.wait_window(d)
        if d.result:
            self.db.log("退出登录", f"用户 {self.user_info['username']} 退出",
                        self.user_info["id"], self.user_info["username"])
            for w in self.master.winfo_children():
                w.destroy()
            self.master.geometry("440x640")
            self.master.minsize(100, 100)
            self.master.resizable(False, False)
            from ui.login_window import LoginWindow
            LoginWindow(self.master, on_success=self._go_main).pack(fill="both", expand=True)

    def _go_main(self, user_info):
        for w in self.master.winfo_children():
            w.destroy()
        self.master.geometry("1100x700")
        self.master.minsize(900, 600)
        self.master.resizable(True, True)
        MainWindow(self.master, user_info)
