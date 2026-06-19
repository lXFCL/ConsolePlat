from consoleplat.config import AppSettings, ShopAccount
from consoleplat.services.monitor_fetch_cli import _monitor_account


def test_monitor_cli_reuses_saved_login_for_selected_shop_without_credentials():
    settings = AppSettings(
        active_shop="YUHAOBO",
        accounts={
            "YUHOOBO": ShopAccount(shop_name="YUHOOBO", phone="18800000000", password="secret"),
        },
    )

    account = _monitor_account(settings)

    assert account is not None
    assert account.shop_name == "YUHAOBO"
    assert account.phone == "18800000000"
    assert account.password == "secret"

