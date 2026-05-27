"""
仪表盘
"""
import customtkinter as ctk
from ui.styles import Colors, Fonts, Spacing, Radius
from ui.components import StatCard, StatusBadge


class DashboardTab(ctk.CTkFrame):
    def __init__(self, parent, db, current_user):
        super().__init__(parent, fg_color=Colors.BG_MAIN)
        self.db = db
        self.current_user = current_user
        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.XL, pady=(Spacing.XL, Spacing.LG))
        ctk.CTkLabel(header, text="仪表盘", font=Fonts.H1,
                     text_color=Colors.TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(header, text=f"欢迎回来，{self.current_user['display_name']}",
                     font=Fonts.BODY, text_color=Colors.TEXT_MUTED).pack(
            side="left", padx=(Spacing.MD, 0))

        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=Spacing.XL, pady=(0, Spacing.LG))

        self.orders_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD,
                                         corner_radius=Radius.LG, border_width=1,
                                         border_color=Colors.BORDER)
        self.orders_frame.pack(fill="both", expand=True, padx=Spacing.XL, pady=(0, Spacing.XL))
        self._load()

    def _load(self):
        # 统计卡片
        for w in self.stats_frame.winfo_children():
            w.destroy()
        stats = self.db.get_stats()
        cards = [
            ("🏷️", "品牌", str(stats["brands"]), Colors.PRIMARY),
            ("📦", "产品", str(stats["products"]), Colors.INFO),
            ("📋", "订单", str(stats["orders"]), Colors.SUCCESS),
            ("⏳", "未发货", str(stats["pending"]), Colors.WARNING),
        ]
        self.stats_frame.columnconfigure((0, 1, 2, 3), weight=1)
        for i, (icon, title, value, color) in enumerate(cards):
            ctk.CTkLabel(self.stats_frame, text="").grid(row=0, column=i)
            StatCard(self.stats_frame, title=title, value=value,
                     icon=icon, color=color).grid(row=0, column=i, sticky="nsew",
                                                  padx=(0 if i == 0 else Spacing.MD, 0))

        # 最近订单
        for w in self.orders_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.orders_frame, text="最近订单", font=Fonts.H2,
                     text_color=Colors.TEXT_PRIMARY).pack(
            anchor="w", padx=Spacing.LG, pady=(Spacing.LG, Spacing.MD))

        orders = self.db.get_orders()[:8]
        if not orders:
            ctk.CTkLabel(self.orders_frame, text="📭 暂无订单",
                         font=Fonts.BODY, text_color=Colors.TEXT_MUTED).pack(pady=Spacing.XL)
            return

        # 表头用 grid
        hdr = ctk.CTkFrame(self.orders_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=Spacing.LG)
        headers = ["订单号", "客户", "品牌/产品", "数量", "状态", "日期"]
        widths = [110, 80, 160, 50, 60, 90]
        for i, h in enumerate(headers):
            ctk.CTkLabel(hdr, text=h, font=Fonts.SMALL_B, text_color=Colors.TEXT_MUTED,
                         anchor="w", width=widths[i]).grid(
                row=0, column=i, sticky="w", padx=Spacing.SM, pady=(0, Spacing.SM))

        for idx, order in enumerate(orders):
            bg = Colors.BG_INPUT if idx % 2 == 0 else "transparent"
            row = ctk.CTkFrame(self.orders_frame, fg_color=bg, corner_radius=Radius.SM, height=36)
            row.pack(fill="x", padx=Spacing.LG, pady=1)
            row.pack_propagate(False)
            vals = [
                order.get("order_no", ""),
                order.get("customer", ""),
                f"{order.get('brand_name', '')} / {order.get('product_name', '')}",
                str(order.get("quantity", 0)),
                order.get("status", "pending"),
                order.get("created_at", "")[:10],
            ]
            for i, v in enumerate(vals):
                if i == 4:
                    f = ctk.CTkFrame(row, fg_color="transparent")
                    f.grid(row=0, column=i, sticky="w", padx=Spacing.SM)
                    StatusBadge(f, v)
                else:
                    ctk.CTkLabel(row, text=v, font=Fonts.BODY,
                                 text_color=Colors.TEXT_PRIMARY, anchor="w",
                                 width=widths[i]).grid(row=0, column=i, sticky="w", padx=Spacing.SM)

    def refresh(self):
        self._load()
