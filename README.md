# 索尼原始对焦框看图工具（Windows）

Windows 10/11 桌面看图程序。浏览照片所在文件夹，使用方向键切换、滚轮缩放、鼠标拖动平移；按 **F** 显示或隐藏相机记录的对焦框。支持 ARW、JPEG、PNG、HEIC 等常见照片。只有读取到索尼 ARW 原始对焦坐标时才画框，不从像素推测。

打开 ARW 时先显示文件内嵌预览，然后在后台解码完整 RAW。检查是否真正清晰时，点击 **100%** 查看完整 RAW。RAW 解码比预览慢，也会占用更多内存。

## 下载或在 Windows 构建

仓库的 **Actions → Build Windows app** 会生成 `SonyFocusViewer-Windows` 构建产物，解压后得到 `SonyFocusViewer.exe`。可直接运行，无需在 Windows 上安装 Python。首次打开可能需要等待系统安全检查；此版本尚未购买代码签名证书。

也可以在自己的 Windows 电脑上构建：

1. 安装 [Python 3.11 x64](https://www.python.org/downloads/)，勾选 Python Launcher。
2. 双击 `build-windows.bat`。完成后得到 `dist\SonyFocusViewer.exe`，可先直接运行。若从 Actions 下载，请把该文件放入此目录的 `dist` 文件夹再执行下一步。
3. 如需将它加入 Windows 的“打开方式”和“默认应用”，在 PowerShell 中进入此目录，执行 `powershell -ExecutionPolicy Bypass -File .\install-for-user.ps1`，然后在 Windows 默认应用设置中选它。Windows 不允许普通安装脚本直接覆盖用户已有的默认应用选择。

程序和照片均在本地运行；不上传照片。

## 快捷键

| 操作 | 快捷键 |
| --- | --- |
| 打开照片 | Ctrl+O |
| 打开文件夹 | Ctrl+Shift+O |
| 上一张／下一张 | 左／右方向键 |
| 原始对焦框开关 | F |
| 适合窗口 | Ctrl+0 |
| 100% | Ctrl+1 |

可在资源管理器中右键照片选择“打开方式”，或把文件路径传给 `SonyFocusViewer.exe`。本版读取 A7C II 样片的 `FocusLocation` 和 `FocusFrameSize`。其他索尼机型若使用不同 MakerNote 布局，会显示照片但不画框。
