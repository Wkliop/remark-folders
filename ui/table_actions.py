"""
表格相关操作：排序、全选、行编辑同步。
"""
from __future__ import annotations

from tkinter import ttk
from typing import Dict, List, Tuple

from core.ini_service import FolderRemark


def sort_by_column(
    table: ttk.Treeview,
    column: str,
    sort_directions: Dict[str, bool],
) -> None:
    """
    按列排序表格，仅影响显示顺序。

    Args:
        table: 需要排序的 Treeview 控件。
        column: 目标列名，支持 ``name``/``remark``/``path``。
        sort_directions: 列到排序方向的布尔映射，True 表示升序。
    """
    index_map: Dict[str, int] = {"name": 0, "remark": 1, "path": 2}
    if column not in index_map:
        return
    reverse: bool = sort_directions.get(column, True)
    items: List[str] = list(table.get_children(""))

    def sort_key(item_id: str) -> str:
        values: Tuple[str, str, str] = table.item(
            item_id, "values"
        )  # type: ignore[assignment]
        if len(values) <= index_map[column]:
            return ""
        return values[index_map[column]].lower()

    items.sort(key=sort_key, reverse=not reverse)
    for idx, item_id in enumerate(items):
        table.move(item_id, "", idx)
    sort_directions[column] = not reverse


def select_all_rows(table: ttk.Treeview) -> None:
    """
    全选表格行，便于批量操作。

    Args:
        table: 目标 Treeview 控件。
    """
    all_rows: Tuple[str, ...] = table.get_children()
    table.selection_set(all_rows)


def sync_remark_to_rows(
    table: ttk.Treeview,
    rows_by_path: Dict[str, FolderRemark],
    paths: List[str],
    remark: str,
) -> None:
    """
    更新表格显示与内存模型中的备注值，保持一致性。

    Args:
        table: 目标 Treeview 控件。
        rows_by_path: 路径到 FolderRemark 的映射。
        paths: 需要更新的路径列表。
        remark: 要写入的新备注值。
    """
    for item_id in table.get_children():
        values: Tuple[str, str, str] = table.item(
            item_id, "values"
        )  # type: ignore[assignment]
        if len(values) < 3:
            continue
        path_str: str = values[2]
        if path_str in paths:
            updated: Tuple[str, str, str] = (values[0], remark, path_str)
            table.item(item_id, values=updated)
            if path_str in rows_by_path:
                rows_by_path[path_str].current_remark = remark
