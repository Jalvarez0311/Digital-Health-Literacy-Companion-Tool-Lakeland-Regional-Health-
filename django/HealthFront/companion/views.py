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
from .models import DischargeDocument, PatientUserLink
from .storage import upload_discharge_pdf_to_s3


def home(request):
    return render(request, "companion/index.html")

def signup_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role")
        patient_id_raw = (request.POST.get("patient_id") or "").strip()

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('signup')

        if role == "patient":
            if not patient_id_raw:
                messages.error(request, "Patient ID is required for patient accounts.")
                return redirect(f"/signup/?role={role}")
            if not patient_id_raw.isdigit():
                messages.error(request, "Patient ID must be a number.")
                return redirect(f"/signup/?role={role}")
            if PatientUserLink.objects.filter(patient_id=int(patient_id_raw)).exists():
                messages.error(request, "That Patient ID is already linked to an account.")
                return redirect(f"/signup/?role={role}")

        # Create user in database
        user = User.objects.create_user(username=username, password=password)
        user.save()
        if role == "patient":
            PatientUserLink.objects.create(user=user, patient_id=int(patient_id_raw))
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
            if role == "patient":
                link = PatientUserLink.objects.filter(user=user).first()
                if link is None:
                    messages.error(request, "This account is not linked to a patient record.")
                    return render(request, "companion/login.html")
            login(request, user)
            request.session['role'] = role  # persist role for the session
            if role == "patient":
                request.session['patient_id'] = link.patient_id
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
    """Nurses only — renders the discharge form with the patient dropdown."""
    if request.session.get('role') != 'nurse':
        return redirect('home')
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
    if request.session.get('role') != 'nurse':
        return JsonResponse({"error": "Access denied."}, status=403)

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
        saved_doc = DischargeDocument.objects.create(
            patient_id=patient_id,
            patient_name=f"{context.patient.first_name} {context.patient.last_name}",
            document=document,
            created_by=request.user if request.user.is_authenticated else None,
        )

        object_key, object_url = upload_discharge_pdf_to_s3(
            patient_id=patient_id,
            document_id=saved_doc.id,
            document_text=document,
        )
        saved_doc.s3_object_key = object_key
        saved_doc.s3_object_url = object_url
        saved_doc.save(update_fields=["s3_object_key", "s3_object_url"])

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


def patient_documents(request):
    """Patient-only view of previously generated discharge documents."""
    if request.session.get('role') != 'patient':
        return redirect('home')

    patient_id = request.session.get('patient_id')
    if not patient_id:
        messages.error(request, "No patient record linked to this account.")
        return redirect('dashboard_patient')

    documents = DischargeDocument.objects.filter(patient_id=patient_id)
    selected_id_raw = request.GET.get("doc_id")
    selected_document = None

    if documents.exists():
        if selected_id_raw and selected_id_raw.isdigit():
            selected_document = documents.filter(id=int(selected_id_raw)).first()
        if selected_document is None:
            selected_document = documents.first()

    return render(
        request,
        "companion/patient_documents.html",
        {
            "documents": documents,
            "patient_id": patient_id,
            "selected_document": selected_document,
        },
    )

def logout_view(request):
    # Placeholder: for now, just redirect to home page
    return redirect('home')