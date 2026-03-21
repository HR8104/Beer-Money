from django import forms
from datetime import datetime
from django.utils import timezone
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
        if mobile:
            if not mobile.isdigit():
                raise forms.ValidationError("Mobile number should contain only digits.")
            if len(mobile) != 10:
                raise forms.ValidationError("Mobile number must be exactly 10 digits.")
        return mobile

class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = [
            'full_name', 'phone', 'company_name', 'location', 'profile_picture_url'
        ]

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            if not phone.isdigit():
                raise forms.ValidationError("Phone number should contain only digits.")
            if len(phone) != 10:
                raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone

class GigForm(forms.ModelForm):
    class Meta:
        model = Gig
        fields = ['title', 'description', 'date', 'start_time', 'end_time', 'earnings', 'image', 'status']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 5:
            raise forms.ValidationError("Title is too short.")
        return title

    def clean(self):
        cleaned_data = super().clean()
        date_val = cleaned_data.get("date")
        start_time_val = cleaned_data.get("start_time")
        end_time_val = cleaned_data.get("end_time")

        # Basic timing checks
        if date_val and start_time_val:
            gig_dt = timezone.make_aware(
                datetime.combine(date_val, start_time_val),
                timezone.get_current_timezone(),
            )
            if gig_dt <= timezone.localtime():
                raise forms.ValidationError("Gig start time must be in the future.")
        
        if start_time_val and end_time_val:
            if end_time_val <= start_time_val:
                raise forms.ValidationError("End time must be after start time.")

        return cleaned_data
