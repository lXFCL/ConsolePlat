from pathlib import Path

from consoleplat.services.print_gallery_service import collect_print_gallery


def test_print_gallery_copies_exact_local_sku_match(tmp_path):
    local_dir = tmp_path / "local"
    target_dir = tmp_path / "batch" / "印花图集"
    local_dir.mkdir()
    (local_dir / "BO-1616.png").write_bytes(b"real")
    (local_dir / "demo_BO-1616.png").write_bytes(b"wrong")

    result = collect_print_gallery(
        skus=["BO-1616"],
        source="local",
        local_dir=local_dir,
        github_raw_base_url="",
        target_dir=target_dir,
    )

    assert result.copied == 1
    assert result.missing_skus == []
    assert (target_dir / "BO-1616.png").read_bytes() == b"real"
    assert not (target_dir / "demo_BO-1616.png").exists()


def test_print_gallery_downloads_from_github_and_caches_locally(tmp_path):
    local_dir = tmp_path / "local"
    target_dir = tmp_path / "batch" / "印花图集"
    calls = []

    def downloader(url, dest):
        calls.append((url, Path(dest).name))
        if url.endswith("/BO-1616.png"):
            Path(dest).write_bytes(b"downloaded")
            return True
        return False

    result = collect_print_gallery(
        skus=["BO-1616"],
        source="github",
        local_dir=local_dir,
        github_raw_base_url="https://raw.githubusercontent.com/demo/gallery/main",
        target_dir=target_dir,
        downloader=downloader,
    )

    assert result.copied == 1
    assert result.missing_skus == []
    assert calls[0][0] == "https://raw.githubusercontent.com/demo/gallery/main/BO-1616.png"
    assert (local_dir / "BO-1616.png").read_bytes() == b"downloaded"
    assert (target_dir / "BO-1616.png").read_bytes() == b"downloaded"


def test_print_gallery_records_missing_without_failing(tmp_path):
    result = collect_print_gallery(
        skus=["BO-9999"],
        source="github",
        local_dir=tmp_path / "local",
        github_raw_base_url="https://raw.githubusercontent.com/demo/gallery/main",
        target_dir=tmp_path / "target",
        downloader=lambda _url, _dest: False,
    )

    assert result.copied == 0
    assert result.missing_skus == ["BO-9999"]


def test_print_gallery_uses_newest_duplicate_and_warns(tmp_path):
    local_dir = tmp_path / "local"
    nested = local_dir / "nested"
    nested.mkdir(parents=True)
    old = local_dir / "BO-1616.png"
    new = nested / "BO-1616.webp"
    old.write_bytes(b"old")
    new.write_bytes(b"new")
    old_mtime = 1000
    new_mtime = 2000
    old.touch()
    new.touch()
    import os

    os.utime(old, (old_mtime, old_mtime))
    os.utime(new, (new_mtime, new_mtime))

    result = collect_print_gallery(
        skus=["BO-1616"],
        source="local",
        local_dir=local_dir,
        github_raw_base_url="",
        target_dir=tmp_path / "target",
    )

    assert result.copied == 1
    assert result.warnings
    assert (tmp_path / "target" / "BO-1616.webp").read_bytes() == b"new"
