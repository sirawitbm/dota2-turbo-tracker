"""Render the app icon (the same one drawn in ui.app_icon) to
assets/TurboTracker.ico. Needs PySide6 and Pillow; run once, commit the .ico.

Run:  python tools/make_icon.py
"""

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402
from PySide6.QtCore import QBuffer, QIODevice  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import ui  # noqa: E402


def main():
    QApplication(sys.argv)
    pix = ui.app_icon().pixmap(256, 256)
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    pix.save(buf, "PNG")
    image = Image.open(io.BytesIO(bytes(buf.data())))
    out = ROOT / "assets" / "TurboTracker.ico"
    out.parent.mkdir(exist_ok=True)
    image.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                           (64, 64), (128, 128), (256, 256)])
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
