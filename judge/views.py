from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render, get_list_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import generic
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.views.generic.edit import FormMixin
from django.contrib import messages

from .forms import SendSolutionForm
from .models import Course, Problem, Solution, TestRun
from .tasks import validate_solution


class IndexView(TemplateView):
    template_name = 'judge/index.html'


class CourseListView(generic.ListView):
    template_name = 'judge/courses.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        return Course.objects.filter(assigned_users__id=self.request.user.id)


class CourseCreate(generic.CreateView):
    template_name = 'judge/add_course.html'
    model = Course
    fields = ['name']
    success_url = '/courses/'

    def form_valid(self, form):
        obj = form.save(commit=True)
        obj.assigned_users.add(self.request.user)
        obj.save()
        return super(CourseCreate, self).form_valid(form)

    def get_initial(self):
        user = get_object_or_404(User, id=self.request.user.id)
        return {'assigned_users': user}


class ProblemListView(generic.ListView):
    template_name = 'judge/problems.html'
    context_object_name = 'latest_problem_list'

    def get_queryset(self):
        return Problem.objects.filter(course__id=self.kwargs.get('pk'))

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context['pk'] = self.kwargs.get('pk')
        context['course'] = Course.objects.get(id=self.kwargs.get('pk'))
        return context


class ProblemCreate(generic.CreateView):
    template_name = 'judge/add_problem.html'
    model = Problem
    fields = ['course', 'title', 'description']

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.pub_date = timezone.now()
        obj.save()
        return super(ProblemCreate, self).form_valid(form)

    def get_initial(self):
        course = get_object_or_404(Course, id=self.kwargs.get('pk'))
        return {'course': course}

    def get_success_url(self):
        course = get_object_or_404(Course, id=self.kwargs.get('pk'))
        return reverse('judge:problems', args=[course.id])


class ProblemDetailView(FormMixin, generic.DetailView):
    model = Problem
    form_class = SendSolutionForm
    template_name = 'judge/detail.html'
    pk_url_kwarg = 'problem_pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        solution = Solution.objects.filter(
            user__id=self.request.user.id,
            problem__pk=self.kwargs.get('problem_pk')
        ).last()
        context['user'] = self.request.user
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
