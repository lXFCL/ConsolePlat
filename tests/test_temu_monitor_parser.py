from consoleplat.services.temu_monitor_source import (
    LoginRequiredError,
    TARGET_URL,
    choose_auth_gateway_click_point,
    choose_preferred_page,
    should_navigate_to_target,
    is_auth_gateway_text,
    is_business_page_text,
    is_login_page_text,
    parse_monitor_payload,
    phone_login_selectors,
    login_submit_labels,
    choose_new_page,
    choose_policy_click_point,
    is_authorization_confirm_text,
    TemuMonitorSource,
    choose_current_shop_name,
    choose_shop_click_point,
    choose_target_shop_switch_point,
    monitor_shop_names,
)


def test_parse_monitor_payload_extracts_yuhoobo_orders_and_metrics():
    payload = {
        "tab_counts": {
            "全部": 2424,
            "待发货": 2,
            "已送货": 68,
        },
        "rows": [
            {
                "text": "备货单号 WB2606194882401 备货母单号 WP2606198703980 商品信息 货号：SZW-3113 SKU 信息 属性：黑色-M SKU 货号：SZW-3113-M 备货件数 12",
                "cells": ["WB2606194882401", "SZW-3113", "黑色-M SKU 货号：SZW-3113-M", "12", "待发货"],
            },
            {
                "text": "备货单号 WB2606194882412 备货母单号 WP2606198703981 商品信息 货号：SZW-3114 SKU 信息 属性：白色-XL SKU 货号：SZW-3114-XL 备货件数 7",
                "cells": ["WB2606194882412", "SZW-3114", "白色-XL SKU 货号：SZW-3114-XL", "7", "待发货"],
            },
        ],
    }

    snapshot = parse_monitor_payload(payload, shop_name="YUHOOBO", refresh_interval_seconds=5)

    assert snapshot.shop_name == "YUHOOBO"
    assert snapshot.metrics["待发货"] == 2
    assert snapshot.metrics["备货件数"] == 19
    assert snapshot.orders[0].product_sku == "SZW-3113"
    assert snapshot.orders[0].sku_code == "SZW-3113-M"
    assert snapshot.orders[0].color == "黑色"
    assert snapshot.orders[0].size == "M"


def test_parse_monitor_payload_accepts_sendgoods_records():
    payload = {
        "tab_counts": {"待发货": 1},
        "records": [
            {
                "beihuo_order": "WB2606194882401",
                "parent_order": "WP2606198703980",
                "product_sku": "SZW-3113",
                "sku_code": "SZW-3113-M",
                "sku_attr": "黑色-M",
                "color": "黑色",
                "size": "M",
                "quantity": 12,
                "image_url": "https://img.kwcdn.com/product/open/demo-goods.jpeg",
            }
        ],
    }

    snapshot = parse_monitor_payload(payload, shop_name="YUHOOBO", refresh_interval_seconds=5)

    assert len(snapshot.orders) == 1
    assert snapshot.orders[0].order_id == "WB2606194882401"
    assert snapshot.orders[0].product_sku == "SZW-3113"
    assert snapshot.orders[0].quantity == 12
    assert snapshot.metrics["备货件数"] == 12


def test_parse_monitor_payload_uses_real_zero_tab_count_without_demo_rows():
    payload = {
        "tab_counts": {
            "全部": 2,
            "待发货": 0,
            "已入库": 2,
        },
        "rows": [],
        "page_text": "全部(2) 待创建(0) 待发货(0) 已入库(2) 暂无数据 共有 0 条",
    }

    snapshot = parse_monitor_payload(payload, shop_name="YUHOOBO", refresh_interval_seconds=5)

    assert snapshot.metrics["待发货"] == 0
    assert snapshot.metrics["备货件数"] == 0
    assert snapshot.orders == ()
    assert "待发货 0" in snapshot.events[0].message


def test_login_page_text_detection_handles_auth_pages():
    assert is_login_page_text("欢迎 登录 手机号 密码")
    assert is_login_page_text("确认授权并前往 Seller Central")
    assert is_login_page_text("即将前往 Seller Central（全球）的「YUHOOBO」店铺 确认授权并前往")
    assert not is_login_page_text("紧急备货建议 待发货 备货单号")


def test_business_page_requires_real_business_text_not_only_url():
    assert is_business_page_text("紧急备货建议 待发货 备货单号 备货件数")
    assert not is_business_page_text("Seller Central 登录 手机号 密码")
    assert not is_business_page_text("")


def test_business_page_detection_tolerates_global_login_text():
    text = (
        "TEMU Agent Center 登录账号 紧急备货建议 "
        "全部(2) 待创建(0) 待发货(0) 已入库(2) "
        "备货单号 SKU 货号 暂无数据 共有 0 条"
    )

    assert is_business_page_text(text)
    assert not is_login_page_text(text)


def test_page_state_prefers_business_text_over_plugin_login_hint():
    source = object.__new__(TemuMonitorSource)
    source._plugin_state = lambda page: {"isLoginLike": True, "textSample": "登录 手机号"}

    state = source._page_state(
        object(),
        "TEMU Agent Center 登录 紧急备货建议 全部(2) 待发货(0) 备货单号 暂无数据",
    )

    assert state == "business"


def test_shop_detection_finds_current_top_bar_shop():
    elements = [
        {"text": "TEMU Agent Center", "x": 210, "y": 18, "w": 160, "h": 24},
        {"text": "YUHAOBO", "x": 58, "y": 19, "w": 78, "h": 20},
        {"text": "YUHOOBO", "x": 90, "y": 220, "w": 82, "h": 20},
    ]

    assert choose_current_shop_name(elements, monitor_shop_names("YUHOOBO")) == "YUHAOBO"


def test_shop_menu_click_prefers_current_shop_in_header():
    elements = [
        {"text": "YUHAOBO", "x": 58, "y": 19, "w": 78, "h": 20},
        {"text": "YUHAOBO 商品列表", "x": 300, "y": 320, "w": 180, "h": 24},
    ]

    assert choose_shop_click_point(elements, "YUHAOBO") == (97, 29)


def test_target_shop_switch_point_uses_button_in_target_row():
    elements = [
        {"text": "当前店铺 YUHAOBO 切换", "x": 340, "y": 263, "w": 600, "h": 90},
        {"text": "切换", "x": 847, "y": 294, "w": 68, "h": 28},
        {"text": "YUHOOBO 切换", "x": 340, "y": 365, "w": 600, "h": 90},
        {"text": "切换", "x": 847, "y": 396, "w": 68, "h": 28},
    ]

    assert choose_target_shop_switch_point(elements, "YUHOOBO") == (881, 410)


def test_cdp_backed_source_close_does_not_close_browser_page():
    class DummyContext:
        closed = False

        def close(self):
            self.closed = True

    class DummyBrowser:
        closed = False

        def close(self):
            self.closed = True

    class DummyPlaywright:
        stopped = False

        def stop(self):
            self.stopped = True

    source = object.__new__(TemuMonitorSource)
    context = DummyContext()
    browser = DummyBrowser()
    playwright = DummyPlaywright()
    source._context = context
    source._browser = browser
    source._playwright = playwright
    source._owns_context = False

    source.close()

    assert not context.closed
    assert not browser.closed
    assert playwright.stopped


def test_monitor_source_attempts_to_set_page_size_to_100():
    class FakePage:
        def __init__(self):
            self.scripts = []
            self.waits = []

        def evaluate(self, script):
            self.scripts.append(script)
            return len(self.scripts) in {2, 3}

        def wait_for_timeout(self, _ms):
            self.waits.append(_ms)

    source = object.__new__(TemuMonitorSource)
    page = FakePage()

    source._ensure_page_size_100(page)

    assert page.waits == [700, 1500]
    assert len(page.scripts) == 3
    assert "scrollTo" not in page.scripts[0]
    assert any("scrollTo" in script for script in page.scripts)
    assert any("100" in script for script in page.scripts)


def test_monitor_source_does_not_scroll_when_page_size_is_already_100():
    class FakePage:
        def __init__(self):
            self.scripts = []
            self.waits = []

        def evaluate(self, script):
            self.scripts.append(script)
            return True

        def wait_for_timeout(self, _ms):
            self.waits.append(_ms)

    source = object.__new__(TemuMonitorSource)
    page = FakePage()

    source._ensure_page_size_100(page)

    assert page.waits == []
    assert len(page.scripts) == 1
    assert "scrollTo" not in page.scripts[0]


def test_monitor_source_closes_only_target_monitor_pages():
    class FakePage:
        def __init__(self, url):
            self.url = url
            self.closed = False

        def close(self):
            self.closed = True

    target = FakePage("https://agentseller.temu.com/stock/fully-mgt/order-manage-urgency")
    other_agent_page = FakePage("https://agentseller.temu.com/goods/list")
    other_site_page = FakePage("https://example.com/stock/fully-mgt/order-manage-urgency")

    class FakeContext:
        pages = [target, other_agent_page, other_site_page]

    source = object.__new__(TemuMonitorSource)
    source._context = FakeContext()

    closed_count = source.close_monitor_pages()

    assert closed_count == 1
    assert target.closed
    assert not other_agent_page.closed
    assert not other_site_page.closed


def test_monitor_source_close_pages_does_not_launch_chrome_when_cdp_unavailable():
    class FailingChromium:
        def connect_over_cdp(self, _endpoint):
            raise RuntimeError("cdp unavailable")

    class FakePlaywright:
        chromium = FailingChromium()

    source = object.__new__(TemuMonitorSource)
    source._context = None
    source._playwright = FakePlaywright()
    source.cdp_endpoint = "http://127.0.0.1:9222"
    source._launch_chrome_for_cdp = lambda: (_ for _ in ()).throw(AssertionError("should not launch chrome"))

    assert source.close_monitor_pages() == 0


def test_page_size_script_handles_right_bottom_page_size_text_variants():
    class FakePage:
        def __init__(self):
            self.scripts = []
            self.waits = []

        def evaluate(self, script):
            self.scripts.append(script)
            return len(self.scripts) in {2, 3}

        def wait_for_timeout(self, _ms):
            self.waits.append(_ms)

    source = object.__new__(TemuMonitorSource)
    page = FakePage()

    source._ensure_page_size_100(page)

    combined = "\n".join(page.scripts)
    assert "isPageSize100" in combined
    assert "findPageSizeTrigger" in combined
    assert "clickableParent" in combined
    assert "pointerdown" in combined
    assert "itemPerPage100" in combined
    assert "pageChar" in combined


def test_auth_gateway_detection_handles_region_center_page():
    assert is_auth_gateway_text("Beta 中文 卖家课堂 商家中心 中国地区 商家中心 其他地区 敬请期待")
    assert not is_auth_gateway_text("紧急备货建议 待发货 备货单号")


def test_choose_auth_gateway_click_point_prefers_right_side_center_entry():
    elements = [
        {"text": "商家中心", "x": 320, "y": 180, "w": 640, "h": 20},
        {"text": "中国地区 商家中心", "x": 320, "y": 240, "w": 640, "h": 103},
        {"text": "商家中心", "x": 686, "y": 281, "w": 100, "h": 21},
    ]

    point = choose_auth_gateway_click_point(elements)

    assert point == (736, 291)


def test_choose_preferred_page_uses_new_login_tab_after_gateway_click():
    pages = [
        "https://agentseller.temu.com/auth/authentication?redirectUrl=https%3A%2F%2Fagentseller.temu.com%2Fstock%2Ffully-mgt%2Forder-manage-urgency",
        "https://seller.kuajingmaihuo.com/settle/seller-login?redirectUrl=https%3A%2F%2Fagentseller.temu.com%2Fstock%2Ffully-mgt%2Forder-manage-urgency",
    ]

    assert choose_preferred_page(pages) == 1


def test_choose_preferred_page_uses_actual_target_path_not_redirect_param():
    pages = [
        "https://agentseller.temu.com/auth/authentication?redirectUrl=https%3A%2F%2Fagentseller.temu.com%2Fstock%2Ffully-mgt%2Forder-manage-urgency",
        "https://agentseller.temu.com/stock/fully-mgt/order-manage-urgency",
    ]

    assert choose_preferred_page(pages) == 1


def test_choose_preferred_page_ignores_unescaped_redirect_param():
    pages = [
        "https://agentseller.temu.com/auth/authentication?redirectUrl=https://agentseller.temu.com/stock/fully-mgt/order-manage-urgency",
        "https://seller.kuajingmaihuo.com/settle/seller-login?redirectUrl=target",
    ]

    assert choose_preferred_page(pages) == 1


def test_choose_preferred_page_prefers_newest_login_tab():
    pages = [
        "https://seller.kuajingmaihuo.com/settle/seller-login?redirectUrl=old",
        "https://agentseller.temu.com/auth/authentication?redirectUrl=target",
        "https://seller.kuajingmaihuo.com/settle/seller-login?redirectUrl=new",
    ]

    assert choose_preferred_page(pages) == 2


def test_phone_login_selectors_cover_real_seller_login_input():
    selectors = phone_login_selectors()

    assert "input[name='usernameId']" in selectors
    assert "input[placeholder*='手机号码']" in selectors


def test_fetch_navigation_does_not_interrupt_login_or_auth_pages():
    login_url = "https://seller.kuajingmaihuo.com/settle/seller-login?redirectUrl=target"
    auth_url = "https://agentseller.temu.com/auth/authentication?redirectUrl=target"

    assert should_navigate_to_target("", "") is True
    assert should_navigate_to_target(TARGET_URL, "紧急备货建议 待发货") is False
    assert should_navigate_to_target(login_url, "手机号登录 密码 授权登录") is False
    assert should_navigate_to_target(auth_url, "中国地区 商家中心 敬请期待") is False


def test_login_submit_prefers_authorized_login_button_over_generic_login_text():
    labels = login_submit_labels()

    assert labels[0] == "授权登录"
    assert labels.index("授权登录") < labels.index("登录")


def test_authorization_confirm_page_detection():
    text = "即将前往 Seller Central（全球）的「YUHOOBO」店铺 您授权您的账号ID和店铺名称在卖家中心各板块共享，并已阅读并同意 隐私政策 确认授权并前往"

    assert is_authorization_confirm_text(text)


def test_choose_new_page_prefers_page_created_after_click():
    before = ["https://agentseller.temu.com/auth/authentication"]
    after = [
        "https://agentseller.temu.com/auth/authentication",
        "https://seller.kuajingmaihuo.com/settle/seller-login?redirectUrl=target",
    ]

    assert choose_new_page(before, after) == 1


def test_choose_policy_click_point_targets_visible_checkbox_area():
    elements = [
        {"text": "隐私政策", "x": 168, "y": 445, "w": 40, "h": 16},
        {"text": "您授权您的账号ID和店铺名称在卖家中心各板块共享，并已阅读并同意 隐私政策", "x": 168, "y": 431, "w": 370, "h": 31},
    ]

    assert choose_policy_click_point(elements) == (158, 439)


def test_login_required_error_is_a_runtime_error():
    err = LoginRequiredError("需要人工登录")

    assert isinstance(err, RuntimeError)
