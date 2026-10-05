"""Read camera-recorded AF geometry from an untouched Sony ARW file.

This module deliberately does not infer focus from image pixels. Unknown or
malformed MakerNote layouts return no focus frame.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct


@dataclass(frozen=True)
class FocusFrame:
    image_width: int
    image_height: int
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class RawInfo:
    model: str
    orientation: int
    image_width: int
    image_height: int
    preview_jpeg: bytes
    focus: FocusFrame | None
    focus_reason: str


class TiffReader:
    TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}

    def __init__(self, data: bytes):
        self.data = data
        if len(data) < 8 or data[:2] != b"II" or self.u16(2) != 42:
            raise ValueError("不是受支持的 Sony ARW/TIFF 文件")

    def bounds(self, offset: int, size: int) -> None:
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise ValueError("元数据超出文件范围")

    def u16(self, offset: int) -> int:
        self.bounds(offset, 2)
        return struct.unpack_from("<H", self.data, offset)[0]

    def u32(self, offset: int) -> int:
        self.bounds(offset, 4)
        return struct.unpack_from("<I", self.data, offset)[0]

    def ifd(self, offset: int) -> dict[int, tuple[int, int, int, int]]:
        count = self.u16(offset)
        if count > 4096:
            raise ValueError("元数据目录无效")
        self.bounds(offset + 2, count * 12)
        entries = {}
        for i in range(count):
            entry_offset = offset + 2 + i * 12
            tag, typ, amount, value = struct.unpack_from("<HHII", self.data, entry_offset)
            entries[tag] = (typ, amount, value, entry_offset + 8)
        return entries

    def location(self, entry: tuple[int, int, int, int]) -> tuple[int, int]:
        typ, amount, value, inline = entry
        size = self.TYPE_SIZES.get(typ, 1) * amount
        offset = inline if size <= 4 else value
        self.bounds(offset, size)
        return offset, size

    def number(self, entry: tuple[int, int, int, int], index: int = 0) -> int:
        typ, amount, _, _ = entry
        if index >= amount:
            raise ValueError("元数据字段长度不足")
        offset, _ = self.location(entry)
        if typ == 3:
            return self.u16(offset + index * 2)
        if typ == 4:
            return self.u32(offset + index * 4)
        if typ in (1, 7):
            return self.data[offset + index]
        raise ValueError("元数据字段类型不受支持")

    def text(self, entry: tuple[int, int, int, int] | None) -> str:
        if entry is None:
            return ""
        offset, size = self.location(entry)
        return self.data[offset:offset + size].split(b"\0", 1)[0].decode("ascii", "replace").strip()


def read_arw(path: str | Path) -> RawInfo:
    t = TiffReader(Path(path).read_bytes())
    root = t.ifd(t.u32(4))
    if t.text(root.get(0x010F)) != "SONY":
        raise ValueError("不是索尼相机文件")
    model = t.text(root.get(0x0110))
    orientation = t.number(root[0x0112]) if 0x0112 in root else 1
    preview_offset = t.number(root[0x0201])
    preview_size = t.number(root[0x0202])
    t.bounds(preview_offset, preview_size)
    preview = t.data[preview_offset:preview_offset + preview_size]
    if preview_size < 100 or preview[:2] != b"\xff\xd8":
        raise ValueError("ARW 中没有可用的内嵌 JPEG 预览")

    exif = t.ifd(t.number(root[0x8769]))
    image_width = t.number(exif[0xA002])
    image_height = t.number(exif[0xA003])
    focus = None
    reason = "文件中没有可用的原始对焦框记录"
    try:
        maker_offset, _ = t.location(exif[0x927C])
        maker = t.ifd(maker_offset)
        location = maker[0x2027]  # Sony FocusLocation: image W,H, center X,Y
        frame_size = maker[0x2037]  # Sony FocusFrameSize: two uint16 values, then flags
        if location[0] == 3 and location[1] >= 4 and frame_size[1] >= 4:
            w, h, x, y = (t.number(location, i) for i in range(4))
            size_offset, _ = t.location(frame_size)
            fw, fh = t.u16(size_offset), t.u16(size_offset + 2)
            if 0 < w <= 20000 and 0 < h <= 20000 and 0 <= x <= w and 0 <= y <= h and 0 < fw <= w and 0 < fh <= h:
                focus = FocusFrame(w, h, x, y, fw, fh)
                reason = ""
    except (KeyError, ValueError, struct.error):
        pass

    if orientation not in (1, 3, 6, 8):
        focus = None
        reason = "这个旋转方向尚未校准，已隐藏对焦框"
    return RawInfo(model, orientation, image_width, image_height, preview, focus, reason)


def orient_focus(frame: FocusFrame, orientation: int) -> FocusFrame:
    w, h, x, y, fw, fh = (
        frame.image_width, frame.image_height, frame.x, frame.y,
        frame.width, frame.height,
    )
    if orientation == 1:
        return frame
    if orientation == 3:
        return FocusFrame(w, h, w - x, h - y, fw, fh)
    if orientation == 6:  # clockwise
        return FocusFrame(h, w, h - y, x, fh, fw)
    if orientation == 8:  # counterclockwise
        return FocusFrame(h, w, y, w - x, fh, fw)
    raise ValueError("旋转方向不受支持")
