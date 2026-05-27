"""
可复用 UI 组件
"""
import customtkinter as ctk
from ui.styles import Colors, Fonts, Spacing, Radius

# ── 订单状态 ──────────────────────────────────
STATUS_MAP = {
    "pending":   ("未发货", Colors.WARNING, Colors.WARNING_LIGHT),
    "shipped":   ("已发货", Colors.PRIMARY, Colors.PRIMARY_DIM),
    "completed": ("已完成", Colors.SUCCESS, Colors.SUCCESS_LIGHT),
    "cancelled": ("已取消", Colors.DANGER,  Colors.DANGER_LIGHT),
}


class Dialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, width=420, height=300):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"+{max(px,0)}+{max(py,0)}")
        self.configure(fg_color=Colors.BG_CARD)
        self.result = None

    def _make_field(self, parent, label, row, **kw):
        ctk.CTkLabel(parent, text=label, font=Fonts.BODY,
                     text_color=Colors.TEXT_SECONDARY).grid(
            row=row, column=0, sticky="w", pady=(Spacing.SM, 2), padx=Spacing.XS)
        entry = ctk.CTkEntry(parent, font=Fonts.BODY, height=36,
                             border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                             corner_radius=Radius.SM, **kw)
        entry.grid(row=row, column=1, sticky="ew", pady=(Spacing.SM, 2), padx=Spacing.XS)
        return entry

    def _make_combo(self, parent, label, row, values, **kw):
        ctk.CTkLabel(parent, text=label, font=Fonts.BODY,
                     text_color=Colors.TEXT_SECONDARY).grid(
            row=row, column=0, sticky="w", pady=(Spacing.SM, 2), padx=Spacing.XS)
        combo = ctk.CTkComboBox(parent, values=values, font=Fonts.BODY, height=36,
                                border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
                                button_color=Colors.PRIMARY, button_hover_color=Colors.PRIMARY_HOVER,
                                dropdown_fg_color=Colors.BG_CARD, corner_radius=Radius.SM, **kw)
        combo.grid(row=row, column=1, sticky="ew", pady=(Spacing.SM, 2), padx=Spacing.XS)
        return combo

    def _make_buttons(self, parent, row, ok_text="确定", cancel_text="取消"):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, columnspan=2, pady=(Spacing.LG, 0), sticky="e")
        ctk.CTkButton(frame, text=cancel_text, font=Fonts.BODY, width=80, height=34,
                      fg_color=Colors.BG_INPUT, hover_color=Colors.BORDER,
                      text_color=Colors.TEXT_SECONDARY, corner_radius=Radius.SM,
                      command=self.destroy).pack(side="right", padx=(Spacing.SM, 0))
        ctk.CTkButton(frame, text=ok_text, font=Fonts.BODY_B, width=80, height=34,
                      fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                      corner_radius=Radius.SM, command=self._on_ok).pack(side="right")

    def _on_ok(self):
        self.destroy()


class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, message, title="确认操作"):
        super().__init__(parent)
        self.title(title)
        self.geometry("360x180")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=Colors.BG_CARD)
        self.result = False
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - 360) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - 180) // 2
        self.geometry(f"+{max(px,0)}+{max(py,0)}")

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)
        ctk.CTkLabel(frame, text="⚠️", font=(Fonts.FAMILY, 28)).pack(pady=(0, Spacing.SM))
        ctk.CTkLabel(frame, text=message, font=Fonts.BODY, wraplength=280,
                     text_color=Colors.TEXT_PRIMARY).pack(pady=(0, Spacing.LG))
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        ctk.CTkButton(btn_frame, text="取消", font=Fonts.BODY, width=80, height=34,
                      fg_color=Colors.BG_INPUT, hover_color=Colors.BORDER,
                      text_color=Colors.TEXT_SECONDARY, corner_radius=Radius.SM,
                      command=self.destroy).pack(side="right", padx=(Spacing.SM, 0))
        ctk.CTkButton(btn_frame, text="确定", font=Fonts.BODY_B, width=80, height=34,
                      fg_color=Colors.DANGER, hover_color="#DC2626", corner_radius=Radius.SM,
                      command=self._confirm).pack(side="right")

    def _confirm(self):
        self.result = True
        self.destroy()


class StatCard(ctk.CTkFrame):
    def __init__(self, parent, title, value, icon="", color=Colors.PRIMARY, **kw):
        super().__init__(parent, fg_color=Colors.BG_CARD, corner_radius=Radius.LG,
                         border_width=1, border_color=Colors.BORDER, **kw)
        self.configure(height=110)
        self.pack_propagate(False)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=Spacing.LG, pady=(Spacing.LG, Spacing.XS))
        icon_frame = ctk.CTkFrame(top, fg_color=color, width=36, height=36,
                                  corner_radius=Radius.FULL)
        icon_frame.pack(side="left")
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(icon_frame, text=icon, font=(Fonts.FAMILY, 16),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(top, text=title, font=Fonts.SMALL,
                     text_color=Colors.TEXT_MUTED).pack(side="right")
        ctk.CTkLabel(self, text=value, font=(Fonts.FAMILY, 26, "bold"),
                     text_color=Colors.TEXT_PRIMARY).pack(padx=Spacing.LG, anchor="w")


class StatusBadge(ctk.CTkLabel):
    def __init__(self, parent, status, **kw):
        label, fg, bg = STATUS_MAP.get(status, ("未知", Colors.TEXT_MUTED, Colors.BG_INPUT))
        super().__init__(parent, text=label, font=Fonts.SMALL_B, text_color=fg,
                         fg_color=bg, corner_radius=Radius.SM, **kw)
        self.configure(height=24, padx=10)
        self.pack_propagate(False)


class Toast(ctk.CTkToplevel):
    def __init__(self, parent, message, kind="success", duration=2000):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(fg_color=Colors.SUCCESS if kind == "success"
                       else Colors.DANGER if kind == "error" else Colors.PRIMARY)
        ctk.CTkLabel(self, text=message, font=Fonts.BODY_B,
                     text_color="white", padx=16, pady=10).pack()
        self.update_idletasks()
        w = self.winfo_width()
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + 60
        self.geometry(f"+{max(px,0)}+{max(py,0)}")
        self.after(duration, self.destroy)


class EmptyState(ctk.CTkFrame):
    def __init__(self, parent, icon="📭", message="暂无数据", **kw):
        super().__init__(parent, fg_color=Colors.BG_CARD, corner_radius=Radius.LG,
                         border_width=1, border_color=Colors.BORDER, **kw)
        self.configure(height=200)
        self.pack_propagate(False)
        ctk.CTkLabel(self, text=icon, font=(Fonts.FAMILY, 36),
                     text_color=Colors.TEXT_MUTED).place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(self, text=message, font=Fonts.BODY,
                     text_color=Colors.TEXT_MUTED).place(relx=0.5, rely=0.65, anchor="center")
