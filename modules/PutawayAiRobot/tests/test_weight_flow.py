import pytest

from weight_flow import fill_weights


class FakeInput:
    def __init__(self):
        self.filled = []

    def scroll_into_view_if_needed(self, **_kwargs):
        return None

    def click(self, **_kwargs):
        return None

    def fill(self, value, **_kwargs):
        self.filled.append(value)


class FakeLocator:
    def __init__(self, inputs):
        self.inputs = inputs

    def count(self):
        return len(self.inputs)

    def nth(self, index):
        return self.inputs[index]


class FakePage:
    def __init__(self, inputs):
        self.inputs = inputs

    def locator(self, selector):
        assert selector == 'input[name="weight"]:visible'
        return FakeLocator(self.inputs)

    def wait_for_timeout(self, _milliseconds):
        return None


def test_fill_weights_fills_each_visible_input_in_order():
    inputs = [FakeInput() for _ in range(5)]

    fill_weights(FakePage(inputs), [140, 141, 150, 155, 166])

    assert [item.filled for item in inputs] == [["140"], ["141"], ["150"], ["155"], ["166"]]


@pytest.mark.parametrize("weights", [[142, 147, 152, 157], [142, 147, 152, 157, 0], [142, 147, 152, 157, 162.5]])
def test_fill_weights_rejects_values_that_are_not_five_positive_integers(weights):
    with pytest.raises(ValueError, match="五个正整数"):
        fill_weights(FakePage([FakeInput() for _ in range(5)]), weights)
