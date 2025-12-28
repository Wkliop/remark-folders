"""
资源管理器右键菜单的注册与取消。
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List
import winreg

from core.constants import CONTEXT_MENU_NAME
from core.utils import log_message


def _menu_paths(menu_name: str) -> List[str]:
    """
    生成所有需要写入的注册表路径，统一管理根路径结构。

    Args:
        menu_name: 右键菜单名称。

    Returns:
        包含目录、空白区与磁盘三类路径的列表。
    """
    base = r"Software\Classes"
    return [
        fr"{base}\Directory\shell\{menu_name}",
        fr"{base}\Directory\Background\shell\{menu_name}",
        fr"{base}\Drive\shell\{menu_name}",
    ]


def _set_command(key: winreg.HKEYType, command: str) -> None:
    """
    为指定注册表键写入 command 子键。

    Args:
        key: 已打开的注册表键。
        command: 完整的执行命令。
    """
    winreg.SetValue(key, "command", winreg.REG_SZ, command)


def _open_or_create(path: str) -> winreg.HKEYType:
    """
    打开或创建可写注册表键，统一权限配置。

    Args:
        path: 目标注册表路径。

    Returns:
        可写的注册表键句柄。
    """
    return winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        path,
        0,
        winreg.KEY_WRITE,
    )


def register_context_menu(
    python_exe: Path | None,
    target_path: Path,
    menu_name: str = CONTEXT_MENU_NAME,
) -> None:
    """
    注册右键菜单，将菜单动作指向可执行目标。

    Args:
        python_exe: Python 解释器路径；冻结包时传入 None。
        target_path: 目标脚本或可执行文件路径。
        menu_name: 右键菜单名称。
    """
    if python_exe is None:
        command_base: str = f'"{target_path}"'
    else:
        command_base = f'"{python_exe}" "{target_path}"'

    commands: Dict[str, str] = {
        "Directory": f'{command_base} "%V"',
        "Directory\\Background": f'{command_base} "%V"',
        "Drive": f'{command_base} "%1"',
    }

    for path in _menu_paths(menu_name):
        key = _open_or_create(path)
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, menu_name)
        if "Background" in path:
            command = commands["Directory\\Background"]
        elif "Drive" in path:
            command = commands["Drive"]
        else:
            command = commands["Directory"]
        log_message("INFO", f"register menu {path} -> {command}")
        _set_command(key, command)
        winreg.CloseKey(key)


def unregister_context_menu(menu_name: str = CONTEXT_MENU_NAME) -> None:
    """
    取消右键菜单，清理所有相关注册表项。

    Args:
        menu_name: 右键菜单名称。
    """
    for path in _menu_paths(menu_name):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path + r"\command")
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
            log_message("INFO", f"unregister menu {path}")
        except FileNotFoundError:
            continue


def is_context_menu_registered(menu_name: str = CONTEXT_MENU_NAME) -> bool:
    """
    检查右键菜单是否已经存在。

    Args:
        menu_name: 右键菜单名称。

    Returns:
        True 表示任一注册表路径存在，False 表示未注册。
    """
    for path in _menu_paths(menu_name):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ
            )
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            continue
    return False
