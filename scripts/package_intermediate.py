"""Package the derived SQLite database into checksum-verified gzip parts.

This does not include the original automotive JSON or archives. Parts are
intended for GitHub Release assets rather than Git objects.
"""
import gzip
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/automotive_us_2019.sqlite"
OUTPUT = ROOT / "outputs/transfer"
MANIFEST = ROOT / "data/processed/intermediate_transfer.json"
PART_BYTES = 1024**3


class SplitWriter:
    def __init__(self):
        self.stream = None
        self.parts = []
        self.part_size = 0
        self.digest = None

    def close_part(self):
        if self.stream is not None:
            self.stream.close()
            self.parts[-1].update(bytes=self.part_size, sha256=self.digest.hexdigest())
            self.stream = None

    def write(self, data):
        original_size = len(data)
        view = memoryview(data)
        while view:
            if self.stream is None:
                name = f"automotive_us_2019.sqlite.gz.part{len(self.parts)+1:03d}"
                path = OUTPUT / name
                self.stream = path.open("xb")
                self.parts.append({"name": name})
                self.part_size = 0
                self.digest = hashlib.sha256()
            length = min(len(view), PART_BYTES-self.part_size)
            self.stream.write(view[:length])
            self.digest.update(view[:length])
            self.part_size += length
            view = view[length:]
            if self.part_size == PART_BYTES:
                self.close_part()
        return original_size

    def flush(self):
        if self.stream:
            self.stream.flush()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if MANIFEST.exists():
        raise FileExistsError("A transfer manifest already exists; retain or explicitly manage it before rebuilding.")
    writer = SplitWriter()
    digest = hashlib.sha256()
    total = SOURCE.stat().st_size
    read = 0
    start = last = time.monotonic()
    with SOURCE.open("rb") as source, gzip.GzipFile(fileobj=writer, mode="wb", compresslevel=1, mtime=0, filename="") as compressed:
        while True:
            block = source.read(16*1024*1024)
            if not block:
                break
            digest.update(block)
            compressed.write(block)
            read += len(block)
            now = time.monotonic()
            if now-last >= 20:
                print(f"Packaging {read/total:.0%}: {read/1024**3:.2f}/{total/1024**3:.2f} GiB", flush=True)
                last = now
    writer.close_part()
    metadata = {
        "repository": "joseph-xuan/si618-fall2026-project-team8",
        "release_tag": "data-transfer-2026-10-14",
        "format": "concatenated gzip stream split into ordered parts",
        "target_path": "data/processed/automotive_us_2019.sqlite",
        "uncompressed_bytes": total, "uncompressed_sha256": digest.hexdigest(),
        "parts": writer.parts,
    }
    MANIFEST.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Packaged into {len(writer.parts)} part(s), {sum(p['bytes'] for p in writer.parts)/1024**3:.2f} GiB", flush=True)


if __name__ == "__main__":
    main()
