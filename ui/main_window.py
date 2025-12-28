"""
Tk 主窗口：目录树、备注表格、文本映射、保存。
"""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Dict, List, Optional, Tuple

from core.ini_service import DesktopIniService, FolderRemark
from core.context_menu import (
    register_context_menu,
    unregister_context_menu,
    is_context_menu_registered,
)
from core.constants import (
    APP_TITLE,
    CONTEXT_MENU_NAME,
    TEXT_BIND_MENU,
    TEXT_UNBIND_MENU,
    TEXT_SELECT_FOLDER,
    TEXT_REFRESH,
    TEXT_MAP_BUTTON,
    TEXT_SAVE,
    TITLE_INFO,
    TITLE_MAPPING,
    TITLE_EDIT_REMARK,
    TITLE_RESULT,
    TITLE_ERROR,
    MSG_MAPPING_HINT,
    PROMPT_NEW_REMARK,
    LABEL_DRIVE,
    LABEL_CURRENT_PATH_PREFIX,
    PLACEHOLDER_LOADING,
    COLUMN_HEADER_NAME,
    COLUMN_HEADER_REMARK,
    COLUMN_HEADER_PATH,
)
from core.utils import ensure_windows_platform, list_drives, log_message
from ui.table_actions import (
    sort_by_column,
    select_all_rows,
    sync_remark_to_rows,
)
from ui.dialogs import mapping_dialog, parse_mapping_lines


class MainApp(tk.Tk):
    """
    主界面：目录树 + 备注表格。

    Attributes:
        service: desktop.ini 读写服务实例。
        rows_by_path: 路径到 FolderRemark 的映射，用于脏检查。
        sort_directions: 列排序方向标记。
        current_path: 当前加载的目录路径。
        initial_path: 启动参数传入的初始路径。
        initial_warning: 路径解析警告信息。
    """

    def __init__(
        self,
        initial_path: Optional[Path] = None,
        initial_warning: Optional[str] = None,
    ) -> None:
        """
        初始化窗口与数据状态，处理启动参数。

        Args:
            initial_path: 启动时要展示的目录；无效时回退到第一块盘符。
            initial_warning: 路径解析产生的警告文案。
        """
        super().__init__()
        ensure_windows_platform()
        self.title(APP_TITLE)
        self.geometry("1200x720")

        self.service: DesktopIniService = DesktopIniService()
        self.rows_by_path: Dict[str, FolderRemark] = {}
        self.sort_directions: Dict[str, bool] = {
            "name": True,
            "remark": True,
            "path": True,
        }
        self.current_path: Optional[Path] = None
        self.initial_path: Optional[Path] = (
            initial_path if initial_path and initial_path.exists() else None
        )
        self.initial_warning: Optional[str] = initial_warning

        self.drive_var: tk.StringVar = tk.StringVar()
        self.dir_tree: ttk.Treeview
        self.table: ttk.Treeview
        self.path_label: tk.Label

        self._build_layout()
        self._init_drives()

    def _build_layout(self) -> None:
        """
        构建界面布局，包括顶部工具栏、目录树和表格区域。
        """
        top_bar: ttk.Frame = ttk.Frame(self)
        top_bar.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(top_bar, text=LABEL_DRIVE).pack(side=tk.LEFT)
        self.drive_combo: ttk.Combobox = ttk.Combobox(
            top_bar,
            textvariable=self.drive_var,
            state="readonly",
            width=10,
        )
        self.drive_combo.pack(side=tk.LEFT, padx=4)
        self.drive_combo.bind("<<ComboboxSelected>>", self._on_drive_changed)

        browse_button: ttk.Button = ttk.Button(
            top_bar, text=TEXT_SELECT_FOLDER, command=self._pick_folder
        )
        browse_button.pack(side=tk.LEFT, padx=4)

        refresh_button: ttk.Button = ttk.Button(
            top_bar, text=TEXT_REFRESH, command=self._refresh_current
        )
        refresh_button.pack(side=tk.LEFT, padx=4)

        self.bind_button_text: tk.StringVar = tk.StringVar(
            value=TEXT_BIND_MENU
        )
        bind_button: ttk.Button = ttk.Button(
            top_bar,
            textvariable=self.bind_button_text,
            command=self._toggle_context_menu,
        )
        bind_button.pack(side=tk.LEFT, padx=4)

        splitter: ttk.Panedwindow = ttk.Panedwindow(
            self, orient=tk.HORIZONTAL
        )
        splitter.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # 左侧目录树。
        left_frame: ttk.Frame = ttk.Frame(splitter)
        self.dir_tree = ttk.Treeview(
            left_frame,
            columns=("fullpath",),
            show="tree",
            selectmode="browse",
        )
        dir_scrollbar: ttk.Scrollbar = ttk.Scrollbar(
            left_frame,
            orient=tk.VERTICAL,
            command=self.dir_tree.yview,
        )
        self.dir_tree.configure(yscrollcommand=dir_scrollbar.set)
        self.dir_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dir_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.dir_tree.bind("<<TreeviewOpen>>", self._on_tree_expand)
        self.dir_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        splitter.add(left_frame, weight=1)

        # 右侧表格。
        right_frame: ttk.Frame = ttk.Frame(splitter)
        action_bar: ttk.Frame = ttk.Frame(right_frame)
        action_bar.pack(fill=tk.X, pady=(0, 6))

        self.path_label = ttk.Label(
            action_bar, text=LABEL_CURRENT_PATH_PREFIX
        )
        self.path_label.pack(side=tk.LEFT)

        mapping_button: ttk.Button = ttk.Button(
            action_bar,
            text=TEXT_MAP_BUTTON,
            command=self._bulk_mapping_dialog,
        )
        save_button: ttk.Button = ttk.Button(
            action_bar, text=TEXT_SAVE, command=self._save_changes
        )
        for widget in (save_button, mapping_button):
            widget.pack(side=tk.RIGHT, padx=4)

        style: ttk.Style = ttk.Style(self)
        style.configure("Bordered.Treeview", borderwidth=1, relief="solid")
        style.configure(
            "Bordered.Treeview.Heading",
            borderwidth=1,
            relief="solid",
        )

        self.table = ttk.Treeview(
            right_frame,
            columns=("name", "remark", "path"),
            show="headings",
            selectmode="extended",
            style="Bordered.Treeview",
        )
        self.table.heading(
            "name",
            text=COLUMN_HEADER_NAME,
            command=lambda: self._sort_by_column("name"),
        )
        self.table.heading(
            "remark",
            text=COLUMN_HEADER_REMARK,
            command=lambda: self._sort_by_column("remark"),
        )
        self.table.heading(
            "path",
            text=COLUMN_HEADER_PATH,
            command=lambda: self._sort_by_column("path"),
        )
        self.table.column("name", width=200, anchor=tk.W, stretch=True)
        self.table.column("remark", width=300, anchor=tk.W, stretch=True)
        self.table.column("path", width=400, anchor=tk.W, stretch=True)

        table_scrollbar: ttk.Scrollbar = ttk.Scrollbar(
            right_frame,
            orient=tk.VERTICAL,
            command=self.table.yview,
        )
        self.table.configure(yscrollcommand=table_scrollbar.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        table_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.table.bind("<Double-1>", self._on_table_double_click)
        self.table.bind("<Control-a>", self._select_all_rows)
        self.table.bind("<Control-A>", self._select_all_rows)

        splitter.add(right_frame, weight=2)

        # 初始化右键绑定按钮状态。
        if is_context_menu_registered(CONTEXT_MENU_NAME):
            self.bind_button_text.set(TEXT_UNBIND_MENU)
        else:
            self.bind_button_text.set(TEXT_BIND_MENU)
        self._show_initial_warning()

    def _init_drives(self) -> None:
        """
        初始化盘符选择，并加载首个目录树节点。
        """
        drives: List[str] = list_drives()
        if not drives:
            messagebox.showerror(TITLE_ERROR, "未找到可用盘符。")
            self.destroy()
            return
        self.drive_combo["values"] = drives

        if self.initial_path:
            target: Path = (
                self.initial_path
                if self.initial_path.is_dir()
                else self.initial_path.parent
            )
            drive_root: str = target.anchor or drives[0]
            if drive_root in drives:
                self.drive_var.set(drive_root)
            else:
                self.drive_var.set(drives[0])
            self._load_tree_root(target)
            return

        self.drive_var.set(drives[0])
        self._load_tree_root(Path(drives[0]))

    def _load_tree_root(self, root_path: Path) -> None:
        """
        设置目录树根节点，并懒加载一级子目录。

        Args:
            root_path: 作为根节点展示的路径。
        """
        self.dir_tree.delete(*self.dir_tree.get_children())
        root_id: str = self.dir_tree.insert(
            "",
            tk.END,
            text=str(root_path),
            values=(str(root_path),),
            open=True,
        )
        self._insert_children(root_id, root_path)
        self.dir_tree.selection_set(root_id)
        self.dir_tree.focus(root_id)
        self._load_directory(root_path)

    def _insert_children(self, node_id: str, path: Path) -> None:
        """
        插入子节点，懒加载更深层目录。

        Args:
            node_id: 目录树节点 ID。
            path: 节点对应的路径。
        """
        for child_id in self.dir_tree.get_children(node_id):
            self.dir_tree.delete(child_id)

        try:
            subfolders: List[Path] = self.service.list_subfolders(path)
        except Exception as exc:
            messagebox.showerror(
                TITLE_ERROR,
                f"读取目录失败: {path}\n{exc}",
            )
            return

        for folder in subfolders:
            child_id: str = self.dir_tree.insert(
                node_id,
                tk.END,
                text=folder.name,
                values=(str(folder),),
                open=False,
            )
            if self._has_subfolder(folder):
                self.dir_tree.insert(
                    child_id,
                    tk.END,
                    text=PLACEHOLDER_LOADING,
                    values=("placeholder",),
                )

    def _has_subfolder(self, path: Path) -> bool:
        """
        检测是否存在子目录，用于决定是否放置懒加载占位符。

        Args:
            path: 需要检测的路径。

        Returns:
            True 表示存在有效子目录，False 表示不存在或访问失败。
        """
        try:
            for child in path.iterdir():
                if (
                    child.is_dir()
                    and child.name.lower() not in self.service.skip_names
                ):
                    return True
        except Exception:
            return False
        return False

    def _on_tree_expand(self, event: tk.Event) -> None:
        """
        展开节点时触发懒加载，防止一次性加载过深目录。

        Args:
            event: Treeview 打开事件。
        """
        node_id: str = self.dir_tree.focus()
        path_str: str = self.dir_tree.set(node_id, "fullpath")
        if not path_str or path_str == "placeholder":
            return
        self._insert_children(node_id, Path(path_str))

    def _on_tree_select(self, event: tk.Event) -> None:
        """
        选中目录后加载子目录备注到表格。

        Args:
            event: Treeview 选中事件。
        """
        selected_ids: Tuple[str, ...] = self.dir_tree.selection()
        if not selected_ids:
            return
        path_str: str = self.dir_tree.set(selected_ids[0], "fullpath")
        if not path_str or path_str == "placeholder":
            return
        self._load_directory(Path(path_str))

    def _load_directory(self, path: Path) -> None:
        """
        加载当前目录的子目录备注，刷新表格与内存模型。

        Args:
            path: 需要展示的目录路径。
        """
        self.current_path = path
        self.path_label.config(text=f"{LABEL_CURRENT_PATH_PREFIX}{path}")
        self.rows_by_path.clear()
        for item in self.table.get_children():
            self.table.delete(item)

        subfolders: List[Path] = self.service.list_subfolders(path)
        for folder in subfolders:
            remark: str = self.service.read_info_tip(folder)
            row: FolderRemark = FolderRemark(
                name=folder.name,
                path=folder,
                original_remark=remark,
                current_remark=remark,
            )
            self.rows_by_path[str(folder)] = row
            self.table.insert(
                "",
                tk.END,
                values=(row.name, row.current_remark, str(row.path)),
            )

    def _on_drive_changed(self, event: tk.Event) -> None:
        """
        切换盘符后重载目录树。

        Args:
            event: Combobox 选择事件。
        """
        drive: str = self.drive_var.get()
        if drive:
            self._load_tree_root(Path(drive))

    def _pick_folder(self) -> None:
        """
        选择任意目录作为树根。
        """
        from tkinter import filedialog

        selected: str = filedialog.askdirectory()
        if selected:
            self._load_tree_root(Path(selected))

    def _refresh_current(self) -> None:
        """
        刷新当前目录，重新读取备注。
        """
        if self.current_path:
            self._load_directory(self.current_path)

    def _selected_item_ids(self) -> List[str]:
        """
        返回当前选中行（按显示顺序），便于批量处理。

        Returns:
            Treeview 选中行的 ID 列表。
        """
        return sorted(self.table.selection(), key=self.table.index)

    def _set_remark_for_paths(self, paths: List[str], remark: str) -> None:
        """
        同步内存模型与表格中的备注值。

        Args:
            paths: 需要更新的路径集合。
            remark: 要写入的新备注。
        """
        sync_remark_to_rows(self.table, self.rows_by_path, paths, remark)

    def handle_external_path(self, payload: str) -> None:
        """
        处理其他进程转发的路径请求，在当前实例中打开目标目录。

        Args:
            payload: 外部进程传递的路径字符串。
        """

        def _process() -> None:
            self.lift()
            try:
                self.focus_force()
            except Exception:
                pass

            target_text: str = payload.strip()
            if not target_text:
                return

            target_path: Path = Path(target_text)
            if not target_path.exists():
                messagebox.showerror(
                    TITLE_ERROR, f"路径不存在：{target_path}"
                )
                return

            directory: Path = (
                target_path if target_path.is_dir() else target_path.parent
            )
            drive_root: str = directory.anchor
            if drive_root and drive_root in self.drive_combo["values"]:
                self.drive_var.set(drive_root)
            self._load_tree_root(directory)

        self.after(0, _process)

    def _on_table_double_click(self, event: tk.Event) -> None:
        """
        双击备注列时弹出编辑框。

        Args:
            event: 双击事件。
        """
        item_id: str = self.table.identify_row(event.y)
        column: str = self.table.identify_column(event.x)
        if not item_id or column != "#2":
            return
        values: Tuple[str, str, str] = self.table.item(
            item_id, "values"
        )  # type: ignore[assignment]
        if len(values) < 3:
            return
        current: str = values[1]
        new_remark: Optional[str] = simpledialog.askstring(
            TITLE_EDIT_REMARK,
            PROMPT_NEW_REMARK,
            initialvalue=current,
        )
        if new_remark is None:
            return
        self._set_remark_for_paths([values[2]], new_remark)

    def _bulk_mapping_dialog(self) -> None:
        """
        通过文本映射批量修改备注，格式“文件名->备注”。
        """
        item_ids: List[str] = self._selected_item_ids()
        if not item_ids:
            messagebox.showinfo(TITLE_INFO, "请先选择至少一行。")
            return

        mappings: List[Tuple[str, str, str]] = []
        for item_id in item_ids:
            values: Tuple[str, str, str] = self.table.item(
                item_id, "values"
            )  # type: ignore[assignment]
            if len(values) < 3:
                continue
            mappings.append((values[0], values[1], values[2]))

        def apply_callback(text_widget: tk.Text, dialog: tk.Toplevel) -> None:
            mapping_dict: Dict[str, str] = parse_mapping_lines(
                text_widget, dialog
            )
            if not mapping_dict:
                return

            applied: List[str] = []
            missing: List[str] = []
            extra: List[str] = []
            unchanged: List[str] = []

            name_to_info: Dict[str, Tuple[str, str]] = {
                name: (remark, path) for name, remark, path in mappings
            }
            for name, remark in mapping_dict.items():
                if name in name_to_info:
                    current_remark, path = name_to_info[name]
                    if remark == current_remark:
                        unchanged.append(name)
                        continue
                    self._set_remark_for_paths([path], remark)
                    applied.append(name)
                else:
                    extra.append(name)

            for name in name_to_info:
                if name not in mapping_dict:
                    missing.append(name)

            messages: List[str] = []
            if applied:
                messages.append(f"已应用：{', '.join(applied)}")
            if unchanged:
                messages.append(f"未变更：{', '.join(unchanged)}")
            if missing:
                messages.append(f"未提供备注：{', '.join(missing)}")
            if extra:
                messages.append(
                    f"多余文件名（未匹配选中项）：{', '.join(extra)}"
                )

            if messages:
                messagebox.showinfo(
                    TITLE_RESULT, "\n".join(messages), parent=dialog
                )
            if missing or extra:
                return
            dialog.destroy()

        mapping_dialog(
            self,
            mappings,
            apply_callback,
            title=TITLE_MAPPING,
            hint=MSG_MAPPING_HINT,
        )

    def _save_changes(self) -> None:
        """
        将修改写入 desktop.ini 并展示处理结果。
        """
        changed: List[FolderRemark] = [
            row
            for row in self.rows_by_path.values()
            if row.current_remark != row.original_remark
        ]
        if not changed:
            messagebox.showinfo(TITLE_INFO, "没有需要保存的修改。")
            return

        success_items: List[str] = []
        failed_items: List[Tuple[str, str]] = []
        for row in changed:
            try:
                self.service.write_info_tip(row.path, row.current_remark)
                row.original_remark = row.current_remark
                success_items.append(row.name)
            except Exception as exc:
                failed_items.append((row.name, str(exc)))

        total_count: int = len(changed)
        success_count: int = len(success_items)
        failed_count: int = len(failed_items)

        messages: List[str] = [
            f"处理总数: {total_count} | 成功: {success_count}"
            f" | 失败: {failed_count}"
        ]
        if success_items:
            messages.append(
                f"成功项({success_count}): {', '.join(success_items)}"
            )
        if failed_items:
            messages.append("失败项列表：")
            for name, reason in failed_items:
                messages.append(f"- {name}: {reason}")

        messagebox.showinfo(TITLE_RESULT, "\n".join(messages))
        if self.current_path:
            self._load_directory(self.current_path)

    def _sort_by_column(self, column: str) -> None:
        """
        按列排序表格，仅影响显示。

        Args:
            column: 目标列名。
        """
        sort_by_column(self.table, column, self.sort_directions)

    def _select_all_rows(self, event: tk.Event) -> str:
        """
        Ctrl+A 全选表格行。

        Args:
            event: 键盘事件。

        Returns:
            固定返回 "break" 以阻断默认快捷键行为。
        """
        select_all_rows(self.table)
        return "break"

    def _toggle_context_menu(self) -> None:
        """
        注册/取消资源管理器右键菜单，保持按钮文案同步。
        """
        try:
            is_frozen: bool = getattr(sys, "frozen", False)
            python_exe: Path | None = (
                None if is_frozen else Path(sys.executable)
            )
            project_dir: Path = Path(__file__).resolve().parents[1]
            target: Path = (
                Path(sys.executable)
                if is_frozen
                else project_dir / "main.py"
            )
            if is_context_menu_registered(CONTEXT_MENU_NAME):
                unregister_context_menu(CONTEXT_MENU_NAME)
                self.bind_button_text.set(TEXT_BIND_MENU)
                messagebox.showinfo(TITLE_INFO, "已取消右键菜单。")
            else:
                register_context_menu(
                    python_exe,
                    target,
                    CONTEXT_MENU_NAME,
                )
                self.bind_button_text.set(TEXT_UNBIND_MENU)
                messagebox.showinfo(TITLE_INFO, "已绑定右键菜单。")
        except Exception as exc:
            log_message("ERROR", f"context menu toggle failed: {exc}")
            messagebox.showerror(TITLE_ERROR, f"操作失败：{exc}")

    def _show_initial_warning(self) -> None:
        """
        启动时提示路径回退信息，便于用户理解初始状态。
        """
        if self.initial_warning:
            messagebox.showinfo(TITLE_INFO, self.initial_warning)
