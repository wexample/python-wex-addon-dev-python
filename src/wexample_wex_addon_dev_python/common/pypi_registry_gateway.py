from __future__ import annotations

from wexample_api.common.abstract_gateway import AbstractGateway
from wexample_helpers.classes.field import public_field
from wexample_helpers.decorator.base_class import base_class


@base_class
class PypiRegistryGateway(AbstractGateway):
    """Thin HTTP gateway over the PyPI Simple index (PEP 503).

    Targets public PyPI (`https://pypi.org`) and private indexes that
    expose the same `/simple/<package>/` layout (e.g. GitLab Package
    Registry). Optional Basic auth is wired via `username` + `token`
    (use `__token__` as username for token-based auth).
    """

    username: str | None = public_field(
        default=None,
        description="Username for Basic auth. Use '__token__' for token-based auth.",
    )
    token: str | None = public_field(
        default=None,
        description="API token paired with `username` for Basic auth.",
    )

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        if self.token:
            import base64

            credentials = base64.b64encode(
                f"{self.username or '__token__'}:{self.token}".encode()
            ).decode()
            self.default_headers["Authorization"] = f"Basic {credentials}"

    def has_version(self, package: str, version: str) -> bool:
        """Return True iff `package==version` is published on this index.

        Uses the PEP 503 Simple index and matches the version string against
        the HTML body. Returns False on 404 (unknown package, or version not
        yet propagated through the registry's CDN).
        """
        response = self.make_request(
            endpoint=f"simple/{package}/",
            expected_status_codes=[200, 404],
            fatal_if_unexpected=False,
            quiet=True,
        )
        if response is None or response.status_code != 200:
            return False
        return version in response.text
