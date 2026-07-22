from pathlib import Path

import pytest

from consoleplat.services.ai_selection_service import (
    SelectionCandidate,
    create_batch,
    download_candidate_images,
    export_batch,
    load_batches,
    parse_sales_count,
    rank_candidates,
)


def make_candidate(index: int, sales_count: int | None = None) -> SelectionCandidate:
    count = index if sales_count is None else sales_count
    return SelectionCandidate(
        title=f"商品 {index}",
        sales_text=f"已售 {count}",
        sales_count=count,
        price="$9.99",
        product_url=f"https://www.temu.com/goods-{index}.html?refer_page_name=search",
        image_url="",
        keyword="黑白T恤",
    )


def test_parse_sales_count_supports_k_wan_and_plain_counts():
    assert parse_sales_count("1.2K sold") == 1200
    assert parse_sales_count("已售 3.4万") == 34000
    assert parse_sales_count("销量 98") == 98
    assert parse_sales_count("无销量") is None


def test_rank_candidates_deduplicates_canonical_links_and_keeps_top_30():
    candidates = [make_candidate(index) for index in range(35)]
    candidates.append(
        SelectionCandidate(
            title="重复商品",
            sales_text="已售 999",
            sales_count=999,
            price="$8.99",
            product_url="https://www.temu.com/goods-34.html",
            image_url="",
            keyword="黑白T恤",
        )
    )

    ranked = rank_candidates(candidates, limit=30)

    assert len(ranked) == 30
    assert ranked[0].sales_count == 999
    assert ranked[0].rank == 1
    assert ranked[-1].rank == 30


def test_create_batch_requires_configured_program_data_dir():
    with pytest.raises(ValueError, match="程序数据目录"):
        create_batch("", ["黑白T恤"])


def test_export_batch_writes_history_under_program_data_dir(tmp_path):
    batch = create_batch(tmp_path, ["黑白T恤"], created_at="2026-07-22T15:30:00")
    candidate = make_candidate(99)

    result = export_batch(batch, [candidate], failures=["商品 B 未读取到销量"])

    assert result.csv_path.exists()
    assert result.xlsx_path.exists()
    assert result.failure_path.exists()
    assert result.batch_dir.parent == tmp_path / "AI选品"
    assert load_batches(tmp_path)[0].batch_dir == result.batch_dir
    assert "商品标题" in result.csv_path.read_text(encoding="utf-8-sig")


def test_download_images_keeps_good_candidate_when_another_image_fails(tmp_path, monkeypatch):
    def fake_download(url, target, timeout=20):
        if url.endswith("bad.jpg"):
            raise OSError("network")
        Path(target).write_bytes(b"image")

    monkeypatch.setattr("consoleplat.services.ai_selection_service.download_image", fake_download)
    good = make_candidate(2)
    good.image_url = "https://img.example/good.jpg"
    bad = make_candidate(1)
    bad.image_url = "https://img.example/bad.jpg"

    download_candidate_images([good, bad], tmp_path)

    assert Path(good.local_image_path).exists()
    assert bad.status == "主图下载失败"
    assert "network" in bad.error
