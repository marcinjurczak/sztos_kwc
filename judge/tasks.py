from celery import shared_task

from .models import Solution


@shared_task()
def validate_solution(id: int):
    solution = Solution.objects.get(pk=id)
    solution.state = Solution.State.IN_PROGRESS
    solution.save()
    problem = solution.problem

    try:
        content = list(solution.get_sources().keys())[0]
        solution.valid = int(len(content)) == len(problem.description)
    except ValueError:
        solution.valid = False

    solution.state = Solution.State.VALIDATED
    solution.save()
