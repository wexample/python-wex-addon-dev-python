from __future__ import annotations

from wexample_wex_addon_app.workdir.mixin.abstract_profiling_workdir_mixin import (
    AbstractProfilingWorkdirMixin,
)


class WithProfilingPythonWorkdirMixin(AbstractProfilingWorkdirMixin):
    """Mixin that adds pytest-benchmark profiling capability to a Python workdir.

    Runs benchmarks in the workdir's local venv so that local (unpublished)
    dependencies are available — no Docker required.

    Requires the workdir to have benchmark tests written with pytest-benchmark:
        def test_my_function(benchmark):
            benchmark(my_function, ...)
    """

    _BENCH_OUTPUT_FILENAME = ".wex_bench.json"

    def run_profiling(self) -> dict:
        import json
        import subprocess

        bench_output_path = self.get_path() / self._BENCH_OUTPUT_FILENAME
        python = self._get_profiling_python()


        bench_result = subprocess.run(
            [
                str(python), "-m", "pytest", self.get_benchmark_dir(),
                "--benchmark-only",
                f"--benchmark-json={bench_output_path}",
                "-q",
            ],
            capture_output=True,
            text=True,
            cwd=str(self.get_path()),
        )

        if not bench_output_path.exists():
            return {
                "error": (
                    "No benchmark output produced.\n"
                    f"pytest stdout:\n{bench_result.stdout}\n"
                    f"pytest stderr:\n{bench_result.stderr}"
                )
            }

        try:
            content = bench_output_path.read_text().strip()
            if not content:
                return {
                    "error": (
                        "No benchmark tests found. Add tests using pytest-benchmark:\n"
                        "  def test_my_function(benchmark):\n"
                        "      benchmark(my_function, ...)"
                    )
                }
            raw = json.loads(content)
        finally:
            bench_output_path.unlink(missing_ok=True)

        return self._parse_profiling_output(raw)

    def _get_profiling_python(self):
        import sys
        from pathlib import Path

        return Path(sys.executable)

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
