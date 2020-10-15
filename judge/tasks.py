from logging import Logger
from pathlib import Path
from subprocess import Popen, PIPE
from tempfile import TemporaryDirectory
from typing import Tuple, List, Optional
from dataclasses import dataclass, field

from celery import shared_task
from celery.utils.log import get_task_logger

from .models import Solution, TestRun


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
    stdout, stderr, return_code = Task(
        ["g++", *sources.keys(), "-o", "/app/build/a.out"],
        cwd="/app",
        ro_binds=[("/lib", "/lib"), ("/lib64", "/lib64"), ("/usr", "/usr"), ("/bin", "/bin")],
        binds=[(tmp_dir.name, "/app")],
        unshare_all=True,
    ).execute()

    if return_code != 0:
        log.info(f"Compilation failed. GCC exited with error code {return_code}.")
        log.info(f"stdout: {stdout.decode('utf-8')}")
        log.info(f"stderr: {stderr.decode('utf-8')}")
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
            stdout, stderr, return_code = Task(
                ["build/a.out"],
                stdin=test_case.input.encode("utf-8"),
                cwd="/app",
                ro_binds=[("/lib", "/lib"), ("/lib64", "/lib64"), ("/usr", "/usr"), (tmp_dir.name, "/app")],
                unshare_all=True,
            ).execute()

            test_run.stdout = stdout.decode("utf-8")
            test_run.stderr = stderr.decode("utf-8")
            test_run.return_code = return_code

            if return_code != 0:
                log.info(f"Program exited with error code {return_code}.")
                log.info(f"stdout: {stdout}")
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
class Task:
    argv: List[str]
    stdin: bytes = b""
    cwd: Optional[str] = None
    ro_binds: List[Tuple[str, str]] = field(default_factory=list)
    binds: List[Tuple[str, str]] = field(default_factory=list)
    unshare_all: bool = False

    def execute(self) -> Tuple[bytes, bytes, int]:
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
        print(args)
        child = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = child.communicate(input=self.stdin)

        return stdout, stderr, child.returncode
