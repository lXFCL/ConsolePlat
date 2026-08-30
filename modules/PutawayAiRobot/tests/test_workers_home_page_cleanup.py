import unittest

from album_cleanup_flow import _is_album_page_url
from workers import _is_dianxiaomi_home_page


class DianxiaomiHomePageCleanupTest(unittest.TestCase):
    def test_matches_dianxiaomi_home_page_urls(self):
        self.assertTrue(_is_dianxiaomi_home_page("https://www.dianxiaomi.com/home.htm"))
        self.assertTrue(_is_dianxiaomi_home_page("https://www.dianxiaomi.com/home.htm?from=robot"))
        self.assertTrue(
            _is_dianxiaomi_home_page(
                "https://www.dianxiaomi.com/web/home?from=robot",
                "https://www.dianxiaomi.com/web/home",
            )
        )

    def test_does_not_match_create_or_other_pages(self):
        self.assertFalse(_is_dianxiaomi_home_page("https://www.dianxiaomi.com/temu/createProduct.htm"))
        self.assertFalse(_is_dianxiaomi_home_page("https://www.dianxiaomi.com/pictureSpace/index.htm"))
        self.assertFalse(_is_dianxiaomi_home_page("https://example.com/home.htm"))
        self.assertFalse(_is_dianxiaomi_home_page(""))

    def test_matches_custom_album_url_ignoring_query_parameters(self):
        self.assertTrue(
            _is_album_page_url(
                "https://www.dianxiaomi.com/web/service/album?_ts=123",
                "https://www.dianxiaomi.com/web/service/album",
            )
        )
        self.assertFalse(
            _is_album_page_url(
                "https://www.dianxiaomi.com/album/index.htm",
                "https://www.dianxiaomi.com/web/service/album",
            )
        )


if __name__ == "__main__":
    unittest.main()
