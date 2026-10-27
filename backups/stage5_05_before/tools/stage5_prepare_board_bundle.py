#!/usr/bin/env python3
"""Create a source-only board-review archive locally. Does not invoke SSH/SCP."""

import hashlib
import argparse
import io
import json
from pathlib import Path
import tarfile


def package_files(root):
    selected = [Path("CMakeLists.txt"), Path("README_STAGE5.txt")]
    for folder in ("src", "include", "tests"):
        selected.extend(p.relative_to(root) for p in (root / folder).rglob("*")
                        if p.is_file() and p.suffix in {".cpp", ".h", ".hpp", ".cmake", ".txt"})
    selected.extend(p.relative_to(root) for p in (root / "tools").glob("stage5_board_*.*")
                    if p.suffix in {".sh", ".py"})
    selected.append(Path("docs/stage5_01_board_review.md"))
    if (root / "docs/stage5_01_readonly_preflight.md").is_file():
        selected.append(Path("docs/stage5_01_readonly_preflight.md"))
    return sorted(set(selected))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-name", default="stage5_01_review.tgz")
    args = parser.parse_args()
    if Path(args.archive_name).name != args.archive_name or not args.archive_name.endswith(".tgz"):
        parser.error("Use a simple .tgz basename")
    root = Path(__file__).resolve().parents[1]
    destination = root / "reports/stage5_01_local/board_package"
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / args.archive_name
    if archive.exists():
        raise SystemExit("Archive already exists; retain it and choose a fresh version before repackaging")
    manifest = []
    for relative in package_files(root):
        path = root / relative
        if path.is_symlink() or not path.is_file() or ".." in relative.parts or relative.is_absolute():
            raise SystemExit("Unsafe or missing package member: " + str(relative))
        data = path.read_bytes()
        manifest.append({"file": relative.as_posix(), "size": len(data),
                         "sha256": hashlib.sha256(data).hexdigest()})
    checksums = "".join(f"{row['sha256']}  {row['file']}\n" for row in manifest).encode("utf-8")
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as output:
        for row in manifest:
            data = (root / row["file"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise SystemExit("Source changed while packaging: " + row["file"])
            entry = tarfile.TarInfo(row["file"])
            entry.size = len(data)
            entry.mode = 0o644
            output.addfile(entry, io.BytesIO(data))
        entry = tarfile.TarInfo("SOURCE_SHA256SUMS")
        entry.size = len(checksums)
        entry.mode = 0o644
        output.addfile(entry, io.BytesIO(checksums))
    result = {"status": "PREPARED_LOCALLY_NOT_DEPLOYED", "archive": archive.name,
              "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
              "destination": "/home/cat/projects/RK3576/rk3576_multimodal_stage5_review",
              "excluded": ["models", "SDK", "runtime libraries", "build products", "backups", ".git"],
              "files": manifest}
    current = destination / "bundle_manifest.json"
    if current.is_file():
        previous = json.loads(current.read_text(encoding="utf-8"))
        frozen = destination / (previous["archive"] + ".manifest.json")
        if not frozen.exists():
            frozen.write_bytes(current.read_bytes())
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    current.write_text(rendered, encoding="utf-8")
    (destination / (archive.name + ".manifest.json")).write_text(rendered, encoding="utf-8")
    (destination / (archive.name + ".sha256")).write_text(
        result["archive_sha256"] + "  " + archive.name + "\n", encoding="ascii")
    print(f"Prepared {len(manifest)} source/document/script files. No remote action performed.")
    print("SHA256 " + result["archive_sha256"])


if __name__ == "__main__":
    main()
