import unittest

from workers import _is_dianxiaomi_home_page


class DianxiaomiHomePageCleanupTest(unittest.TestCase):
    def test_matches_dianxiaomi_home_page_urls(self):
        self.assertTrue(_is_dianxiaomi_home_page("https://www.dianxiaomi.com/home.htm"))
        self.assertTrue(_is_dianxiaomi_home_page("https://www.dianxiaomi.com/home.htm?from=robot"))

    def test_does_not_match_create_or_other_pages(self):
        self.assertFalse(_is_dianxiaomi_home_page("https://www.dianxiaomi.com/temu/createProduct.htm"))
        self.assertFalse(_is_dianxiaomi_home_page("https://www.dianxiaomi.com/pictureSpace/index.htm"))
        self.assertFalse(_is_dianxiaomi_home_page("https://example.com/home.htm"))
        self.assertFalse(_is_dianxiaomi_home_page(""))


if __name__ == "__main__":
    unittest.main()
