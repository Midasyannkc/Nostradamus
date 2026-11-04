"""Replace the template's en dash bullet characters with a hyphen so the file holds no en or em dashes."""
import shutil
import sys
import zipfile

src = sys.argv[1]
tmp = src + ".tmp"
with zipfile.ZipFile(src) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
    for item in zi.infolist():
        data = zi.read(item.filename)
        if item.filename.endswith(".xml"):
            data = data.decode("utf8").replace("–", "-").replace("—", "-").encode("utf8")
        zo.writestr(item, data)
shutil.move(tmp, src)
