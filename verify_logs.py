import os
import django
import json
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beermoney.settings')
django.setup()

from core.models import EmployerProfile, Gig, Application, UserProfile, AdminLog
from core.views.employer import post_gig, employer_manage_gig, manage_application

def setup_request(method, path, data, session_email):
    factory = RequestFactory()
    if method == 'POST':
        request = factory.post(path, data=json.dumps(data), content_type='application/json')
    else:
        request = factory.get(path)
    
    # Add session
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session['user_email'] = session_email
    request.session.save()
    return request

def test_logs():
    print("Starting verification of admin logs...")
    
    # Setup test data
    employer_email = "test_employer@example.com"
    student_email = "test_student@example.com"
    
    # Cleanup previous test data if any
    EmployerProfile.objects.filter(email=employer_email).delete()
    UserProfile.objects.filter(email=student_email).delete()
    AdminLog.objects.filter(admin_email=employer_email).delete()
    
    employer = EmployerProfile.objects.create(
        email=employer_email,
        full_name="Test Employer",
        phone="1234567890",
        company_name="Test Co",
        location="Test City"
    )
    
    student = UserProfile.objects.create(
        email=student_email,
        full_name="Test Student",
        mobile="9876543210",
        gender="male",
        dob="2000-01-01",
        college="Test College"
    )
    
    # 1. Test POST_GIG
    print("Testing POST_GIG...")
    post_data = {
        'title': 'Test Log Gig',
        'description': 'This is a test gig description.',
        'date': '2026-03-20',
        'time': '10:00:00',
        'earnings': '500'
    }
    request = setup_request('POST', '/api/post-gig/', post_data, employer_email)
    response = post_gig(request)
    print(f"Post Gig Response: {response.content.decode()}")
    
    gig = None
    try:
        gig = Gig.objects.get(title='Test Log Gig', employer=employer)
        log = AdminLog.objects.filter(action='POST_GIG', target='Test Log Gig').first()
        if log:
            print(f"SUCCESS: POST_GIG log found: {log}")
        else:
            print("FAILED: POST_GIG log NOT found.")
    except Gig.DoesNotExist:
        print("FAILED: Gig was not created.")

    if gig:
        # 2. Test CLOSE_GIG
        print("Testing CLOSE_GIG...")
        manage_data = {
            'gig_id': gig.id,
            'action': 'CLOSE'
        }
        request = setup_request('POST', '/api/employer/manage-gig/', manage_data, employer_email)
        response = employer_manage_gig(request)
        print(f"Manage Gig Response: {response.content.decode()}")
        
        log = AdminLog.objects.filter(action='CLOSE_GIG', target='Test Log Gig').first()
        if log:
            print(f"SUCCESS: CLOSE_GIG log found: {log}")
        else:
            print("FAILED: CLOSE_GIG log NOT found.")

        # 3. Test HIRE_STUDENT
        print("Testing HIRE_STUDENT...")
        application = Application.objects.create(gig=gig, student=student)
        app_data = {
            'app_id': application.id,
            'action': 'ACCEPT'
        }
        request = setup_request('POST', '/api/employer/manage-application/', app_data, employer_email)
        response = manage_application(request)
        print(f"Manage Application Response: {response.content.decode()}")
        
        log = AdminLog.objects.filter(action='HIRE_STUDENT', target=student_email).first()
        if log:
            print(f"SUCCESS: HIRE_STUDENT log found: {log}")
        else:
            print("FAILED: HIRE_STUDENT log NOT found.")

    # Cleanup
    # gig.delete()
    # employer.delete()
    # student.delete()

if __name__ == "__main__":
    test_logs()
