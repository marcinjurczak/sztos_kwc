from django import forms


class SendSolutionForm(forms.Form):
    sources = forms.FileField(
        label='Send a file',
        widget=forms.ClearableFileInput(attrs={"multiple": True})
    )
