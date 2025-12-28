"""
单实例控制：监听本地端口，转发外部请求路径到已运行实例。
"""
from __future__ import annotations

import socket
import threading
from typing import Callable

from core.constants import SINGLE_INSTANCE_HOST, SINGLE_INSTANCE_PORT
from core.utils import log_message


class SingleInstance:
    """
    基于本地 TCP 端口的单实例控制器。

    Attributes:
        host: 监听地址。
        port: 监听端口。
        server_socket: 监听套接字引用。
    """

    def __init__(
        self,
        host: str = SINGLE_INSTANCE_HOST,
        port: int = SINGLE_INSTANCE_PORT,
    ) -> None:
        self.host: str = host
        self.port: int = port
        self.server_socket: socket.socket | None = None

    def try_bind(self) -> bool:
        """
        尝试绑定监听端口，判断是否为首个实例。

        Returns:
            True 表示绑定成功（当前为主实例）；False 表示端口被占用。
        """
        if self.server_socket:
            return True
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            sock.bind((self.host, self.port))
            sock.listen(5)
            self.server_socket = sock
            return True
        except OSError:
            sock.close()
            return False

    def start_accepting(self, handler: Callable[[str], None]) -> None:
        """
        在后台线程接受连接，读取路径字符串并交给回调。

        Args:
            handler: 收到新路径字符串时的回调。
        """
        if not self.server_socket:
            raise RuntimeError("server_socket not initialized.")

        def _run() -> None:
            while True:
                try:
                    conn, _ = self.server_socket.accept()
                except OSError:
                    break
                try:
                    data: bytes = conn.recv(4096)
                    payload: str = data.decode("utf-8").strip()
                    if payload and handler:
                        handler(payload)
                except Exception as exc:  # noqa: BLE001
                    log_message(
                        "ERROR",
                        f"single instance handler error: {exc}",
                    )
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def send_payload(self, payload: str) -> bool:
        """
        作为客户端向已运行实例发送字符串。

        Args:
            payload: 需要转发的路径文本。

        Returns:
            True 表示发送成功；False 表示连接失败。
        """
        try:
            with socket.create_connection(
                (self.host, self.port), timeout=1
            ) as conn:
                conn.sendall(payload.encode("utf-8"))
            return True
        except OSError:
            return False
