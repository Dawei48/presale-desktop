"""
全局搜索
"""
import customtkinter as ctk
from ui.styles import Colors, Fonts, Spacing, Radius
from ui.components import StatusBadge, EmptyState


class SearchTab(ctk.CTkFrame):
    def __init__(self, parent, db, current_user):
        super().__init__(parent, fg_color=Colors.BG_MAIN)
        self.db = db
        self.current_user = current_user
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._do_search())

        ctk.CTkLabel(self, text="全局搜索", font=Fonts.H1,
                     text_color=Colors.TEXT_PRIMARY).pack(
            anchor="w", padx=Spacing.XL, pady=(Spacing.XL, Spacing.MD))

        sf = ctk.CTkFrame(self, fg_color="transparent")
        sf.pack(fill="x", padx=Spacing.XL, pady=(0, Spacing.LG))
        self.search_entry = ctk.CTkEntry(
            sf, textvariable=self.search_var,
            placeholder_text="🔍  输入关键词搜索产品和订单...",
            font=(Fonts.FAMILY, 15), height=44,
            border_color=Colors.BORDER, fg_color=Colors.BG_INPUT, corner_radius=Radius.MD)
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.focus()
        self.result_label = ctk.CTkLabel(sf, text="", font=Fonts.SMALL,
                                         text_color=Colors.TEXT_MUTED)
        self.result_label.pack(side="right", padx=Spacing.LG)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
            scrollbar_button_color=Colors.BORDER, scrollbar_button_hover_color=Colors.TEXT_MUTED)
        self.scroll.pack(fill="both", expand=True, padx=Spacing.XL, pady=(0, Spacing.XL))
        EmptyState(self.scroll, "🔍", "输入关键词开始搜索").pack(fill="x")

    def _do_search(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        kw = self.search_var.get().strip()
        if not kw:
            EmptyState(self.scroll, "🔍", "输入关键词开始搜索").pack(fill="x")
            self.result_label.configure(text="")
            return

        products = self.db.search_products(kw)
        orders = self.db.get_orders(keyword=kw)
        total = len(products) + len(orders)
        self.result_label.configure(text=f"找到 {total} 条结果")
        if total == 0:
            EmptyState(self.scroll, "🤷", f"没有找到「{kw}」相关结果").pack(fill="x")
            return

        if products:
            sec = ctk.CTkFrame(self.scroll, fg_color="transparent")
            sec.pack(fill="x", pady=(0, Spacing.MD))
            ctk.CTkLabel(sec, text=f"📦 产品 ({len(products)})", font=Fonts.H2,
                         text_color=Colors.PRIMARY).pack(anchor="w", pady=(0, Spacing.SM))
            for p in products:
                card = ctk.CTkFrame(sec, fg_color=Colors.BG_CARD, corner_radius=Radius.MD,
                                    border_width=1, border_color=Colors.BORDER)
                card.pack(fill="x", pady=(0, 4))
                inner = ctk.CTkFrame(card, fg_color="transparent")
                inner.pack(fill="x", padx=Spacing.LG, pady=Spacing.MD)
                ctk.CTkLabel(inner, text=p["name"], font=Fonts.BODY_B,
                             text_color=Colors.TEXT_PRIMARY).pack(side="left")
                if p.get("brand_name"):
                    ctk.CTkLabel(inner, text=p["brand_name"], font=Fonts.SMALL,
                                 text_color=Colors.PRIMARY, fg_color=Colors.PRIMARY_LIGHT,
                                 corner_radius=Radius.SM, padx=6, pady=2).pack(
                        side="left", padx=(Spacing.SM, 0))
                ctk.CTkLabel(inner, text=f"¥{p['price']:,.0f}",
                             font=Fonts.BODY_B, text_color=Colors.PRIMARY).pack(side="right")

        if orders:
            sec = ctk.CTkFrame(self.scroll, fg_color="transparent")
            sec.pack(fill="x", pady=(0, Spacing.MD))
            ctk.CTkLabel(sec, text=f"📋 订单 ({len(orders)})", font=Fonts.H2,
                         text_color=Colors.INFO).pack(anchor="w", pady=(0, Spacing.SM))
            for o in orders:
                card = ctk.CTkFrame(sec, fg_color=Colors.BG_CARD, corner_radius=Radius.MD,
                                    border_width=1, border_color=Colors.BORDER)
                card.pack(fill="x", pady=(0, 4))
                inner = ctk.CTkFrame(card, fg_color="transparent")
                inner.pack(fill="x", padx=Spacing.LG, pady=Spacing.MD)
                left = ctk.CTkFrame(inner, fg_color="transparent")
                left.pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(left, text=o.get("order_no", ""), font=Fonts.SMALL_B,
                             text_color=Colors.PRIMARY).pack(side="left")
                ctk.CTkLabel(left, text=f"  {o.get('customer', '')}  {o.get('brand_name', '')}/{o.get('product_name', '')}",
                             font=Fonts.BODY, text_color=Colors.TEXT_PRIMARY).pack(side="left")
                right = ctk.CTkFrame(inner, fg_color="transparent")
                right.pack(side="right")
                StatusBadge(right, o.get("status", "pending")).pack(side="right")

    def refresh(self):
        self._do_search()
