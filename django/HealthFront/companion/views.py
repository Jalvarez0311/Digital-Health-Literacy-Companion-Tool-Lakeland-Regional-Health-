import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from ai.db_query import build_patient_context, fetch_patient_list
from ai.llm import generate_discharge_document
from ai.models import CurrentVisit


def home(request):
    return render(request, "companion/index.html")

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
        return redirect(f"/login/?role={role}")

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
    """Renders the discharge form — populates the patient dropdown from Supabase."""
    try:
        patients = fetch_patient_list()
    except Exception:
        patients = []
    return render(request, "companion/discharge_summary.html", {"patients": patients})


@require_POST
def generate_discharge(request):
    """
    POST  /discharge/generate/
    Body (JSON or form): { "patient_id": <int> }

    Queries the patient's full medical history from Supabase, sends it to the
    LLM, and returns the generated discharge document as JSON.
    """
    try:
        patient_id = int(request.POST.get("patient_id", 0))
        if not patient_id:
            return JsonResponse({"error": "patient_id is required."}, status=400)

        # Split comma-separated lists entered by the nurse
        def split_list(raw: str) -> list:
            return [s.strip() for s in raw.split(",") if s.strip()] if raw else []

        current_visit = CurrentVisit(
            visit_date=request.POST.get("visit_date"),
            reason_for_visit=request.POST.get("reason_for_visit", ""),
            current_diagnoses=split_list(request.POST.get("current_diagnoses", "")),
            current_medications=split_list(request.POST.get("current_medications", "")),
            notes=request.POST.get("notes") or None,
        )

        context = build_patient_context(patient_id, current_visit)
        document = generate_discharge_document(context)

        return JsonResponse({
            "patient_id": patient_id,
            "patient_name": f"{context.patient.first_name} {context.patient.last_name}",
            "document": document,
        })

    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except Exception as exc:
        return JsonResponse({"error": f"Unexpected error: {exc}"}, status=500)

def survey(request):
    return render(request, "companion/survey.html")

def patient_info(request):
    return render(request, "companion/patient_info.html")

def logout_view(request):
    # Placeholder: for now, just redirect to home page
    return redirect('home')