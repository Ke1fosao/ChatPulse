from __future__ import annotations

import base64
import hashlib
import io
import json
import tarfile
from pathlib import Path

CHUNKS = [
    ("3e00028547cdbb5ef4613e9ce7b3478f1d7c1be6", "tools/architecture-batch.part00"),
    ("27e7d18c577d989406b9660361ae88db0261f9d1", "tools/architecture-batch.part01"),
    ("7d933dd735c5f4219402806cf5f27575b761f534", "tools/architecture-batch.part02"),
    ("3d54a6f9e5e555f607dd36225209b7f33855b58b", "tools/architecture-batch.part03a"),
    ("de812842f9627fb8c5d309dab9372be54cb1d1b4", "tools/architecture-batch.part03b"),
    ("598de1bec7e6cf85acddf58c676184c7f28713e4", "tools/architecture-batch.part03c"),
    ("014f35003b39c123310a6c2058bafae0b4726d28", "tools/architecture-batch.part03d"),
    ("993f553cadcdc7157ad36c9ba0919186f2984358", "tools/architecture-batch.part04"),
    ("3b4988cc2fc3c9d85e7ca1793de83feffba42db5", "tools/architecture-batch.part05a"),
    ("83311b9300e6a2f41011c87ee6386f5afcfff6dd", "tools/architecture-batch.part05b"),
    ("8287f0ec7edb9f8fb1dd9b183599f504802ff1b0", "tools/architecture-batch.part05c"),
    ("6a421eab5246bc7bc7d06eca6e01d68dc6672322", "tools/architecture-batch.part05d"),
    ("ba08ce5765da8ac3138597de75a7484ef532131f", "tools/architecture-batch.part06"),
    ("6c51c221e77d45cc5724d018418774018d5eccfa", "tools/architecture-batch.part07"),
]
ARCHIVE_SHA256 = "4af8ec7883c8e2dda60b549f4415464ae70c69f2705cdf9d4e2f25b6ee48e0b5"


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def validate_member(member: tarfile.TarInfo) -> None:
    path = Path(member.name)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Unsafe archive path: {member.name}")
    if member.issym() or member.islnk():
        raise RuntimeError(f"Archive links are not allowed: {member.name}")


def main() -> None:
    print("phase=verify_chunks")
    encoded_parts: list[bytes] = []
    for expected, raw_path in CHUNKS:
        path = Path(raw_path)
        data = path.read_bytes()
        actual = git_blob_sha(data)
        print(f"chunk={path.name} bytes={len(data)} sha={actual}")
        if actual != expected:
            raise RuntimeError(f"Invalid chunk {raw_path}: expected {expected}, got {actual}")
        encoded_parts.append(data)

    print("phase=decode_base64")
    encoded = b"".join(encoded_parts)
    archive = base64.b64decode(encoded, validate=True)
    actual_archive_sha = hashlib.sha256(archive).hexdigest()
    print(f"archive_bytes={len(archive)} archive_sha256={actual_archive_sha}")
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
