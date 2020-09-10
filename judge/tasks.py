from io import StringIO
from logging import Logger
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT
from tempfile import TemporaryDirectory

from celery import shared_task
from celery.utils.log import get_task_logger

from .models import Solution, TestCase


@shared_task()
def validate_solution(id: int):
    solution = Solution.objects.get(pk=id)
    solution.state = Solution.State.IN_PROGRESS
    solution.save()

    try:
        solution.valid = validate(solution)
    except Exception as e:
        get_task_logger(__name__).error("An exception was thrown during validation.", e)
        solution.valid = False

    if solution.state == Solution.State.IN_PROGRESS:
        solution.state = Solution.State.VALIDATED

    solution.save()


def validate(solution: Solution) -> bool:
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
    else:
        valid = True
        for test_case in solution.problem.test_cases.all():
            program = Popen(["./a.out"], text=True, cwd=tmp_dir.name, stdin=PIPE, stdout=PIPE)
            log.debug("Running")
            stdout, _ = program.communicate(input=test_case.input)
            if program.returncode != 0:
                log.info(f"Program exited with error code {program.returncode}.")
                log.info(f"stdout: {stdout}")
                solution.state = Solution.State.CRASHED
            else:
                log.debug("Validating")
                if valid:
                    valid = stdout.strip() == test_case.expected_output.strip()

        tmp_dir.cleanup()
        return valid

    tmp_dir.cleanup()
    return False
