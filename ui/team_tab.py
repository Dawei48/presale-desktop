"""
团队管理 - 管理员增删成员，设置角色
"""
import customtkinter as ctk
from ui.styles import Colors, Fonts, Spacing, Radius
from ui.components import Dialog, ConfirmDialog, Toast, EmptyState


class MemberDialog(Dialog):
    """新增/编辑成员对话框"""

    def __init__(self, parent, member: dict = None, on_save=None, db=None):
        self.member = member
        self.on_save = on_save
        self.db = db
        is_edit = member is not None
        title = "编辑成员" if is_edit else "新增成员"
        super().__init__(parent, title, width=400, height=340)

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=Spacing.XL, pady=Spacing.XL)
        form.columnconfigure(1, weight=1)

        self.entry_username = self._make_field(form, "用户名 *", 0)
        self.entry_name = self._make_field(form, "显示名称 *", 1)
        self.entry_password = self._make_field(form, "密码" + ("" if is_edit else " *"), 2, show="•")

        # 角色选择
        ctk.CTkLabel(form, text="角色", font=Fonts.BODY,
                     text_color=Colors.TEXT_SECONDARY).grid(
            row=3, column=0, sticky="w", pady=(Spacing.SM, 2))
        self.combo_role = ctk.CTkComboBox(
            form, values=["管理员", "成员"], font=Fonts.BODY, height=36,
            border_color=Colors.BORDER, fg_color=Colors.BG_INPUT,
            button_color=Colors.PRIMARY, corner_radius=Radius.SM)
        self.combo_role.grid(row=3, column=1, sticky="ew", pady=(Spacing.SM, 2))

        # 提示
        if not is_edit:
            ctk.CTkLabel(form, text="成员默认密码为 123456，登录后可自行修改",
                         font=Fonts.TINY, text_color=Colors.TEXT_MUTED).grid(
                row=4, column=0, columnspan=2, sticky="w", pady=(0, 4))
            self.entry_password.insert(0, "123456")

        self._make_buttons(form, row=5)

        # 填充编辑数据
        if is_edit:
            self.entry_username.insert(0, member["username"])
            self.entry_name.insert(0, member["display_name"])
            self.entry_password.configure(placeholder_text="留空则不修改")
            if member.get("role") == "admin":
                self.combo_role.set("管理员")
            else:
                self.combo_role.set("成员")

    def _on_ok(self):
        username = self.entry_username.get().strip()
        display_name = self.entry_name.get().strip()
        password = self.entry_password.get().strip()
        role = "admin" if self.combo_role.get() == "管理员" else "member"

        if not username or not display_name:
            Toast(self, "用户名和显示名称不能为空", "error")
            return

        if not self.member and not password:
            Toast(self, "密码不能为空", "error")
            return

        # 检查用户名重复
        if self.db and (not self.member or self.member["username"] != username):
            if self.db.user_exists(username):
                Toast(self, "用户名已存在", "error")
                return

        self.result = {
            "username": username,
            "display_name": display_name,
            "role": role,
        }
        if password:
            self.result["password"] = password

        if self.on_save:
            self.on_save(self.result)
        self.destroy()


class TeamTab(ctk.CTkFrame):
    def __init__(self, parent, db, current_user):
        super().__init__(parent, fg_color=Colors.BG_MAIN)
        self.db = db
        self.current_user = current_user
        self.is_admin = current_user.get("role") == "admin"

        self._build()
        self._load()

    def _build(self):
        # ── 标题 ──────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.XL, pady=(Spacing.XL, Spacing.LG))

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="团队管理", font=Fonts.H1,
                     text_color=Colors.TEXT_PRIMARY).pack(side="left")

        if self.is_admin:
            right = ctk.CTkFrame(header, fg_color="transparent")
            right.pack(side="right")
            ctk.CTkButton(right, text="＋ 新增成员", font=Fonts.BODY_B, height=36,
                          fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER,
                          corner_radius=Radius.SM,
                          command=self._add).pack(side="right")

        # ── 成员列表 ──────────────────────
        self.list_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=Spacing.XL,
                             pady=(0, Spacing.XL))

    def _load(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        users = self.db.get_users()

        # 表头
        header = ctk.CTkFrame(self.list_frame, fg_color="transparent", height=36)
        header.pack(fill="x", pady=(0, Spacing.SM))
        header.pack_propagate(False)

        headers = [("用户名", 140), ("显示名称", 160), ("角色", 100), ("创建时间", 160)]
        if self.is_admin:
            headers.append(("操作", 120))
        for i, (h, w) in enumerate(headers):
            ctk.CTkLabel(header, text=h, font=Fonts.SMALL_B,
                         text_color=Colors.TEXT_MUTED, anchor="w", width=w).grid(
                row=0, column=i, sticky="w", padx=Spacing.MD)

        for idx, user in enumerate(users):
            bg = Colors.BG_INPUT if idx % 2 == 0 else "transparent"
            row = ctk.CTkFrame(self.list_frame, fg_color=bg,
                               corner_radius=Radius.SM, height=44)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            # 当前用户高亮
            is_self = user["id"] == self.current_user["id"]

            vals = [
                user["username"] + (" (我)" if is_self else ""),
                user["display_name"],
                "👑 管理员" if user["role"] == "admin" else "成员",
                user.get("created_at", "")[:10],
            ]

            widths = [140, 160, 100, 160]
            for i, v in enumerate(vals):
                color = Colors.TEXT_PRIMARY if not is_self else Colors.PRIMARY
                ctk.CTkLabel(row, text=v, font=Fonts.BODY,
                             text_color=color, anchor="w", width=widths[i]).grid(
                    row=0, column=i, sticky="w", padx=Spacing.MD)

            if self.is_admin:
                btn_f = ctk.CTkFrame(row, fg_color="transparent")
                btn_f.grid(row=0, column=len(vals), sticky="w", padx=Spacing.MD)

                ctk.CTkButton(btn_f, text="编辑", font=Fonts.SMALL, width=48, height=26,
                              fg_color="transparent", hover_color=Colors.PRIMARY_LIGHT,
                              text_color=Colors.PRIMARY, corner_radius=Radius.SM,
                              command=lambda u=user: self._edit(u)).pack(side="left", padx=2)

                # 不允许删除自己和最后一个管理员
                can_delete = not is_self
                if can_delete and user["role"] == "admin":
                    admin_count = sum(1 for u in users if u["role"] == "admin")
                    can_delete = admin_count > 1

                if can_delete:
                    ctk.CTkButton(btn_f, text="删除", font=Fonts.SMALL, width=48, height=26,
                                  fg_color="transparent", hover_color=Colors.DANGER_LIGHT,
                                  text_color=Colors.DANGER, corner_radius=Radius.SM,
                                  command=lambda u=user: self._delete(u)).pack(side="left", padx=2)

    def _add(self):
        def on_save(data):
            self.db.add_user(data["username"], data["password"],
                             data["display_name"], data["role"])
            self.db.log("新增成员", f"用户: {data['username']}",
                        self.current_user["id"], self.current_user["username"])
            Toast(self, "✅ 成员已添加")
            self._load()
        MemberDialog(self, on_save=on_save, db=self.db)

    def _edit(self, user: dict):
        def on_save(data):
            kwargs = {}
            if "password" in data:
                kwargs["password"] = data["password"]
            self.db.update_user(user["id"],
                                display_name=data["display_name"],
                                role=data["role"],
                                **kwargs)
            self.db.log("编辑成员", f"用户: {data['username']}",
                        self.current_user["id"], self.current_user["username"])
            Toast(self, "✅ 成员信息已更新")
            self._load()
        MemberDialog(self, member=user, on_save=on_save, db=self.db)

    def _delete(self, user: dict):
        d = ConfirmDialog(self, f"确定要删除成员「{user['display_name']}」吗？")
        self.wait_window(d)
        if d.result:
            self.db.delete_user(user["id"])
            self.db.log("删除成员", f"用户: {user['username']}",
                        self.current_user["id"], self.current_user["username"])
            Toast(self, "🗑️ 成员已删除")
            self._load()

    def refresh(self):
        self._load()
