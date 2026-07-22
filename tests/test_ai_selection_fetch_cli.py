from consoleplat.services.ai_selection_fetch_cli import _search, parse_search_cards, should_stop_after_page


def test_parse_search_cards_marks_missing_sales_as_failures():
    cards, failures = parse_search_cards(
        [
            {
                "title": "商品 A",
                "sales_text": "已售 1.2K",
                "price": "$9",
                "href": "/goods-a.html",
                "image_url": "https://img.example/a.jpg",
            },
            {
                "title": "商品 B",
                "sales_text": "",
                "price": "$8",
                "href": "/goods-b.html",
                "image_url": "https://img.example/b.jpg",
            },
        ],
        keyword="黑白T恤",
    )

    assert len(cards) == 1
    assert cards[0].sales_count == 1200
    assert cards[0].product_url == "https://www.temu.com/goods-a.html"
    assert failures == ["商品 商品 B 未读取到销量"]


def test_should_stop_only_after_two_empty_pages():
    assert should_stop_after_page(1) is False
    assert should_stop_after_page(2) is True


def test_search_uses_visible_search_field_without_child_filter():
    calls = []

    class Field:
        @property
        def first(self):
            return self

        def count(self):
            return 1

        def is_visible(self):
            return True

        def fill(self, value, timeout):
            calls.append(("fill", value, timeout))

        def press(self, key, timeout):
            calls.append(("press", key, timeout))

    class Page:
        def locator(self, selector):
            calls.append(("locator", selector))
            return Field()

        def wait_for_load_state(self, state, timeout):
            calls.append(("wait", state, timeout))

    assert _search(Page(), "黑白T恤") is True
    assert ("fill", "黑白T恤", 2500) in calls
    assert ("press", "Enter", 2500) in calls
