from logging import Logger

from celery import shared_task
from celery.utils.log import get_task_logger

from .env.c import CRunner
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
        # TODO: update solution state


def validate(solution: Solution) -> None:
    log: Logger = get_task_logger(__name__)
    env = CRunner()

    # call gcc
    log.debug("Compiling")
    result = env.compile(solution.get_sources())

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
            result = env.run(
                stdin=test_case.input.encode("utf-8"),
                memory_limit=test_case.memory_limit,
                time_limit=test_case.time_limit,
            )

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

    env.clean_up()
