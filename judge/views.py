from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.views.generic.edit import FormMixin

from .forms import SendSolutionForm
from .models import Problem, Solution, TestRun
from .tasks import validate_solution


class IndexView(TemplateView):
    template_name = 'judge/index.html'


class ProblemListView(generic.ListView):
    template_name = 'judge/problems.html'
    context_object_name = 'latest_problem_list'

    def get_queryset(self):
        """Return all published problems."""
        return Problem.objects.order_by('-pub_date')[:]


class ProblemDetailView(FormMixin, generic.DetailView):
    model = Problem
    form_class = SendSolutionForm
    template_name = 'judge/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        solution = Solution.objects.filter(
            user__id=self.request.user.id,
            problem__pk=self.kwargs.get('pk')
        ).last()
        context['user'] = self.request.user.is_authenticated
        context["solution"] = solution
        if solution:
            if solution.test_runs.count() > 0:
                context["grade"] = solution.test_runs.filter(
                    state=TestRun.State.VALID).count() / solution.test_runs.count()
            else:
                context["grade"] = 0
        return context


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
