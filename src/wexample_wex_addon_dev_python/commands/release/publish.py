from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.helpers.shell import shell_run
from wexample_wex_core.decorator.command import command
from wexample_wex_core.decorator.option import option

if TYPE_CHECKING:
    from wexample_wex_core.context.execution_context import ExecutionContext


@command(description="Publish the Python package to PyPI.")
@option(
    name="username",
    type=str,
    required=False,
    description="PyPI username (use '__token__' when using an API token); if omitted, environment variables may be used.",
)
@option(
    name="password",
    type=str,
    required=False,
    description="PyPI password or API token value; if omitted, environment variables may be used.",
)
@option(
    name="token",
    type=str,
    required=False,
    description="Convenience: API token (maps to username='__token__' and password=<token>); overrides username/password if provided.",
)
def python__release__publish(
        context: ExecutionContext,
        username: str | None,
        password: str | None,
        token: str | None,
) -> None:
    shell_run(
        ['pdm', 'build'],
        inherit_stdio=True,
    )

    # Map token to PyPI's token-based authentication if provided
    if token:
        username = '__token__'
        password = token

    # Build the publish command, adding credentials only when given
    publish_cmd = ['pdm', 'publish']
    if username is not None:
        publish_cmd += ['--username', username]
    if password is not None:
        publish_cmd += ['--password', password]

    shell_run(
        publish_cmd,
        inherit_stdio=True,
    )
