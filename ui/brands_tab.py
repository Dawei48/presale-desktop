"""
品牌管理 - 三级结构的第一级
"""
import customtkinter as ctk
from ui.styles import Colors, Fonts, Spacing, Radius
from ui.components import Dialog, ConfirmDialog, Toast, EmptyState


class BrandDialog(Dialog):
    def __init__(self, parent, brand=None, on_save=None):
        self.brand = brand
        self.on_save = on_save
        super().__init__(parent, "编辑品牌" if brand else "新增品牌", width=380, height=200)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)
        form.columnconfigure(1, weight=1)
        self.entry_name = self._make_field(form, "品牌名称 *", 0)
        self._make_buttons(form, 1)

        if brand:
            self.entry_name.insert(0, brand["name"])

    def _on_ok(self):
        name = self.entry_name.get().strip()
        if not name:
            Toast(self, "品牌名称不能为空", "error")
            return
        self.result = {"name": name}
        if self.on_save:
            self.on_save(self.result)
        self.destroy()


class BrandsTab(ctk.CTkFrame):
    def __init__(self, parent, db, current_user, on_brand_select=None):
        super().__init__(parent, fg_color=Colors.BG_MAIN)
        self.db = db
        self.current_user = current_user
        self.on_brand_select = on_brand_select  # 点击品牌跳转产品
        self._build()
        self._load()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.XL, pady=(Spacing.XL, Spacing.LG))
        ctk.CTkLabel(header, text="品牌管理", font=Fonts.H1,
                     text_color=Colors.TEXT_PRIMARY).pack(side="left")
        ctk.CTkButton(header, text="＋ 新增品牌", font=Fonts.BODY_B, height=36,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.SM, command=self._add).pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent",
            scrollbar_button_color=Colors.BORDER, scrollbar_button_hover_color=Colors.TEXT_MUTED)
        self.list_frame.pack(fill="both", expand=True, padx=Spacing.XL, pady=(0, Spacing.XL))

    def _load(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        brands = self.db.get_brands()
        if not brands:
            EmptyState(self.list_frame, "🏷️", "暂无品牌，点击右上角新增").pack(fill="x")
            return
        for b in brands:
            card = ctk.CTkFrame(self.list_frame, fg_color=Colors.BG_CARD,
                                corner_radius=Radius.LG, border_width=1,
                                border_color=Colors.BORDER, cursor="hand2")
            card.pack(fill="x", pady=(0, Spacing.SM))
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=Spacing.LG, pady=Spacing.LG)
            left = ctk.CTkFrame(inner, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(left, text=b["name"], font=Fonts.H2,
                         text_color=Colors.TEXT_PRIMARY).pack(side="left")
            ctk.CTkLabel(left, text=f"  {b['product_count']} 个产品",
                         font=Fonts.SMALL, text_color=Colors.TEXT_MUTED).pack(
                side="left", padx=(Spacing.SM, 0))
            ctk.CTkLabel(left, text=f"  {b.get('created_at', '')[:10]}",
                         font=Fonts.TINY, text_color=Colors.TEXT_MUTED).pack(
                side="left", padx=(Spacing.SM, 0))
            btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
            btn_frame.pack(side="right")
            ctk.CTkButton(btn_frame, text="查看产品", font=Fonts.SMALL, width=70, height=28,
                          fg_color=Colors.PRIMARY_LIGHT, hover_color=Colors.PRIMARY_DIM,
                          text_color=Colors.PRIMARY, corner_radius=Radius.SM,
                          command=lambda b=b: self._go_products(b)).pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text="编辑", font=Fonts.SMALL, width=48, height=28,
                          fg_color="transparent", hover_color=Colors.PRIMARY_LIGHT,
                          text_color=Colors.PRIMARY, corner_radius=Radius.SM,
                          command=lambda b=b: self._edit(b)).pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text="删除", font=Fonts.SMALL, width=48, height=28,
                          fg_color="transparent", hover_color=Colors.DANGER_LIGHT,
                          text_color=Colors.DANGER, corner_radius=Radius.SM,
                          command=lambda b=b: self._delete(b)).pack(side="left", padx=2)

    def _go_products(self, brand):
        if self.on_brand_select:
            self.on_brand_select(brand)

    def _add(self):
        def on_save(data):
            self.db.add_brand(data["name"])
            self.db.log("新增品牌", f"品牌: {data['name']}", self.current_user["id"], self.current_user["username"])
            Toast(self, "✅ 品牌已添加")
            self._load()
        BrandDialog(self, on_save=on_save)

    def _edit(self, brand):
        def on_save(data):
            self.db.update_brand(brand["id"], data["name"])
            self.db.log("编辑品牌", f"品牌: {data['name']}", self.current_user["id"], self.current_user["username"])
            Toast(self, "✅ 品牌已更新")
            self._load()
        BrandDialog(self, brand=brand, on_save=on_save)

    def _delete(self, brand):
        d = ConfirmDialog(self, f"确定要删除品牌「{brand['name']}」吗？\n该品牌下所有产品和订单都会被删除。")
        self.wait_window(d)
        if d.result:
            self.db.delete_brand(brand["id"])
            self.db.log("删除品牌", f"品牌: {brand['name']}", self.current_user["id"], self.current_user["username"])
            Toast(self, "🗑️ 品牌已删除")
            self._load()

    def refresh(self):
        self._load()
