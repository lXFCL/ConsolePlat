from datetime import datetime
from pathlib import Path

from consoleplat.services.print_gallery_service import collect_print_gallery, pull_random_github_print


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


def test_pull_random_github_print_accepts_repo_url_and_saves_bo_by_date(tmp_path):
    calls = []

    def fetch_json(url):
        calls.append(url)
        if url == "https://api.github.com/repos/demo/gallery":
            return {"default_branch": "main"}
        if url == "https://api.github.com/repos/demo/gallery/contents/prints?ref=main":
            return [
                {
                    "type": "file",
                    "name": "BO-1616.png",
                    "download_url": "https://raw.githubusercontent.com/demo/gallery/main/prints/BO-1616.png",
                },
                {"type": "file", "name": "notes.txt", "download_url": "https://example.invalid/notes.txt"},
            ]
        raise AssertionError(url)

    def downloader(url, dest):
        Path(dest).write_bytes(b"downloaded")
        return True

    result = pull_random_github_print(
        github_url="https://github.com/demo/gallery",
        local_gallery_dir=tmp_path / "gallery",
        fetch_json=fetch_json,
        downloader=downloader,
        chooser=lambda items: items[0],
        now=lambda: datetime(2026, 6, 27, 10, 0, 0),
    )

    expected = tmp_path / "gallery" / "github拉取" / "BO" / "2026" / "6月" / "最终透明底" / "BO-1616.png"
    assert result.ok is True
    assert result.saved_path == str(expected)
    assert expected.read_bytes() == b"downloaded"
    assert calls == [
        "https://api.github.com/repos/demo/gallery",
        "https://api.github.com/repos/demo/gallery/contents/prints?ref=main",
    ]


def test_pull_random_github_print_accepts_raw_url_and_saves_unknown_as_common(tmp_path):
    def fetch_json(url):
        assert url == "https://api.github.com/repos/demo/gallery/contents/prints?ref=main"
        return [
            {
                "type": "file",
                "name": "dog_text_01.png",
                "download_url": "https://raw.githubusercontent.com/demo/gallery/main/prints/dog_text_01.png",
            }
        ]

    def downloader(_url, dest):
        Path(dest).write_bytes(b"common")
        return True

    result = pull_random_github_print(
        github_url="https://raw.githubusercontent.com/demo/gallery/main/prints/",
        local_gallery_dir=tmp_path / "gallery",
        fetch_json=fetch_json,
        downloader=downloader,
        now=lambda: datetime(2026, 6, 27, 10, 0, 0),
    )

    expected = tmp_path / "gallery" / "github拉取" / "通用素材" / "2026" / "6月" / "最终透明底" / "dog_text_01.png"
    assert result.ok is True
    assert result.saved_path == str(expected)
    assert expected.read_bytes() == b"common"


def test_pull_random_github_print_removes_empty_file_after_download_failure(tmp_path):
    def fetch_json(_url):
        return [
            {
                "type": "file",
                "name": "SZW-3163.png",
                "download_url": "https://raw.githubusercontent.com/demo/gallery/main/prints/SZW-3163.png",
            }
        ]

    def downloader(_url, dest):
        Path(dest).write_bytes(b"")
        return False

    result = pull_random_github_print(
        github_url="https://raw.githubusercontent.com/demo/gallery/main/prints/",
        local_gallery_dir=tmp_path / "gallery",
        fetch_json=fetch_json,
        downloader=downloader,
        now=lambda: datetime(2026, 6, 27, 10, 0, 0),
    )

    expected = tmp_path / "gallery" / "github拉取" / "SZW" / "2026" / "6月" / "最终透明底" / "SZW-3163.png"
    assert result.ok is False
    assert not expected.exists()
