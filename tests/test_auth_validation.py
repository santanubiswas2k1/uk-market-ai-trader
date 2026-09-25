from src.security.auth import REQUIRED_SCOPE, _valid_audiences, _valid_issuers
from src.config import SETTINGS


def test_required_scope_name():
    assert REQUIRED_SCOPE == "access_as_user"


def test_configured_audience_supports_uri_and_guid():
    if SETTINGS.api_audience and SETTINGS.api_audience.startswith("api://"):
        audiences = _valid_audiences()
        assert SETTINGS.api_audience in audiences
        assert SETTINGS.api_audience.removeprefix("api://") in audiences


def test_valid_issuers_include_v1_and_v2():
    if SETTINGS.azure_tenant_id:
        issuers = _valid_issuers()
        assert f"https://login.microsoftonline.com/{SETTINGS.azure_tenant_id}/v2.0" in issuers
        assert f"https://sts.windows.net/{SETTINGS.azure_tenant_id}/" in issuers
