"""Register supported photo types with Finder's Open With menu."""

from pathlib import Path
import plistlib
import sys


bundle = Path(sys.argv[1])
plist = bundle / "Contents" / "Info.plist"
with plist.open("rb") as stream:
    info = plistlib.load(stream)

info["CFBundleName"] = "Sony Focus Viewer"
info["CFBundleDisplayName"] = "索尼原始对焦框看图工具"
info["CFBundleIdentifier"] = "com.liu223344.focusviewer"
info["CFBundleDocumentTypes"] = [
    {
        "CFBundleTypeName": "Sony ARW raw photo",
        "CFBundleTypeRole": "Viewer",
        "LSHandlerRank": "Alternate",
        "LSItemContentTypes": ["com.sony.arw-raw-image"],
        "CFBundleTypeExtensions": ["arw"],
    },
    {
        "CFBundleTypeName": "Photo",
        "CFBundleTypeRole": "Viewer",
        "LSHandlerRank": "Alternate",
        "LSItemContentTypes": [
            "public.jpeg", "public.png", "public.tiff", "public.heic",
            "com.compuserve.gif", "org.webmproject.webp", "com.microsoft.bmp",
        ],
        "CFBundleTypeExtensions": [
            "jpg", "jpeg", "png", "tif", "tiff", "heic", "heif",
            "gif", "webp", "bmp",
        ],
    },
]
with plist.open("wb") as stream:
    plistlib.dump(info, stream)
