from django import forms
from .models import UserProfile, EmployerProfile, Gig

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'full_name', 'mobile', 'gender', 'dob', 'college', 
            'about', 'skills', 'intro_video_url', 'profile_picture_url'
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if mobile and not mobile.isdigit():
            raise forms.ValidationError("Mobile number should contain only digits.")
        return mobile

class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = [
            'full_name', 'phone', 'company_name', 'location', 'profile_picture_url'
        ]

class GigForm(forms.ModelForm):
    class Meta:
        model = Gig
        fields = ['title', 'description', 'date', 'time', 'earnings', 'image', 'status']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 5:
            raise forms.ValidationError("Title is too short.")
        return title
