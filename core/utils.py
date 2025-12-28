"""
通用工具函数：平台校验、盘符枚举、文件属性操作、desktop.ini 读写与轻量日志。
"""
from __future__ import annotations

import ctypes
import os
import tempfile
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import List

from core.constants import (
    FILE_ATTRIBUTE_HIDDEN,
    FILE_ATTRIBUTE_SYSTEM,
    INVALID_FILE_ATTRIBUTES,
)


def ensure_windows_platform() -> None:
    """
    确保仅在 Windows 平台运行，避免 Win32 API 调用在其他平台崩溃。

    Raises:
        EnvironmentError: 当在非 Windows 平台调用时抛出。
    """
    if os.name != "nt":
        raise EnvironmentError("本工具仅支持 Windows。")


def list_drives() -> List[str]:
    """
    枚举系统盘符，便于初始化目录树的根节点。

    Returns:
        包含盘符字符串的列表（例如 ``['C:\\\\', 'D:\\\\']``）。
    """
    buf_len: int = ctypes.windll.kernel32.GetLogicalDriveStringsW(0, None)
    buf: ctypes.Array = ctypes.create_unicode_buffer(buf_len)
    ctypes.windll.kernel32.GetLogicalDriveStringsW(buf_len, buf)
    raw: str = buf[: buf_len]
    return [item for item in raw.split("\x00") if item]


def get_file_attributes(path: Path) -> int:
    """
    读取文件或目录的属性值，确保无效路径及时失败。

    Args:
        path: 目标文件或目录的完整路径。

    Returns:
        Win32 文件属性整数值。

    Raises:
        FileNotFoundError: 当路径不存在或属性读取返回无效值时抛出。
    """
    attr: int = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    if attr == INVALID_FILE_ATTRIBUTES:
        raise FileNotFoundError(f"无法读取属性: {path}")
    return attr


def set_file_attributes(path: Path, attributes: int) -> None:
    """
    设置文件或目录的属性值，失败时快速失败。

    Args:
        path: 目标文件或目录的完整路径。
        attributes: 需要设置的 Win32 属性位掩码。

    Raises:
        OSError: 当 Win32 API 返回失败时抛出。
    """
    ok: int = ctypes.windll.kernel32.SetFileAttributesW(str(path), attributes)
    if ok == 0:
        raise OSError(f"设置属性失败: {path}")


def safe_read_config(ini_path: Path) -> ConfigParser:
    """
    宽容读取 desktop.ini；若编码异常则返回空配置以避免阻塞主流程。

    Args:
        ini_path: 目标 desktop.ini 路径。

    Returns:
        已加载内容的 ConfigParser；若读取失败则为空实例。
    """
    parser: ConfigParser = ConfigParser()
    parser.optionxform = str
    if not ini_path.exists():
        return parser
    for encoding in ("utf-16", "utf-8-sig", "mbcs"):
        try:
            text: str = ini_path.read_text(encoding=encoding)
            parser.read_string(text)
            return parser
        except Exception:
            continue
    return parser


def write_config(ini_path: Path, parser: ConfigParser) -> None:
    """
    使用 utf-16 持久化 desktop.ini，保持与资源管理器一致的编码。

    Args:
        ini_path: 目标 desktop.ini 路径。
        parser: 已填充的配置对象。
    """
    with ini_path.open("w", encoding="utf-16") as ini_file:
        parser.write(ini_file)


def ensure_folder_system(folder: Path) -> None:
    """
    将目录标记为 SYSTEM 属性，确保 InfoTip 能被资源管理器识别。

    Args:
        folder: 需要标记的目录路径。

    Raises:
        FileNotFoundError: 当目录不存在时由 get_file_attributes 抛出。
        OSError: 当设置属性失败时抛出。
    """
    attributes: int = get_file_attributes(folder)
    if attributes & FILE_ATTRIBUTE_SYSTEM:
        return
    set_file_attributes(folder, attributes | FILE_ATTRIBUTE_SYSTEM)


def ensure_ini_hidden_system(ini_path: Path) -> None:
    """
    将 desktop.ini 标记为隐藏+系统属性，避免用户误删。

    Args:
        ini_path: desktop.ini 文件路径。

    Raises:
        FileNotFoundError: 当文件不存在时由 get_file_attributes 抛出。
        OSError: 当设置属性失败时抛出。
    """
    attributes: int = get_file_attributes(ini_path)
    target: int = attributes | FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM
    if target != attributes:
        set_file_attributes(ini_path, target)


def log_message(level: str, message: str) -> None:
    """
    追加简单日志到系统临时目录，便于问题追踪且不影响主流程。

    Args:
        level: 日志等级标签，例如 ``\"INFO\"``、``\"ERROR\"``。
        message: 需要记录的文本内容。

    Notes:
        写日志失败时会忽略异常，保证业务逻辑不中断。
    """
    try:
        log_dir: Path = Path(tempfile.gettempdir())
        log_file: Path = log_dir / "desktopini_tool.log"
        timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_file.open("a", encoding="utf-8", errors="ignore") as f:
            f.write(f"{timestamp} [{level}] {message}\n")
    except Exception:
        return
