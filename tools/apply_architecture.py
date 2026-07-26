from __future__ import annotations

import base64
import hashlib
import io
import json
import tarfile
from pathlib import Path

CHUNKS = [
    (10_000, "tools/architecture-batch.part00"),
    (10_000, "tools/architecture-batch.part01"),
    (10_000, "tools/architecture-batch.part02"),
    (2_500, "tools/architecture-batch.part03a"),
    (2_500, "tools/architecture-batch.part03b"),
    (2_500, "tools/architecture-batch.part03c"),
    (2_500, "tools/architecture-batch.part03d"),
    (10_000, "tools/architecture-batch.part04"),
    (2_500, "tools/architecture-batch.part05a"),
    (2_500, "tools/architecture-batch.part05b"),
    (2_500, "tools/architecture-batch.part05c"),
    (2_500, "tools/architecture-batch.part05d"),
    (10_000, "tools/architecture-batch.part06"),
    (7_404, "tools/architecture-batch.part07"),
]
ARCHIVE_SHA256 = "4af8ec7883c8e2dda60b549f4415464ae70c69f2705cdf9d4e2f25b6ee48e0b5"


def validate_member(member: tarfile.TarInfo) -> None:
    path = Path(member.name)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Unsafe archive path: {member.name}")
    if member.issym() or member.islnk():
        raise RuntimeError(f"Archive links are not allowed: {member.name}")


def main() -> None:
    print("phase=verify_chunks")
    encoded_parts: list[bytes] = []
    for expected_size, raw_path in CHUNKS:
        path = Path(raw_path)
        data = path.read_bytes()
        print(f"chunk={path.name} bytes={len(data)}")
        if len(data) != expected_size:
            raise RuntimeError(
                f"Invalid chunk size for {raw_path}: expected {expected_size}, got {len(data)}"
            )
        encoded_parts.append(data)

    print("phase=decode_base64")
    encoded = b"".join(encoded_parts)
    archive = base64.b64decode(encoded, validate=True)
    actual_archive_sha = hashlib.sha256(archive).hexdigest()
    print(f"encoded_bytes={len(encoded)} archive_bytes={len(archive)} archive_sha256={actual_archive_sha}")
    if actual_archive_sha != ARCHIVE_SHA256:
        raise RuntimeError(
            f"Invalid archive: expected {ARCHIVE_SHA256}, got {actual_archive_sha}"
        )

    print("phase=extract_archive")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        members = package.getmembers()
        for member in members:
            validate_member(member)
        print(f"archive_members={len(members)}")
        package.extractall(".", members=members)

    print("phase=apply_manifest")
    manifest_path = Path(".architecture-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for raw_path in manifest["delete"]:
        path = Path(raw_path)
        if path.exists():
            path.unlink()
            print(f"deleted={path}")
    manifest_path.unlink()

    print("phase=cleanup_transport")
    for path in Path("tools").glob("architecture-batch.part*"):
        path.unlink()
    Path(__file__).unlink()
    print("architecture_package_applied=true")


if __name__ == "__main__":
    main()
