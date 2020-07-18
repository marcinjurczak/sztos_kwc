from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic

from .models import Question, Solution


class IndexView(generic.ListView):
    template_name = 'judge/index.html'
    context_object_name = 'latest_question_list'

    def get_queryset(self):
        """Return all published questions."""
        return Question.objects.order_by('-pub_date')[:]


class DetailView(generic.DetailView):
    model = Question
    template_name = 'judge/detail.html'


class ResultsView(generic.DetailView):
    model = Question
    template_name = 'judge/results.html'


def send(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    try:
        sent_solution = question.solution_set.get(pk=request.POST['solution'])
    except (KeyError, Solution.DoesNotExist):
        return render(request, 'judge/detail.html', {
            'question': question,
            'error_message': "You didn't send a solution.",
        })
    else:
        sent_solution.votes += 1
        sent_solution.save()
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('judge:results', args=(question.id,)))

