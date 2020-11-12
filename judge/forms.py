from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from judge.models import Problem, TestCase, Course, Solution


class CourseCreateForm(forms.ModelForm):
    student_list = forms.CharField(widget=forms.Textarea(),
                                   help_text='Insert users next to each other or line by line')

    class Meta:
        model = Course
        fields = ['name']

    def clean(self):
        super().clean()
        users = self.cleaned_data['student_list'].split()
        all_users = list(User.objects.all().values_list('username', flat=True))
        unknown_users = []

        for user in users:
            if user not in all_users:
                unknown_users.append(user)

        if unknown_users:
            self._errors['student_list'] = self.error_class([
                'No such users exist:'])
            for user in unknown_users:
                self.add_error('student_list', user)
        return self.cleaned_data


class CourseUpdateForm(forms.ModelForm):
    student_list = forms.CharField(widget=forms.Textarea(),
                                   help_text='Insert users next to each other or line by line')

    class Meta:
        model = Course
        fields = ['name']

    def clean(self):
        super().clean()
        users = self.cleaned_data['student_list'].split()
        all_users = list(User.objects.all().values_list('username', flat=True))
        unknown_users = []

        for user in users:
            if user not in all_users:
                unknown_users.append(user)

        if unknown_users:
            self._errors['student_list'] = self.error_class([
                'No such users exist:'])
            for user in unknown_users:
                self.add_error('student_list', user)
        return self.cleaned_data


class SendSolutionForm(forms.Form):
    sources = forms.FileField(
        label='Send a file',
        widget=forms.ClearableFileInput(attrs={"multiple": True})
    )
    language = forms.ChoiceField(choices=Solution.Language.choices)


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


class StudentForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['assigned_users']
        widgets = {
            'assigned_users': forms.CheckboxSelectMultiple()
        }
