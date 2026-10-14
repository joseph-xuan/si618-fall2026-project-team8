"""Upload prepared database parts to a draft release using Git credentials.

Credentials stay in process memory and are not printed or written to disk.
Run with --publish after the repository commit has been pushed to publish it.
"""
import argparse
import json
from pathlib import Path
import subprocess
import requests

ROOT = Path(__file__).resolve().parents[1]


def main(publish):
    manifest_path = ROOT / "data/processed/intermediate_transfer.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    credential_result = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True, check=True)
    credential = dict(line.split("=",1) for line in credential_result.stdout.splitlines() if "=" in line)
    session = requests.Session()
    session.headers.update({"Authorization": "Bearer " + credential["password"], "Accept": "application/vnd.github+json", "User-Agent": "si618-data-transfer"})
    base = "https://api.github.com/repos/" + manifest["repository"]
    releases = session.get(base + "/releases", timeout=30)
    releases.raise_for_status()
    release = next((r for r in releases.json() if r["tag_name"] == manifest["release_tag"]), None)
    if release is None:
        response = session.post(base + "/releases", json={
            "tag_name": manifest["release_tag"], "target_commitish": "main",
            "name": "Processed automotive intermediate — October 14, 2026",
            "body": "Derived SQLite intermediate for regenerating samples on another computer. Original automotive JSON and archives are excluded. Clone the repository and run python scripts/restore_intermediate.py to download, reconstruct, and SHA256-verify the database. The 500,000-row Parquet sample and IPEDS 2019 files are included directly in the repository.",
            "draft": True, "prerelease": False,
        }, timeout=30)
        response.raise_for_status()
        release = response.json()
    assets = {asset["name"]: asset for asset in release["assets"]}
    for part in manifest["parts"]:
        if part["name"] in assets:
            asset = assets[part["name"]]
            if asset["size"] != part["bytes"]:
                raise RuntimeError("Existing release asset has an unexpected size; retained without replacement.")
        else:
            path = ROOT / "outputs/transfer" / part["name"]
            print(f"Uploading {part['name']}: {part['bytes']:,} bytes", flush=True)
            with path.open("rb") as data:
                response = session.post(release["upload_url"].split("{")[0], params={"name": part["name"]}, data=data,
                                        headers={"Content-Type": "application/octet-stream"}, timeout=(30,900))
            response.raise_for_status()
            asset = response.json()
        if asset["size"] != part["bytes"]:
            raise RuntimeError("Release asset size mismatch")
        remote_digest = asset.get("digest")
        if remote_digest and remote_digest != "sha256:" + part["sha256"]:
            raise RuntimeError("Release asset checksum mismatch")
        part["url"] = asset["browser_download_url"]
        part["asset_api_url"] = asset["url"]
        print(f"Verified uploaded asset: {part['name']}", flush=True)
    manifest["release_url"] = release["html_url"]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if publish:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        response = session.patch(release["url"], json={"draft": False, "target_commitish": head}, timeout=30)
        response.raise_for_status()
        published = response.json()
        manifest["release_url"] = published["html_url"]
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print("Published:", published["html_url"], flush=True)
    else:
        print("All assets uploaded to draft release; publish after pushing the repository.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true")
    main(parser.parse_args().publish)
