from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import timedelta, datetime
from pathlib import Path
from subprocess import Popen, PIPE, TimeoutExpired
from tempfile import TemporaryDirectory
from typing import List, Optional, Tuple, Dict


@dataclass
class TaskResult:
    stdout: bytes
    stderr: bytes
    return_code: int
    time: timedelta
    timed_out: bool


@dataclass
class Task:
    argv: List[str]
    stdin: bytes = b""
    cwd: Optional[str] = None
    ro_binds: List[Tuple[str, str]] = field(default_factory=list)
    binds: List[Tuple[str, str]] = field(default_factory=list)
    unshare_all: bool = False
    memory_limit: Optional[int] = None
    time_limit: Optional[float] = None

    def execute(self) -> TaskResult:
        flags = ["--die-with-parent"]
        for src, dst in self.ro_binds:
            flags += ["--ro-bind", src, dst]

        for src, dst in self.binds:
            flags += ["--bind", src, dst]

        if self.unshare_all:
            flags.append("--unshare-all")

        if self.cwd:
            flags += ["--chdir", self.cwd]

        args = ["/usr/bin/bwrap", *flags, *self.argv]
        if self.memory_limit:
            args = ["/usr/bin/setrlimit", f"{self.memory_limit}"] + args

        print(f"Executing command: {args}")
        child = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        start_time = datetime.now()
        try:
            stdout, stderr = child.communicate(input=self.stdin, timeout=self.time_limit)
            timed_out = False
        except TimeoutExpired:
            timed_out = True
            stdout = b""
            stderr = b""

        time = datetime.now() - start_time

        return TaskResult(
            stdout=stdout,
            stderr=stderr,
            return_code=child.returncode,
            time=time,
            timed_out=timed_out,
        )


class Runner(ABC):
    def set_up(self) -> None:
        return

    def compile(self, sources: Dict[str, str]) -> Optional[TaskResult]:
        return None

    @abstractmethod
    def run(self, stdin: bytes, memory_limit: int, time_limit: int) -> TaskResult:
        raise NotImplementedError()

    def clean_up(self) -> None:
        return


class CRunner(Runner):
    _work_dir: TemporaryDirectory
    _source_dir: Path
    _build_dir: Path

    def __init__(self):
        self._work_dir = TemporaryDirectory()
        self._source_dir = Path(self._work_dir.name, "sources")
        self._build_dir = Path(self._work_dir.name, "build")

        self._source_dir.mkdir()
        self._build_dir.mkdir()

    def compile(self, sources: Dict[str, str]) -> TaskResult:
        for name, content in sources.items():
            with self._source_dir.joinpath(name).open("wb") as source_file:
                source_file.write(content.encode("utf-8"))

        paths = (f"sources/{name}" for name in sources.keys())

        task = Task(
            ["g++", *paths, "-o", "/app/build/a.out"],
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

    def clean_up(self) -> None:
        self._work_dir.cleanup()
