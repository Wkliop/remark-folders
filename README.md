# 文件夹备注批量修改

- 运行：`python main.py` 可选传入目录参数 `python main.py "D:\\"`
- 打包：`pyinstaller main.py --onefile --windowed --icon icon.ico`
- 右键菜单绑定：在应用内点击“绑定右键菜单”即可将资源管理器菜单指向当前程序；再次点击可取消绑定。通过右键菜单打开目录时，若程序已运行，则会在现有窗口中跳转到该目录
- dist文件夹包含一个已经打包好的exe