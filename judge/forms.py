from django import forms


class SendSolutionForm(forms.Form):
    source = forms.FileField(label='Send a file')
