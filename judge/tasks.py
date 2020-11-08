from dataclasses import dataclass, field
from datetime import timedelta, datetime
from logging import Logger
from pathlib import Path
from subprocess import Popen, PIPE, TimeoutExpired
from tempfile import TemporaryDirectory
from typing import Tuple, List, Optional

from celery import shared_task
from celery.utils.log import get_task_logger

from .models import Solution, TestRun

DEFAULT_MEMORY_LIMIT = 1024 * 1024 * 1024  # 1 GB


@shared_task()
def validate_solution(id: int):
    solution = Solution.objects.get(pk=id)
    solution.state = Solution.State.COMPILATION_IN_PROGRESS
    solution.save()

    try:
        validate(solution)
    except Exception as e:
        get_task_logger(__name__).error("An exception was thrown during validation.", e)


def validate(solution: Solution) -> None:
    log: Logger = get_task_logger(__name__)
    tmp_dir = TemporaryDirectory()
    source_path = Path(tmp_dir.name)
    build_path = source_path.joinpath("build")
    build_path.mkdir()
    sources = solution.get_sources()
    for name, content in sources.items():
        with source_path.joinpath(name).open("wb") as source_file:
            source_file.write(content.encode("utf-8"))

    # call gcc
    log.debug("Compiling")
    result = Task(
        ["g++", *sources.keys(), "-o", "/app/build/a.out"],
        cwd="/app",
        ro_binds=[("/lib", "/lib"), ("/lib64", "/lib64"), ("/usr", "/usr"), ("/bin", "/bin")],
        binds=[(tmp_dir.name, "/app")],
        unshare_all=True,
    ).execute()

    if result.return_code != 0:
        log.info(f"Compilation failed. GCC exited with error code {result.return_code}.")
        log.info(f"stdout: {result.stdout.decode('utf-8')}")
        log.info(f"stderr: {result.stderr.decode('utf-8')}")
        solution.state = Solution.State.COMPILATION_FAILED
        solution.save()
    else:
        solution.state = Solution.State.COMPILATION_SUCCESSFUL
        solution.save()
        for test_case in solution.problem.test_cases.all():
            test_run = TestRun(
                solution=solution,
                test_case=test_case,
            )
            test_run.save()

        for test_run in solution.test_runs.all():
            test_case = test_run.test_case
            log.debug("Running")
            result = Task(
                ["build/a.out"],
                stdin=test_case.input.encode("utf-8"),
                cwd="/app",
                ro_binds=[("/lib", "/lib"), ("/lib64", "/lib64"), ("/usr", "/usr"), (tmp_dir.name, "/app")],
                unshare_all=True,
                memory_limit=test_case.memory_limit or DEFAULT_MEMORY_LIMIT,
                time_limit=test_case.time_limit
            ).execute()

            test_run.stdout = result.stdout.decode("utf-8")
            test_run.stderr = result.stderr.decode("utf-8")
            test_run.return_code = result.return_code
            test_run.time = result.time.total_seconds()

            if result.timed_out:
                test_run.state = TestRun.State.TIMED_OUT
            elif result.return_code != 0:
                log.info(f"Program exited with error code {result.return_code}.")
                log.info(f"stdout: {result.stdout}")
                test_run.state = TestRun.State.CRASHED
            else:
                log.debug("Validating")
                if test_run.stdout.strip() == test_case.expected_output.strip():
                    test_run.state = TestRun.State.VALID
                else:
                    test_run.state = TestRun.State.INVALID

            test_run.save()

    tmp_dir.cleanup()


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
