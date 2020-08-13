from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_POST
from django.views.generic.edit import FormMixin

from .forms import SendSolutionForm
from .models import Problem, Solution
from .tasks import validate_solution


class ProblemIndexView(generic.ListView):
    template_name = 'judge/index.html'
    context_object_name = 'latest_problem_list'

    def get_queryset(self):
        """Return all published problems."""
        return Problem.objects.order_by('-pub_date')[:]


class ProblemDetailView(FormMixin, generic.DetailView):
    model = Problem
    form_class = SendSolutionForm
    template_name = 'judge/detail.html'


@require_POST
def send_solution(request, problem_id) -> HttpResponse:
    problem = get_object_or_404(Problem, pk=problem_id)

    if not request.FILES.getlist("sources"):
        return HttpResponseBadRequest("No files sent.")

    solution = Solution(problem=problem, user=request.user)

    for file in request.FILES.getlist("sources"):
        solution.save_file(file)

    solution.save()
    validate_solution.delay(solution.id)
    return HttpResponseRedirect(reverse('judge:detail', args=(problem.id,)))
