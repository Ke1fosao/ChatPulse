from __future__ import annotations

import base64
import hashlib
import io
import json
import tarfile
from pathlib import Path

# One-shot verified transport. The script deletes itself before committing the implementation.
CHUNKS = [Path(f"tools/production-package.part{index:03d}") for index in range(31)]
ARCHIVE_SHA256 = "a3ecfc37ac9e1b152584a442e85f4dd5edd3ab1771a03f224bfd9ad6e3707b7f"
FINAL_CHUNK_SIZE = 1296


def validate_member(member: tarfile.TarInfo) -> None:
    path = Path(member.name)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Unsafe archive path: {member.name}")
    if member.issym() or member.islnk() or member.isdev():
        raise RuntimeError(f"Unsupported archive member: {member.name}")


def main() -> None:
    print("phase=verify_chunks", flush=True)
    encoded_parts: list[bytes] = []
    invalid: list[str] = []
    for index, path in enumerate(CHUNKS):
        data = path.read_bytes()
        expected_size = FINAL_CHUNK_SIZE if index == 30 else 2500
        print(f"chunk={path.name} bytes={len(data)}", flush=True)
        if len(data) != expected_size:
            invalid.append(f"{path}: expected {expected_size}, got {len(data)}")
        encoded_parts.append(data)
    if invalid:
        raise RuntimeError("Invalid chunk sizes: " + "; ".join(invalid))

    print("phase=decode_archive", flush=True)
    archive = base64.b64decode(b"".join(encoded_parts), validate=True)
    digest = hashlib.sha256(archive).hexdigest()
    print(f"archive_bytes={len(archive)} sha256={digest}", flush=True)
    if digest != ARCHIVE_SHA256:
        raise RuntimeError(f"Invalid package digest: expected {ARCHIVE_SHA256}, got {digest}")

    print("phase=extract_archive", flush=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        members = package.getmembers()
        for member in members:
            validate_member(member)
        print(f"archive_members={len(members)}", flush=True)
        package.extractall(".", members=members)

    print("phase=apply_manifest", flush=True)
    manifest_path = Path(".production-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for raw_path in manifest["delete"]:
        path = Path(raw_path)
        if path.exists():
            path.unlink()
            print(f"deleted={path}", flush=True)
    manifest_path.unlink()

    print("phase=cleanup_transport", flush=True)
    for path in CHUNKS:
        path.unlink(missing_ok=True)
    Path(".github/workflows/apply-production.yml").unlink(missing_ok=True)
    Path(__file__).unlink(missing_ok=True)
    print("production_package_applied=true", flush=True)


if __name__ == "__main__":
    main()
