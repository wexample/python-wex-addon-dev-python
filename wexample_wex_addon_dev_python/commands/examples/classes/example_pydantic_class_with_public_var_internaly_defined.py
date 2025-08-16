from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, PrivateAttr


# Stay lazy as most as possible
if TYPE_CHECKING:
    from wexample_wex_addon_dev_python.commands.examples.utils.some_example_type import SomeExampleType


class ExamplePydanticClassWithPublicVarInternallyDefined(BaseModel):
    _internal_var: "SomeExampleType" = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        # Lazy import to avoid circular imports; runs after validation
        from wexample_wex_addon_dev_python.commands.examples.utils.some_example_type import SomeExampleType
        self._internal_var = SomeExampleType(property="Yes")

    @property
    def public_var(self) -> "SomeExampleType":
        return self._internal_var

    @public_var.setter
    def public_var(self, value: "SomeExampleType") -> None:
        from wexample_wex_addon_dev_python.commands.examples.utils.some_example_type import SomeExampleType

        # Stay lazy as most as possible
        # Check value at setting, avoid checking it
        if not isinstance(value, SomeExampleType):
            raise TypeError(f"internal_var must be SomeExampleType, got {type(value)!r}")
        self._internal_var = value

