from __future__ import annotations

from pathlib import Path

from wexample_wex_addon_app.workdir.mixin.with_runner_workdir_mixin import (
    WithRunnerWorkdirMixin,
)


class WithProfilingWorkdirMixin(WithRunnerWorkdirMixin):
    """Mixin that adds pytest-benchmark profiling capability to a workdir.

    Only implemented for Python workdirs. Other workdir types will not inherit this mixin,
    allowing commands to use isinstance(workdir, WithProfilingWorkdirMixin) as a guard.

    Requires the workdir to have benchmark tests written with pytest-benchmark:
        def test_my_function(benchmark):
            benchmark(my_function, ...)
    """

    _PROFILING_RUNNER_NAME = "python-profiling"
    _BENCH_OUTPUT_FILENAME = ".wex_bench.json"

    def get_runners(self) -> dict:
        from wexample_runner.runner_config import RunnerConfig

        dockerfile = (
            Path(__file__).parent.parent.parent
            / "resources"
            / "docker"
            / "Dockerfile.python-profiling"
        )

        runners = super().get_runners()
        runners[self._PROFILING_RUNNER_NAME] = RunnerConfig(
            dockerfile=str(dockerfile),
            mount_path=str(self.get_path()),
            container_workdir="/app",
            ephemeral=False,
        )
        return runners

    def run_profiling(self) -> dict:
        import json

        bench_output_path = self.get_path() / self._BENCH_OUTPUT_FILENAME

        # HOME=/tmp ensures pip and other tools can write in a container
        # running as an arbitrary host UID (no home dir defined inside the image).
        _env = {"HOME": "/tmp", "PIP_NO_CACHE_DIR": "1"}

        # Install project on first use (cached via sentinel file in container)
        install_result = self.runner_exec(
            self._PROFILING_RUNNER_NAME,
            ["sh", "-c", "test -f /tmp/wex_installed || (pip install -e /app -q && touch /tmp/wex_installed)"],
            env=_env,
        )
        if install_result.exit_code != 0:
            return {"error": f"Project install failed:\n{install_result.stderr}"}

        bench_result = self.runner_exec(
            self._PROFILING_RUNNER_NAME,
            [
                "python", "-m", "pytest", "tests/",
                "--benchmark-only",
                f"--benchmark-json=/app/{self._BENCH_OUTPUT_FILENAME}",
                "-q",
            ],
            env=_env,
        )

        if not bench_output_path.exists():
            return {
                "error": (
                    "No benchmark output produced. "
                    "Make sure tests/ contains benchmark tests using pytest-benchmark.\n"
                    f"pytest stdout:\n{bench_result.stdout}\n"
                    f"pytest stderr:\n{bench_result.stderr}"
                )
            }

        try:
            content = bench_output_path.read_text().strip()
            if not content:
                return {"error": "No benchmark tests found. Add tests using pytest-benchmark:\n  def test_my_function(benchmark):\n      benchmark(my_function, ...)"}
            raw = json.loads(content)
        finally:
            bench_output_path.unlink(missing_ok=True)

        return self._parse_profiling_output(raw)

    def _parse_profiling_output(self, raw: dict) -> dict:
        entries = []
        for bench in raw.get("benchmarks", []):
            stats = bench.get("stats", {})
            entries.append({
                "name": bench.get("name"),
                "min_ms": round(stats.get("min", 0) * 1000, 3),
                "mean_ms": round(stats.get("mean", 0) * 1000, 3),
                "median_ms": round(stats.get("median", 0) * 1000, 3),
                "max_ms": round(stats.get("max", 0) * 1000, 3),
                "rounds": stats.get("rounds", 0),
            })

        return {
            "language": "python",
            "tool": "pytest-benchmark",
            "entries": entries,
        }
