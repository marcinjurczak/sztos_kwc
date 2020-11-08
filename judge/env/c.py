from pathlib import Path
from typing import Dict

from .runner import Runner
from .tasks import TaskResult, Task


class CRunner(Runner):
    _build_dir: Path

    def __init__(self):
        super().__init__()
        self._build_dir = Path(self._work_dir.name, "build")

        self._build_dir.mkdir()

    def compile(self, sources: Dict[str, str]) -> TaskResult:
        super().compile(sources)

        paths = (f"sources/{name}" for name in sources.keys())

        task = Task(
            ["/usr/bin/g++", *paths, "-o", "/app/build/a.out"],
            cwd="/app",
            ro_binds=[("/lib", "/lib"), ("/lib64", "/lib64"), ("/usr", "/usr"), ("/bin", "/bin")],
            binds=[(self._work_dir.name, "/app")],
            unshare_all=True,
        )

        return task.execute()

    def run(self, stdin: bytes, memory_limit: int, time_limit: int):
        task = Task(
            ["./a.out"],
            stdin=stdin,
            cwd="/app",
            ro_binds=[("/lib", "/lib"), ("/lib64", "/lib64"), ("/usr", "/usr"), (str(self._build_dir), "/app")],
            unshare_all=True,
            memory_limit=memory_limit,
            time_limit=time_limit
        )

        return task.execute()


