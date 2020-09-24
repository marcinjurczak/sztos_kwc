from logging import Logger
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT
from tempfile import TemporaryDirectory

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
    sources = solution.get_sources()
    for name, content in sources.items():
        with source_path.joinpath(name).open("wb") as source_file:
            source_file.write(content.encode("utf-8"))

    # call gcc
    log.debug("Compiling")
    gcc = Popen(["gcc", *sources.keys()], text=True, cwd=tmp_dir.name, stdout=PIPE, stderr=STDOUT)
    stdout, _ = gcc.communicate()
    if gcc.returncode != 0:
        log.info(f"Compilation failed. GCC exited with error code {gcc.returncode}.")
        log.info(f"stdout: {stdout}")
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
            program = Popen(["./a.out"], text=True, cwd=tmp_dir.name, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            log.debug("Running")
            stdout, stderr = program.communicate(input=test_case.input)

            test_run.stdout = stdout
            test_run.stderr = stderr
            test_run.return_code = program.returncode

            if program.returncode != 0:
                log.info(f"Program exited with error code {program.returncode}.")
                log.info(f"stdout: {stdout}")
                test_run.state = TestRun.State.CRASHED
            else:
                log.debug("Validating")
                if stdout.strip() == test_case.expected_output.strip():
                    test_run.state = TestRun.State.VALID
                else:
                    test_run.state = TestRun.State.INVALID

            test_run.save()

    tmp_dir.cleanup()
