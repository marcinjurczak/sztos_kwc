from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.decorators.http import require_POST, require_GET
from django.views.generic.edit import FormMixin

from .forms import SendSolutionForm
from .models import Course, Problem, Solution, TestRun, TestCase
from .tasks import validate_solution


class IndexView(generic.TemplateView):
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
    success_url = reverse_lazy('judge:courses')

    def form_valid(self, form):
        obj = form.save(commit=True)
        obj.assigned_users.add(self.request.user)
        obj.save()
        return super().form_valid(form)


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


class ProblemCreate(generic.CreateView):
    template_name = 'judge/add_problem.html'
    model = Problem
    fields = ['course', 'title', 'description']

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
        problem = Problem.objects.get(pk=self.kwargs.get('problem_pk'))
        context['user'] = self.request.user
        context['problem_pk'] = problem.id
        context['course_pk'] = problem.course.id
        context["solution"] = solution
        if solution:
            context["grade"] = solution.get_grade()

        return context


class ProblemGradesView(generic.DetailView):
    model = Problem
    template_name = "judge/problem_grades.html"

    def get_queryset(self):
        return super().get_queryset().filter(course__pk=self.kwargs.get("course_pk"))


class TestCaseCreate(generic.CreateView):
    template_name = 'judge/add_test_case.html'
    model = TestCase
    fields = ['problem', 'input', 'expected_output']

    def get_initial(self):
        problem = get_object_or_404(Problem, id=self.kwargs.get('problem_pk'))
        return {'problem': problem}

    def get_success_url(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_pk'))
        problem = get_object_or_404(Problem, id=self.kwargs.get('problem_pk'))
        return reverse('judge:detail', args=[course.id, problem.id])


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
    return HttpResponseRedirect(reverse('judge:detail', args=(problem.course.id, problem.id,)))


@require_GET
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
