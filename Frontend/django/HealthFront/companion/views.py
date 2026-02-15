from django.shortcuts import render
from django.shortcuts import redirect

def home(request):
    return render(request, "companion/index.html")

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

def signup_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('signup')

        # Create user in database
        user = User.objects.create_user(username=username, password=password)
        user.save()
        messages.success(request, "Account created! Please log in.")
        return redirect(f"{redirect('login')}?role={role}")

    return render(request, "companion/signup.html")


def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if role == "nurse":
                return redirect('dashboard_nurse')
            else:
                return redirect('dashboard_patient')
        else:
            messages.error(request, "Invalid login credentials.")

    return render(request, "companion/login.html")
    

def logout_user(request):
    logout(request)
    return redirect('home')


def dashboard_nurse(request):
    return render(request, "companion/dashboard_nurse.html")

def dashboard_patient(request):
    return render(request, "companion/dashboard_patient.html")

def create_discharge(request):
    return render(request, "companion/discharge_summary.html")

def survey(request):
    return render(request, "companion/survey.html")

def patient_info(request):
    return render(request, "companion/patient_info.html")

def logout_view(request):
    # Placeholder: for now, just redirect to home page
    return redirect('home')