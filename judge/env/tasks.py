from dataclasses import dataclass, field
from datetime import timedelta, datetime
from subprocess import Popen, PIPE, TimeoutExpired
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
    env: Optional[Dict[str, str]] = None

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
        child = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=self.env)
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
