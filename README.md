# 索尼原始对焦框看图工具（Windows / macOS）

Windows 10/11 和 macOS 桌面看图程序。浏览照片所在文件夹，使用方向键切换、滚轮缩放、鼠标拖动平移；按 **F** 显示或隐藏相机记录的对焦框。支持 ARW、JPEG、PNG、HEIC 等常见照片。只有读取到索尼 ARW 原始对焦坐标时才画框，不从像素推测。

打开 ARW 时先显示文件内嵌预览，然后在后台解码完整 RAW。检查是否真正清晰时，点击 **100%** 查看完整 RAW。RAW 解码比预览慢，也会占用更多内存。

完整 RAW 的显示亮度会参考相机内嵌预览自动调整，避免从预览切换时突然变暗；这只影响屏幕显示，不修改 ARW 文件。不同的 RAW 解码器仍可能呈现不同的颜色和对比度。

## 下载或在 Windows 构建

仓库的 **Actions → Build Windows app** 会生成 `SonyFocusViewer-Windows` 构建产物，解压后得到 `SonyFocusViewer.exe`。可直接运行，无需在 Windows 上安装 Python。首次打开可能需要等待系统安全检查；此版本尚未购买代码签名证书。

也可以在自己的 Windows 电脑上构建：

1. 安装 [Python 3.11 x64](https://www.python.org/downloads/)，勾选 Python Launcher。
2. 双击 `build-windows.bat`。完成后得到 `dist\SonyFocusViewer.exe`，可先直接运行。若从 Actions 下载，请把该文件放入此目录的 `dist` 文件夹再执行下一步。
3. 如需将它加入 Windows 的“打开方式”和“默认应用”，在 PowerShell 中进入此目录，执行 `powershell -ExecutionPolicy Bypass -File .\install-for-user.ps1`，然后在 Windows 默认应用设置中选它。Windows 不允许普通安装脚本直接覆盖用户已有的默认应用选择。

程序和照片均在本地运行；不上传照片。

## macOS 版本

仓库的 **Actions → Build macOS app** 会生成 Apple Silicon（M 系列芯片）的 `SonyFocusViewer-macOS-arm64` 构建产物。解压出 `SonyFocusViewer.app` 后拖到“应用程序”文件夹即可使用。也可在 Mac 上运行 `bash build-macos.sh` 自行构建；产物位于 `dist/`。

Finder 中右键照片，选择“打开方式 → Sony Focus Viewer”。如果要设为默认看图软件，在照片的“显示简介 → 打开方式”中选择它，再点“全部更改”。首次打开未经公证的构建版本时，可能需要右键应用选择“打开”。

macOS 使用 **⌘O** 打开照片、**⌘⇧O** 打开文件夹、**⌘0** 适合窗口、**⌘1** 查看 100%；其余按键与下表相同。应用也支持从 Finder 拖入照片或文件夹。

## 快捷键

| 操作 | 快捷键 |
| --- | --- |
| 打开照片 | Windows: Ctrl+O / macOS: ⌘O |
| 打开文件夹 | Windows: Ctrl+Shift+O / macOS: ⌘⇧O |
| 上一张／下一张 | 左／右方向键 |
| 原始对焦框开关 | F |
| 适合窗口 | Windows: Ctrl+0 / macOS: ⌘0 |
| 100% | Windows: Ctrl+1 / macOS: ⌘1 |

可在资源管理器中右键照片选择“打开方式”，或把文件路径传给 `SonyFocusViewer.exe`。本版读取 A7C II 样片的 `FocusLocation` 和 `FocusFrameSize`。其他索尼机型若使用不同 MakerNote 布局，会显示照片但不画框。

## 参考项目

[Focus Points](https://github.com/FocusPointsLrC/Focus-Points) 是 Lightroom Classic 插件，主体采用 Apache 2.0 许可证，仓库另含 GPLv2 组件。它对索尼 `FocusLocation` / `FocusFrameSize` 的解释与本工具的 A7C II 样片一致；其文档还提醒，在非原生画幅比例下需要校正对焦坐标区域与输出画面的中心偏移。本工具据此加入了几何位置校正，没有复制其代码。其他相机记录的 PDAF 点、面部和主体框应与实际对焦框分开显示；目前没有把它们混作对焦结果。
