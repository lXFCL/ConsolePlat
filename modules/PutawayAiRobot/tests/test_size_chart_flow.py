from size_chart_flow import _select_grouped_ant_option


class FakeOption:
    def __init__(self, text, group):
        self.text = text
        self.group = group
        self.clicked = False

    def inner_text(self, **_kwargs):
        return self.text

    def scroll_into_view_if_needed(self, **_kwargs):
        return None

    def evaluate(self, _script):
        return self.group

    def get_attribute(self, name):
        return self.text if name == "label" else None

    def click(self, **_kwargs):
        self.clicked = True


class FakeGroup:
    def __init__(self, text):
        self.text = text

    def inner_text(self, **_kwargs):
        return self.text


class FakeLocator:
    def __init__(self, items):
        self.items = items

    def count(self):
        return len(self.items)

    def nth(self, index):
        return self.items[index]


class FakePage:
    def __init__(self, items):
        self.items = items

    def locator(self, selector):
        if selector == ".ant-select-dropdown:visible .ant-select-item-group":
            return FakeLocator([item for item in self.items if isinstance(item, FakeGroup)])
        if selector == ".ant-select-dropdown:visible .ant-select-item-option-grouped":
            return FakeLocator([item for item in self.items if isinstance(item, FakeOption)])
        raise AssertionError(f"unexpected selector: {selector}")


def test_selects_matching_option_from_requested_ant_group():
    backend_template = FakeOption("T恤", "后台模板")
    shop_template = FakeOption("T恤", "店小秘模板")
    page = FakePage(
        [
            FakeGroup("后台模板"),
            backend_template,
            FakeGroup("店小秘模板"),
            shop_template,
        ]
    )

    assert _select_grouped_ant_option(page, "店小秘模板", "T恤") is True
    assert backend_template.clicked is False
    assert shop_template.clicked is True


def test_grouped_option_selection_fails_when_requested_group_is_missing():
    page = FakePage([FakeGroup("后台模板"), FakeOption("T恤", "后台模板")])

    assert _select_grouped_ant_option(page, "店小秘模板", "T恤") is False
