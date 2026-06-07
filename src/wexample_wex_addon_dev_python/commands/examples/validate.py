from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_cli.const.tags import AudienceTag, EffectTag, ScopeTag
from wexample_cli.decorator.command import command
from wexample_wex_core.const.globals import COMMAND_TYPE_ADDON

if TYPE_CHECKING:
    from wexample_cli.context.execution_context import ExecutionContext


@command(
    type=COMMAND_TYPE_ADDON,
    description="Check python code on every file.",
    tags=[
        EffectTag.READ_ONLY,
        AudienceTag.AGENT_SAFE,
        ScopeTag.LOCAL,
        ScopeTag.PACKAGE,
    ],
)
def python__examples__validate(
    context: ExecutionContext,
) -> None:
    from wexample_wex_addon_dev_python.commands.examples.classes.example_pydantic_class_with_public_var_internaly_defined import (
        ExamplePydanticClassWithPublicVarInternallyDefined,
    )

    example_class = ExamplePydanticClassWithPublicVarInternallyDefined()
    context.kernel.log(example_class)
