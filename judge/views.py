from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.edit import FormMixin
from django.urls import reverse
from django.views import generic

from .models import Problem, Solution
from .tasks import validate_solution
from .forms import SendSolutionForm


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


class ResultsView(generic.DetailView):  # name?
    model = Problem
    template_name = 'judge/results.html'


def send_solution(request, problem_id):
    if request.method == 'POST':
        problem = get_object_or_404(Problem, pk=problem_id)
        s = Solution(problem=problem)
        s.save_file(request.FILES["source"])
        s.save()
        validate_solution.delay(s.id)
        return HttpResponseRedirect(reverse('judge:results', args=(problem.id,)))
