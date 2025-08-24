from __future__ import annotations

from typing import TYPE_CHECKING

from wexample_wex_core.decorator.command import command

if TYPE_CHECKING:
    from wexample_wex_core.context.execution_context import ExecutionContext


@command(description="Check python code on every file.")
def python__examples__validate(
    context: ExecutionContext,
) -> None:
    from wexample_wex_addon_dev_python.commands.examples.classes.example_pydantic_class_with_public_var_internaly_defined import (
        ExamplePydanticClassWithPublicVarInternallyDefined,
    )

    example_class = ExamplePydanticClassWithPublicVarInternallyDefined()
    context.kernel.log(example_class)
