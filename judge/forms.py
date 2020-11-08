from django import forms

from judge.models import Problem, TestCase, Course


class CourseCreateForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'assigned_users']
        widgets = {
            'assigned_users': forms.CheckboxSelectMultiple()
        }


class CourseUpdateForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'assigned_users']
        widgets = {
            'assigned_users': forms.CheckboxSelectMultiple()
        }


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


class StudentForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['assigned_users']
        widgets = {
            'assigned_users': forms.CheckboxSelectMultiple()
        }
