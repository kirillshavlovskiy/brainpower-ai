from django import forms
from .models import Course, Code, AI_Code


class ContentForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'objective', 'description']


class CodeForm(forms.ModelForm):
    class Meta:
        model = Code
        fields = ['code']



class GeneratedContentForm(forms.Form):
    prompts = forms.CharField(widget=forms.Textarea, help_text="Enter each prompt on a new line.")

    # Add other fields for parameters as needed
