"""
对话框：文本映射备注。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Tuple, Callable

from core.constants import TITLE_ERROR, TITLE_INFO, BUTTON_APPLY, BUTTON_CANCEL


def mapping_dialog(
    parent: tk.Tk,
    mappings: List[Tuple[str, str, str]],
    apply_callback: Callable[[tk.Text, tk.Toplevel], None],
    title: str,
    hint: str,
) -> None:
    """
    弹出文本映射对话框，让用户批量编辑备注。

    Args:
        parent: 主窗口引用，用于设置模态。
        mappings: 现有映射列表，三元组为 (名称, 备注, 路径)。
        apply_callback: 点击“应用”时的处理回调。
        title: 对话框标题。
        hint: 顶部提示文案。
    """
    dialog: tk.Toplevel = tk.Toplevel(parent)
    dialog.title(title)
    dialog.transient(parent)
    dialog.grab_set()

    ttk.Label(dialog, text=hint).pack(anchor=tk.W, padx=10, pady=6)

    text_widget: tk.Text = tk.Text(
        dialog,
        width=100,
        height=max(10, len(mappings)),
    )
    text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    text_lines: List[str] = [
        f"{name}->{remark}" for name, remark, _ in mappings
    ]
    text_widget.insert("1.0", "\n".join(text_lines))

    button_frame: ttk.Frame = ttk.Frame(dialog)
    button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

    def on_apply() -> None:
        apply_callback(text_widget, dialog)

    ttk.Button(button_frame, text=BUTTON_APPLY, command=on_apply).pack(
        side=tk.RIGHT, padx=4
    )
    ttk.Button(button_frame, text=BUTTON_CANCEL, command=dialog.destroy).pack(
        side=tk.RIGHT, padx=4
    )


def parse_mapping_lines(
    text_widget: tk.Text, dialog: tk.Toplevel
) -> Dict[str, str]:
    """
    解析文本框内容为映射并校验格式。

    Args:
        text_widget: 承载用户输入的文本框。
        dialog: 当前对话框，用于展示校验错误。

    Returns:
        合法的名称到备注的映射字典；若格式错误则返回空字典并弹窗提示。
    """
    raw_lines: List[str] = text_widget.get("1.0", tk.END).splitlines()
    mapping_dict: Dict[str, str] = {}
    line_no: int = 0
    for line in raw_lines:
        line_no += 1
        stripped: str = line.strip()
        if not stripped:
            continue
        if "->" not in stripped:
            messagebox.showerror(
                TITLE_ERROR,
                f"第 {line_no} 行缺少 '->'：{line}",
                parent=dialog,
            )
            return {}
        name_part, remark_part = stripped.split("->", 1)
        if not name_part.strip():
            messagebox.showerror(
                TITLE_ERROR,
                f"第 {line_no} 行文件名为空：{line}",
                parent=dialog,
            )
            return {}
        mapping_dict[name_part.strip()] = remark_part
    if not mapping_dict:
        messagebox.showinfo(
            TITLE_INFO, "没有可用的映射，请检查输入。", parent=dialog
        )
        return {}
    return mapping_dict
