"""
desktop.ini 读写服务。
"""
from __future__ import annotations

import os
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

from core.constants import DEFAULT_SKIP_NAMES
from core.utils import (
    ensure_folder_system,
    ensure_ini_hidden_system,
    safe_read_config,
    write_config,
)


@dataclass
class FolderRemark:
    """
    子目录备注记录，用于界面与数据层同步。

    Attributes:
        name: 目录名称。
        path: 目录的绝对路径。
        original_remark: 初始读取的备注值，用于脏检查。
        current_remark: 当前编辑后的备注值。
    """

    name: str
    path: Path
    original_remark: str
    current_remark: str


class DesktopIniService:
    """
    desktop.ini 读写核心服务。

    Attributes:
        skip_names: 需要跳过的目录名集合（小写），避免遍历系统目录。
    """

    def __init__(self, skip_names: Set[str] = DEFAULT_SKIP_NAMES) -> None:
        """
        初始化服务，预处理跳过目录名称以统一大小写。

        Args:
            skip_names: 需要忽略的目录名称集合。
        """
        self.skip_names: Set[str] = {name.lower() for name in skip_names}

    def list_subfolders(self, parent: Path) -> List[Path]:
        """
        枚举子目录，自动跳过系统目录与无权限目录。

        Args:
            parent: 需要枚举的父目录。

        Returns:
            经过过滤并排序的子目录路径列表。
        """
        subfolders: List[Path] = []
        if not parent.exists():
            return subfolders
        try:
            with os.scandir(parent) as entries:
                for entry in entries:
                    try:
                        if not entry.is_dir(follow_symlinks=False):
                            continue
                    except PermissionError:
                        continue
                    if entry.name.lower() in self.skip_names:
                        continue
                    subfolders.append(Path(entry.path))
        except PermissionError:
            return subfolders
        return sorted(subfolders)

    def read_info_tip(self, folder: Path) -> str:
        """
        读取目录的 InfoTip（备注）。

        Args:
            folder: 目标目录路径。

        Returns:
            InfoTip 文本，若不存在则返回空字符串。
        """
        ini_path: Path = folder / "desktop.ini"
        parser: ConfigParser = safe_read_config(ini_path)
        section: str = ".ShellClassInfo"
        if not parser.has_section(section):
            return ""
        for option in parser.options(section):
            if option.lower() == "infotip":
                return parser.get(section, option, fallback="")
        return ""

    def write_info_tip(self, folder: Path, remark: str) -> None:
        """
        写入或清理目录的 InfoTip，并保持 desktop.ini 属性正确。

        Args:
            folder: 目标目录路径。
            remark: 需要写入的备注文本；为空时删除 InfoTip。

        Raises:
            FileNotFoundError: 当目录不存在时抛出。
        """
        if not folder.exists():
            raise FileNotFoundError(f"目录不存在: {folder}")
        ensure_folder_system(folder)

        ini_path: Path = folder / "desktop.ini"
        parser: ConfigParser = safe_read_config(ini_path)
        parser.optionxform = str
        section: str = ".ShellClassInfo"
        if section not in parser.sections():
            parser.add_section(section)

        # 清理任意大小写的 InfoTip 冗余键，避免重复。
        for option in list(parser.options(section)):
            if option.lower() == "infotip":
                parser.remove_option(section, option)

        if remark:
            parser.set(section, "InfoTip", remark)
        else:
            if parser.has_option(section, "InfoTip"):
                parser.remove_option(section, "InfoTip")
            if not parser.items(section):
                parser.remove_section(section)

        if not parser.sections():
            if ini_path.exists():
                ini_path.unlink()
            return

        write_config(ini_path, parser)
        ensure_ini_hidden_system(ini_path)
