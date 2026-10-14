"""Download repository release parts and restore the derived SQLite database.

The 500,000-row sample and IPEDS files are included in Git; restoring this large
database is optional for notebook work and needed only to regenerate samples.
If the repository is private, set GITHUB_TOKEN in the environment for downloads.
"""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class PartReader(io.RawIOBase):
    def __init__(self, paths):
        self.paths = iter(paths)
        self.stream = None

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.stream is None:
                path = next(self.paths, None)
                if path is None:
                    return 0
                self.stream = path.open("rb")
            count = self.stream.readinto(buffer)
            if count:
                return count
            self.stream.close()
            self.stream = None

    def close(self):
        if self.stream:
            self.stream.close()
        super().close()


def main():
    manifest = json.loads((ROOT / "data/processed/intermediate_transfer.json").read_text(encoding="utf-8"))
    destination = ROOT / manifest["target_path"]
    if destination.exists():
        raise FileExistsError(f"Destination already exists; retained: {destination}")
    partial = destination.with_suffix(".sqlite.partial")
    if partial.exists():
        raise FileExistsError(f"Partial output already exists; retained: {partial}")
    folder = ROOT / "outputs/transfer"
    folder.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "si618-data-restore"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    if shutil.disk_usage(ROOT).free < manifest["uncompressed_bytes"] + sum(p["bytes"] for p in manifest["parts"]) + 1024**3:
        raise RuntimeError("Not enough free space for the compressed parts and restored database.")
    paths = []
    for part in manifest["parts"]:
        path = folder / part["name"]
        if not path.exists():
            url = part.get("url") or f"https://github.com/{manifest['repository']}/releases/download/{manifest['release_tag']}/{part['name']}"
            request_headers = dict(headers)
            if token and part.get("asset_api_url"):
                url = part["asset_api_url"]
                request_headers["Accept"] = "application/octet-stream"
            temp = path.with_name(path.name + ".partial")
            with urllib.request.urlopen(urllib.request.Request(url, headers=request_headers), timeout=120) as response, temp.open("wb") as output:
                shutil.copyfileobj(response, output, 16*1024*1024)
            temp.rename(path)
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(16*1024*1024), b""):
                digest.update(block)
        if path.stat().st_size != part["bytes"] or digest.hexdigest() != part["sha256"]:
            raise RuntimeError(f"Part checksum mismatch: {path.name}")
        paths.append(path)
        print(f"Verified {path.name}", flush=True)
    digest = hashlib.sha256()
    with io.BufferedReader(PartReader(paths)) as parts, gzip.GzipFile(fileobj=parts, mode="rb") as source, partial.open("wb") as output:
        while True:
            block = source.read(16*1024*1024)
            if not block:
                break
            output.write(block)
            digest.update(block)
    if partial.stat().st_size != manifest["uncompressed_bytes"] or digest.hexdigest() != manifest["uncompressed_sha256"]:
        raise RuntimeError("Restored database checksum mismatch; partial file retained.")
    partial.rename(destination)
    print(f"Restored and verified {destination}", flush=True)


if __name__ == "__main__":
    main()
