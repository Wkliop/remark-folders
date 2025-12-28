"""
常量定义：Windows 文件属性、默认跳过目录以及统一的 UI 文案。
"""

# Windows 文件属性常量，用于调用 Win32 API。
FILE_ATTRIBUTE_HIDDEN: int = 0x0002
FILE_ATTRIBUTE_SYSTEM: int = 0x0004
INVALID_FILE_ATTRIBUTES: int = 0xFFFFFFFF

# 默认跳过的系统目录
DEFAULT_SKIP_NAMES = {"$RECYCLE.BIN", "System Volume Information"}

# 资源管理器右键菜单名称。
CONTEXT_MENU_NAME = "文件夹备注修改"

# UI 文案集中配置。
APP_TITLE = "文件夹备注批量修改"
TEXT_BIND_MENU = "绑定右键菜单"
TEXT_UNBIND_MENU = "取消右键菜单"
TEXT_SELECT_FOLDER = "选择文件夹"
TEXT_REFRESH = "刷新当前路径"
TEXT_MAP_BUTTON = "文件夹名映射备注"
TEXT_SAVE = "保存修改"
TITLE_INFO = "提示"
TITLE_MAPPING = "文件夹名映射备注（文件名->备注）"
TITLE_EDIT_REMARK = "编辑备注"
TITLE_RESULT = "结果"
TITLE_ERROR = "错误"
MSG_MAPPING_HINT = (
    "可 Ctrl+A 复制到外部编辑器，修改后粘贴回来。"
    "格式：文件名->备注；删除备注用 文件名->。"
)
PROMPT_NEW_REMARK = "输入新的备注："
LABEL_DRIVE = "盘符:"
LABEL_CURRENT_PATH_PREFIX = "当前路径："
BUTTON_APPLY = "应用"
BUTTON_CANCEL = "取消"
PLACEHOLDER_LOADING = "..."
COLUMN_HEADER_NAME = "文件夹"
COLUMN_HEADER_REMARK = "备注"
COLUMN_HEADER_PATH = "完整路径"

# 实例通讯配置。
SINGLE_INSTANCE_HOST = "127.0.0.1"
SINGLE_INSTANCE_PORT = 53333
