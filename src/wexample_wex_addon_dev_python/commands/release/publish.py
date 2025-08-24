from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_helpers.helpers.shell import shell_run
from wexample_wex_core.decorator.command import command

if TYPE_CHECKING:
    from wexample_wex_core.context.execution_context import ExecutionContext


@command(description=" ")
def python__release__publish(
        context: ExecutionContext,
) -> None:

    shell_run(
        ['pdm', 'build'],
        inherit_stdio=True
    )
