from django import forms

from judge.models import Problem, TestCase


class SendSolutionForm(forms.Form):
    sources = forms.FileField(
        label='Send a file',
        widget=forms.ClearableFileInput(attrs={"multiple": True})
    )


class ProblemForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = ['course', 'title', 'description']

    course = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def clean_course(self):
        return self.initial['course']


class TestCaseForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = ['problem', 'input', 'expected_output', 'points', 'memory_limit', 'time_limit']

    problem = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def clean_problem(self):
        return self.initial['problem']
