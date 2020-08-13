from pathlib import Path
from subprocess import Popen, PIPE
from tempfile import TemporaryDirectory

from celery import shared_task

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

    solution.state = Solution.State.VALIDATED
    solution.save()


def validate(solution: Solution) -> bool:
    tmp_dir = TemporaryDirectory()
    source_path = Path(tmp_dir.name).joinpath("main.c")
    with source_path.open("wb") as source_file:
        source_file.write(solution.get_source().encode("utf-8"))

    # call gcc
    gcc = Popen(["gcc", "main.c"], cwd=tmp_dir.name)
    gcc.wait()
    # call resulting binary
    program = Popen(["./a.out"], text=True, cwd=tmp_dir.name, stdout=PIPE)
    (stdout, _) = program.communicate()
    print(f"stdout: \n{stdout}")

    tmp_dir.cleanup()

    valid = stdout.strip() == solution.problem.description.strip()
    if not valid:
        print(f"expected: {solution.problem.description}")
        print(f"actual: {stdout}")
    return valid
