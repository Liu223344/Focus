"""Sony Focus Viewer: a local, Windows-first photo browser."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import sys

from PIL import Image, ImageOps
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

from PySide6.QtCore import QEvent, Qt, QThread, Signal
from PySide6.QtGui import QAction, QColor, QImage, QKeySequence, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QGraphicsPixmapItem, QGraphicsRectItem,
    QGraphicsScene, QGraphicsView, QLabel, QMainWindow, QMessageBox,
    QStatusBar, QToolBar,
)

from sony_raw import FocusFrame, orient_focus, read_arw


EXTENSIONS = {".arw", ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".gif", ".heic", ".heif"}
FILE_FILTER = "照片 (*.arw *.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff *.gif *.heic *.heif);;所有文件 (*)"
ORIENTATION_OPS = {3: Image.Transpose.ROTATE_180, 6: Image.Transpose.ROTATE_270, 8: Image.Transpose.ROTATE_90}


def natural_key(path: Path):
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", path.name)]


def to_qimage(image: Image.Image) -> QImage:
    rgb = image.convert("RGB")
    width, height = rgb.size
    return QImage(rgb.tobytes(), width, height, width * 3, QImage.Format.Format_RGB888).copy()


def rotate_image(image: Image.Image, orientation: int) -> Image.Image:
    operation = ORIENTATION_OPS.get(orientation)
    return image.transpose(operation) if operation else image


class RawDecodeThread(QThread):
    decoded = Signal(int, object)
    failed = Signal(int, str)

    def __init__(self, request_id: int, path: Path, orientation: int,
                 image_width: int, image_height: int, parent=None):
        super().__init__(parent)
        self.request_id = request_id
        self.path = path
        self.orientation = orientation
        self.image_width = image_width
        self.image_height = image_height

    def run(self):
        try:
            import rawpy
            with rawpy.imread(str(self.path)) as raw:
                # Disable LibRaw's rotation so the EXIF orientation is applied
                # to both image and recorded AF coordinates in the same way.
                pixels = raw.postprocess(use_camera_wb=True, no_auto_bright=True,
                                         output_bps=8, user_flip=0)
            image = Image.fromarray(pixels, "RGB")
            # LibRaw may expose a narrow sensor border beyond the camera's
            # recorded image dimensions (A7C II: 7040x4688 vs 7008x4672).
            # Crop it before mapping camera AF coordinates onto the pixels.
            dw = image.width - self.image_width
            dh = image.height - self.image_height
            if 0 <= dw <= 128 and 0 <= dh <= 128:
                left, top = dw // 2, dh // 2
                image = image.crop((left, top, left + self.image_width,
                                    top + self.image_height))
            image = rotate_image(image, self.orientation)
            self.decoded.emit(self.request_id, to_qimage(image))
        except Exception as exc:
            self.failed.emit(self.request_id, str(exc))


class PhotoView(QGraphicsView):
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.scene_ = QGraphicsScene(self)
        self.setScene(self.scene_)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene_.addItem(self.pixmap_item)
        self.frame_item = QGraphicsRectItem()
        pen = QPen(QColor("#ff4050"), 2)
        pen.setCosmetic(True)
        self.frame_item.setPen(pen)
        self.frame_item.setBrush(Qt.BrushStyle.NoBrush)
        self.frame_item.setZValue(10)
        self.scene_.addItem(self.frame_item)
        self.frame_item.hide()
        self.focus_frame: FocusFrame | None = None
        self.show_focus = True
        self.fit_mode = True
        self.setBackgroundBrush(QColor("#181b1e"))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def set_image(self, image: QImage, focus: FocusFrame | None = None, fit: bool = True):
        self.pixmap_item.setPixmap(QPixmap.fromImage(image))
        self.focus_frame = focus
        self.scene_.setSceneRect(self.pixmap_item.boundingRect())
        self._update_frame()
        if fit or self.fit_mode:
            self.fit_image()

    def set_focus(self, focus: FocusFrame | None):
        self.focus_frame = focus
        self._update_frame()

    def _update_frame(self):
        frame = self.focus_frame
        image = self.pixmap_item.pixmap()
        if not (self.show_focus and frame and not image.isNull()):
            self.frame_item.hide()
            return
        sx = image.width() / frame.image_width
        sy = image.height() / frame.image_height
        self.frame_item.setRect((frame.x - frame.width / 2) * sx,
                                (frame.y - frame.height / 2) * sy,
                                frame.width * sx, frame.height * sy)
        self.frame_item.show()

    def fit_image(self):
        if self.pixmap_item.pixmap().isNull():
            return
        self.fit_mode = True
        self.fitInView(self.scene_.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def actual_size(self):
        self.fit_mode = False
        self.resetTransform()

    def wheelEvent(self, event):
        if self.pixmap_item.pixmap().isNull():
            return super().wheelEvent(event)
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        current = self.transform().m11()
        if 0.04 <= current * factor <= 16:
            self.fit_mode = False
            self.scale(factor, factor)
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit_mode:
            self.fit_image()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.file_dropped.emit(url.toLocalFile())
                event.acceptProposedAction()
                return
        super().dropEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, initial_path: str | None = None):
        super().__init__()
        self.setWindowTitle("索尼原始对焦框看图工具")
        self.resize(1320, 840)
        self.setAcceptDrops(True)
        self.view = PhotoView(self)
        self.view.file_dropped.connect(lambda path: self.open_path(Path(path)))
        self.setCentralWidget(self.view)
        self.files: list[Path] = []
        self.index = -1
        self.request_id = 0
        self.workers: list[RawDecodeThread] = []
        self.current_focus: FocusFrame | None = None
        self._build_toolbar()
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("打开一张照片或一个文件夹。滚轮缩放，拖动平移，左右方向键切换。")
        if initial_path:
            self.open_path(Path(initial_path))

    def _action(self, toolbar, label, callback, shortcut=None, checkable=False):
        action = QAction(label, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.setCheckable(checkable)
        action.triggered.connect(callback)
        toolbar.addAction(action)
        return action

    def _build_toolbar(self):
        bar = QToolBar("看图", self)
        bar.setMovable(False)
        self.addToolBar(bar)
        open_file = self._action(bar, "打开照片", self.choose_file, "Ctrl+O")
        open_folder = self._action(bar, "打开文件夹", self.choose_folder, "Ctrl+Shift+O")
        bar.addSeparator()
        self.prev_action = self._action(bar, "上一张", self.previous, "Left")
        self.next_action = self._action(bar, "下一张", self.next, "Right")
        bar.addSeparator()
        self.focus_action = self._action(bar, "原始对焦框", self.toggle_focus, "F", checkable=True)
        self.focus_action.setChecked(True)
        fit_action = self._action(bar, "适合窗口", self.view.fit_image, "Ctrl+0")
        actual_action = self._action(bar, "100%", self.view.actual_size, "Ctrl+1")
        bar.addSeparator()
        self.counter = QLabel("  未打开照片  ")
        bar.addWidget(self.counter)
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction(open_file)
        file_menu.addAction(open_folder)
        view_menu = self.menuBar().addMenu("查看")
        for action in (self.prev_action, self.next_action, self.focus_action, fit_action, actual_action):
            view_menu.addAction(action)
        self._update_navigation()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.open_path(Path(url.toLocalFile()))
                event.acceptProposedAction()
                return

    def _update_navigation(self):
        self.prev_action.setEnabled(self.index > 0)
        self.next_action.setEnabled(0 <= self.index < len(self.files) - 1)
        if self.index >= 0:
            self.counter.setText(f"  {self.index + 1} / {len(self.files)}  ")

    def choose_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "打开照片", "", FILE_FILTER)
        if filename:
            self.open_path(Path(filename))

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "打开文件夹")
        if folder:
            self.open_path(Path(folder))

    def open_path(self, path: Path):
        path = path.expanduser().resolve()
        if path.is_dir():
            self.files = sorted((p for p in path.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS), key=natural_key)
            self.index = 0 if self.files else -1
        elif path.is_file():
            self.files = sorted((p for p in path.parent.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS), key=natural_key)
            self.index = self.files.index(path) if path in self.files else -1
        else:
            QMessageBox.warning(self, "无法打开", f"找不到文件：{path}")
            return
        if self.index < 0:
            self.statusBar().showMessage("文件夹中没有受支持的照片。")
            self.view.set_image(QImage(), None)
            self._update_navigation()
            return
        self.load_current()

    def previous(self):
        if self.index > 0:
            self.index -= 1
            self.load_current()

    def next(self):
        if self.index < len(self.files) - 1:
            self.index += 1
            self.load_current()

    def toggle_focus(self, checked: bool):
        self.view.show_focus = checked
        self.view._update_frame()

    def load_current(self):
        self.request_id += 1
        request_id = self.request_id
        path = self.files[self.index]
        self._update_navigation()
        self.setWindowTitle(f"{path.name} — 索尼原始对焦框看图工具")
        self.current_focus = None
        try:
            if path.suffix.lower() == ".arw":
                info = read_arw(path)
                with Image.open(BytesIO(info.preview_jpeg)) as source:
                    preview = rotate_image(source.copy(), info.orientation)
                self.current_focus = orient_focus(info.focus, info.orientation) if info.focus else None
                self.view.set_image(to_qimage(preview), self.current_focus)
                if self.current_focus:
                    f = info.focus
                    self.statusBar().showMessage(f"{info.model} · 相机原始对焦框中心 ({f.x}, {f.y}) · 框 {f.width}×{f.height} · 正在解码完整 RAW…")
                else:
                    self.statusBar().showMessage(f"{info.model} · {info.focus_reason} · 正在解码完整 RAW…")
                worker = RawDecodeThread(request_id, path, info.orientation,
                                         info.image_width, info.image_height, self)
                worker.decoded.connect(self._raw_decoded)
                worker.failed.connect(self._raw_failed)
                worker.finished.connect(lambda w=worker: self.workers.remove(w) if w in self.workers else None)
                self.workers.append(worker)
                worker.start()
            else:
                with Image.open(path) as source:
                    image = ImageOps.exif_transpose(source).copy()
                self.view.set_image(to_qimage(image), None)
                self.statusBar().showMessage(f"{path.name} · {image.width}×{image.height} · 此版本只读取 ARW 中的原始对焦框")
        except Exception as exc:
            self.view.set_image(QImage(), None)
            self.statusBar().showMessage(f"无法打开 {path.name}：{exc}")

    def _raw_decoded(self, request_id: int, image: QImage):
        if request_id != self.request_id:
            return
        self.view.set_image(image, self.current_focus, fit=False)
        path = self.files[self.index]
        detail = "相机原始对焦框可切换" if self.current_focus else "无可用原始对焦框"
        self.statusBar().showMessage(f"{path.name} · 完整 RAW {image.width()}×{image.height()} · {detail}")

    def _raw_failed(self, request_id: int, error: str):
        if request_id == self.request_id:
            self.statusBar().showMessage(f"完整 RAW 解码失败；仍可查看相机预览。{error}")

    def closeEvent(self, event):
        for worker in self.workers:
            worker.wait()
        super().closeEvent(event)


class FocusApplication(QApplication):
    file_opened = Signal(str)

    def __init__(self, argv):
        super().__init__(argv)
        self.pending_file: str | None = None

    def event(self, event):
        if event.type() == QEvent.Type.FileOpen:
            self.pending_file = event.file()
            self.file_opened.emit(self.pending_file)
            return True
        return super().event(event)


def main():
    app = FocusApplication(sys.argv)
    app.setApplicationName("索尼原始对焦框看图工具")
    initial = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-psn_") else None
    window = MainWindow(initial)
    app.file_opened.connect(lambda path: window.open_path(Path(path)))
    if app.pending_file and not initial:
        window.open_path(Path(app.pending_file))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
