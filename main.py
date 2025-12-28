"""
入口：启动 Tk 界面；运行命令：python main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from ui.main_window import MainApp
from core.utils import log_message
from core.single_instance import SingleInstance


def _normalize_path_arg(raw: str) -> tuple[Path | None, str | None]:
    """
    规范化右键传入的路径，处理裸盘符等特殊格式。

    Args:
        raw: 原始命令行参数文本，可能包含引号或缺少反斜杠。

    Returns:
        规范化后的路径（若无效则为 None）与可选的警告信息。
    """
    text: str = raw.strip().strip('"')
    if not text:
        return None, None
    if len(text) == 2 and text.endswith(":"):
        text = text + "\\"
    try:
        return Path(text).expanduser().resolve(), None
    except Exception:
        return None, "传入的路径无效，已回退到默认盘符。"


def main() -> None:
    """
    解析初始路径参数并启动 Tk 主窗口。
    """
    initial_path: Path | None = None
    initial_warning: str | None = None
    if len(sys.argv) > 1:
        initial_path, initial_warning = _normalize_path_arg(sys.argv[1])
        if initial_warning:
            log_message("WARN", initial_warning)

    # 单实例：尝试作为主实例，失败则转发路径到已运行实例并退出。
    instance: SingleInstance = SingleInstance()
    payload: str = str(initial_path) if initial_path else ""
    if not instance.try_bind():
        if instance.send_payload(payload):
            log_message("INFO", "已将路径交给已运行实例处理，当前进程退出。")
            return
        log_message(
            "ERROR",
            "已检测到正在运行的实例且转发失败，当前进程退出以保证单实例。",
        )
        return

    app: MainApp = MainApp(initial_path, initial_warning)
    if instance.server_socket:
        instance.start_accepting(app.handle_external_path)
    app.mainloop()


if __name__ == "__main__":
    main()
