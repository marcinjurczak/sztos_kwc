from logging import Logger
from pathlib import Path
from subprocess import Popen, PIPE, STDOUT
from tempfile import TemporaryDirectory

from celery import shared_task
from celery.utils.log import get_task_logger

from .models import Solution


@shared_task()
def validate_solution(id: int):
    solution = Solution.objects.get(pk=id)
    solution.state = Solution.State.IN_PROGRESS
    solution.save()

    try:
        solution.valid = validate(solution)
    except ValueError:
        solution.valid = False

    if solution.state == Solution.State.IN_PROGRESS:
        solution.state = Solution.State.VALIDATED

    solution.save()


def validate(solution: Solution) -> bool:
    log: Logger = get_task_logger("validate")
    tmp_dir = TemporaryDirectory()
    source_path = Path(tmp_dir.name).joinpath("main.c")
    with source_path.open("wb") as source_file:
        source_file.write(solution.get_source().encode("utf-8"))

    # call gcc
    gcc = Popen(["gcc", "main.c"], text=True, cwd=tmp_dir.name, stdout=PIPE, stderr=STDOUT)
    stdout, _ = gcc.communicate()
    if gcc.returncode != 0:
        log.info(f"Compilation failed. GCC exited with error code {gcc.returncode}.")
        log.info(f"stdout: {stdout}")
        solution.state = Solution.State.COMPILATION_FAILED
    else:
        program = Popen(["./a.out"], text=True, cwd=tmp_dir.name, stdout=PIPE)
        stdout, _ = program.communicate()
        if program.returncode != 0:
            log.info(f"Program exited with error code {program.returncode}.")
            log.info(f"stdout: {stdout}")
            solution.state = Solution.State.CRASHED
        else:
            valid = stdout.strip() == solution.problem.description.strip()
            if not valid:
                print(f"expected: {solution.problem.description}")
                print(f"actual: {stdout}")

            tmp_dir.cleanup()
            return valid

    tmp_dir.cleanup()
    return False
