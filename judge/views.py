from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.http import require_POST, require_GET
from django.views.generic.edit import FormMixin

from .forms import SendSolutionForm, ProblemForm, TestCaseForm
from .models import Course, Problem, Solution, TestCase
from .tasks import validate_solution


class IndexView(generic.TemplateView):
    template_name = 'judge/index.html'


@method_decorator(permission_required('judge.view_course'), name='dispatch')
class CourseListView(generic.ListView):
    template_name = 'judge/courses.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        return Course.objects.filter(assigned_users__id=self.request.user.id)


@method_decorator(permission_required('judge.add_course'), name='dispatch')
class CourseCreate(generic.CreateView):
    template_name = 'judge/course_create.html'
    model = Course
    fields = ['name', 'assigned_users']
    success_url = reverse_lazy('judge:courses')

    def get_initial(self):
        user = get_object_or_404(User, id=self.request.user.id)
        return {'assigned_users': user}

    def form_valid(self, form):
        obj = form.save(commit=True)
        obj.assigned_users.add(self.request.user)
        obj.save()
        return super().form_valid(form)


@method_decorator(permission_required('judge.change_course'), name='dispatch')
class CourseUpdate(generic.UpdateView):
    template_name_suffix = '_update'
    model = Course
    fields = ['name', 'assigned_users']
    success_url = reverse_lazy('judge:courses')


@method_decorator(permission_required('judge.delete_course'), name='dispatch')
class CourseDelete(generic.DeleteView):
    template_name_suffix = '_delete'
    model = Course
    success_url = reverse_lazy('judge:courses')


@method_decorator(permission_required('judge.view_problem'), name='dispatch')
class ProblemListView(generic.ListView):
    template_name = 'judge/problems.html'
    context_object_name = 'latest_problem_list'

    def get_queryset(self):
        return Problem.objects.filter(course__id=self.kwargs.get('pk'))

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['pk'] = self.kwargs.get('pk')
        context['course'] = Course.objects.get(id=self.kwargs.get('pk'))
        return context


@method_decorator(permission_required('judge.add_problem'), name='dispatch')
class ProblemCreate(generic.CreateView):
    template_name = 'judge/problem_create.html'
    model = Problem
    form_class = ProblemForm

    def get_initial(self):
        course = get_object_or_404(Course, id=self.kwargs.get('pk'))
        return {'course': course}

    def get_success_url(self):
        course = get_object_or_404(Course, id=self.kwargs.get('pk'))
        return reverse('judge:problems', args=[course.id])

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['course'] = Course.objects.get(id=self.kwargs.get('pk'))
        return context


@method_decorator(permission_required('judge.change_problem'), name='dispatch')
class ProblemUpdate(generic.UpdateView):
    template_name_suffix = '_update'
    model = Problem
    form_class = ProblemForm
    pk_url_kwarg = 'problem_pk'

    def get_initial(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_pk'))
        return {'course': course}

    def get_success_url(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_pk'))
        return reverse('judge:problems', args=[course.id])

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['course'] = Course.objects.get(id=self.kwargs.get('course_pk'))
        return context


@method_decorator(permission_required('judge.delete_problem'), name='dispatch')
class ProblemDelete(generic.DeleteView):
    template_name_suffix = '_delete'
    model = Problem
    pk_url_kwarg = 'problem_pk'

    def get_success_url(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_pk'))
        return reverse('judge:problems', args=[course.id])

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['course'] = Course.objects.get(id=self.kwargs.get('course_pk'))
        return context


@method_decorator(permission_required('judge.view_problem'), name='dispatch')
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
        problem = Problem.objects.get(pk=self.kwargs.get('problem_pk'))
        context['user'] = self.request.user
        context['course'] = problem.course
        context['problem'] = problem
        context["solution"] = solution
        if solution:
            context["grade"] = solution.get_grade()

        return context


@method_decorator(permission_required('judge.view_solution'), name='dispatch')
class SourceCodeView(generic.DetailView):
    model = Solution
    template_name = 'judge/source.html'
    pk_url_kwarg = 'solution_pk'

    def get_queryset(self):
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = Course.objects.get(id=self.kwargs.get('course_pk'))
        context['problem'] = Problem.objects.get(id=self.kwargs.get('problem_pk'))
        return context


@method_decorator(permission_required('judge.view_grades'), name='dispatch')
class ProblemGradesView(generic.DetailView):
    model = Problem
    template_name = "judge/problem_grades.html"

    def get_queryset(self):
        return super().get_queryset().filter(course__pk=self.kwargs.get("course_pk"))

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['course'] = Course.objects.get(id=self.kwargs.get('course_pk'))
        return context


@method_decorator(permission_required('judge.view_testcase'), name='dispatch')
class TestCaseView(generic.ListView):
    template_name = "judge/testcases.html"
    context_object_name = 'test_cases_list'

    def get_queryset(self):
        return TestCase.objects.filter(problem__id=self.kwargs.get('problem_pk'))

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['pk'] = self.kwargs.get('pk')
        context['course'] = Course.objects.get(id=self.kwargs.get('course_pk'))
        context['problem'] = Problem.objects.get(id=self.kwargs.get('problem_pk'))
        return context


@method_decorator(permission_required('judge.add_testcase'), name='dispatch')
class TestCaseCreate(generic.CreateView):
    template_name = 'judge/testcase_create.html'
    model = TestCase
    form_class = TestCaseForm

    def get_initial(self):
        problem = get_object_or_404(Problem, id=self.kwargs.get('problem_pk'))
        return {'problem': problem}

    def get_success_url(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_pk'))
        problem = get_object_or_404(Problem, id=self.kwargs.get('problem_pk'))
        return reverse('judge:test_cases', args=[course.id, problem.id])

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['pk'] = self.kwargs.get('pk')
        context['course'] = Course.objects.get(id=self.kwargs.get('course_pk'))
        context['problem'] = Problem.objects.get(id=self.kwargs.get('problem_pk'))
        return context


@method_decorator(permission_required('judge.change_testcase'), name='dispatch')
class TestCaseUpdate(generic.UpdateView):
    template_name_suffix = '_update'
    model = TestCase
    form_class = TestCaseForm
    pk_url_kwarg = 'test_case_pk'

    def get_initial(self):
        problem = get_object_or_404(Problem, id=self.kwargs.get('problem_pk'))
        return {'problem': problem}

    def get_success_url(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_pk'))
        problem = get_object_or_404(Problem, id=self.kwargs.get('problem_pk'))
        return reverse('judge:test_cases', args=[course.id, problem.id])

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['pk'] = self.kwargs.get('pk')
        context['course'] = Course.objects.get(id=self.kwargs.get('course_pk'))
        context['problem'] = Problem.objects.get(id=self.kwargs.get('problem_pk'))
        return context


@method_decorator(permission_required('judge.delete_testcase'), name='dispatch')
class TestCaseDelete(generic.DeleteView):
    template_name_suffix = '_delete'
    model = TestCase
    pk_url_kwarg = 'test_case_pk'

    def get_success_url(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_pk'))
        problem = get_object_or_404(Problem, id=self.kwargs.get('problem_pk'))
        return reverse('judge:test_cases', args=[course.id, problem.id])

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['pk'] = self.kwargs.get('pk')
        context['course'] = Course.objects.get(id=self.kwargs.get('course_pk'))
        context['problem'] = Problem.objects.get(id=self.kwargs.get('problem_pk'))
        return context


@require_POST
@permission_required('judge.add_solution')
def send_solution(request, problem_id) -> HttpResponse:
    problem = get_object_or_404(Problem, pk=problem_id)

    if not request.FILES.getlist("sources"):
        return HttpResponseBadRequest("No files sent.")

    solution = Solution(problem=problem, user=request.user)

    for file in request.FILES.getlist("sources"):
        solution.save_file(file)

    solution.save()
    validate_solution.delay(solution.id)
    return HttpResponseRedirect(reverse('judge:detail', args=(problem.course.id, problem.id,)))


@require_GET
@permission_required('judge.view_solution')
def download_solution(request, course_pk, problem_pk, solution_pk):
    solution = get_object_or_404(
        Solution,
        pk=solution_pk,
        problem__pk=problem_pk,
        problem__course__pk=course_pk
    )

    data = BytesIO()
    with ZipFile(data, "w", ZIP_DEFLATED) as archive:
        sources = solution.get_sources().items()
        for path, content in sources:
            archive.writestr(path, content)

    return HttpResponse(data.getvalue(), content_type="application/zip")


def handler404(request, exception):
    return render(request, "errors/404.html", status=404)
