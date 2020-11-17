from django import forms
from django.contrib.auth.models import User

from judge.models import Problem, TestCase, Course, Solution


class CourseCreateUpdateForm(forms.ModelForm):
    student_list = forms.CharField(widget=forms.Textarea(),
                                   help_text='Insert users next to each other or line by line')

    class Meta:
        model = Course
        fields = ['name']

    def clean(self):
        super().clean()
        user_list = self.cleaned_data['student_list'].split()
        users = User.objects.filter(username__in=user_list)
        users_set = set(user.username for user in users)
        not_in_db = set(user_list) - users_set

        if not_in_db:
            self._errors['student_list'] = self.error_class([
                'No such users exist:'])
            for user in not_in_db:
                self.add_error('student_list', user)
        return self.cleaned_data


class CourseAddStudentsForm(forms.ModelForm):
    student_list = forms.CharField(widget=forms.Textarea(),
                                   help_text='Insert users next to each other or line by line')

    class Meta:
        model = Course
        fields = []

    def clean(self):
        super().clean()
        user_list = self.cleaned_data['student_list'].split()
        users = User.objects.filter(username__in=user_list)
        users_set = set(user.username for user in users)
        not_in_db = set(user_list) - users_set

        if not_in_db:
            self._errors['student_list'] = self.error_class([
                'No such users exist:'])
            for user in not_in_db:
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
