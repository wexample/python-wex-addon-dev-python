from wexample_wex_core.common.kernel import Kernel
from wexample_wex_core.decorator.command import command
from wexample_wex_core.decorator.option import option


@option(name="file_path", type=str, required=True)
@command()
def python__code__check(
        kernel: "Kernel",
        file_path: str
) -> None:
    import os

    if os.path.exists(file_path):
        print('Code OK ' + file_path)
