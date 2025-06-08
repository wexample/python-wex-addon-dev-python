from wexample_wex_core.common.kernel import Kernel
from wexample_wex_core.decorator.command import command


@command()
def python__code__check(
        kernel: "Kernel"
) -> None:
    print('Code OK')
