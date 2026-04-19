import json

from ai.db_query import build_patient_context, fetch_patient_list
from ai.llm import generate_discharge_document
from ai.models import CurrentVisit
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods, require_POST

from .models import DischargeDocument, PatientUserLink
from .storage import (
    discharge_pdf_bytes,
    get_presigned_s3_url,
    upload_discharge_pdf_to_s3,
)


def _authorized_patient_id(request):
    """
    Return the PatientID this login is allowed to access documents for.
    Uses PatientUserLink (authoritative), not session['patient_id'], which can be tampered with.
    """
    if not request.user.is_authenticated:
        return None
    if request.session.get("role") != "patient":
        return None
    link = PatientUserLink.objects.filter(user=request.user).first()
    return link.patient_id if link else None


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
            return redirect("signup")

        if role == "patient":
            if not patient_id_raw:
                messages.error(request, "Patient ID is required for patient accounts.")
                return redirect(f"/signup/?role={role}")
            if not patient_id_raw.isdigit():
                messages.error(request, "Patient ID must be a number.")
                return redirect(f"/signup/?role={role}")
            if PatientUserLink.objects.filter(patient_id=int(patient_id_raw)).exists():
                messages.error(
                    request, "That Patient ID is already linked to an account."
                )
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
                    messages.error(
                        request, "This account is not linked to a patient record."
                    )
                    return render(request, "companion/login.html")
            login(request, user)
            request.session["role"] = role  # persist role for the session
            if role == "patient":
                request.session["patient_id"] = link.patient_id
            if role == "nurse":
                return redirect("dashboard_nurse")
            else:
                return redirect("dashboard_patient")
        else:
            messages.error(request, "Invalid login credentials.")

    return render(request, "companion/login.html")


def logout_user(request):
    logout(request)
    return redirect("home")


def dashboard_nurse(request):
    return render(request, "companion/dashboard_nurse.html")


def dashboard_patient(request):
    return render(request, "companion/dashboard_patient.html")


def create_discharge(request):
    """Nurses only — renders the discharge form with the patient dropdown."""
    if request.session.get("role") != "nurse":
        return redirect("home")
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
    if request.session.get("role") != "nurse":
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

        return JsonResponse(
            {
                "patient_id": patient_id,
                "patient_name": f"{context.patient.first_name} {context.patient.last_name}",
                "document": document,
            }
        )

    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    except Exception as exc:
        return JsonResponse({"error": f"Unexpected error: {exc}"}, status=500)


@require_http_methods(["GET", "POST"])
def survey(request):
    if request.method == "POST":
        return redirect("survey_thank_you")
    return render(request, "companion/survey.html")


def survey_thank_you(request):
    return render(request, "companion/survey_thank_you.html")


def patient_info(request):
    patient_id = _authorized_patient_id(request)
    return render(
        request,
        "companion/patient_info.html",
        {
            "patient_id": patient_id,
            "username": request.user.username if request.user.is_authenticated else "",
            "first_name": request.user.first_name
            if request.user.is_authenticated
            else "",
            "last_name": request.user.last_name
            if request.user.is_authenticated
            else "",
            "email": request.user.email if request.user.is_authenticated else "",
            "role": request.session.get("role", ""),
        },
    )


def patient_documents(request):
    """Patient-only view of previously generated discharge documents."""
    patient_id = _authorized_patient_id(request)
    if patient_id is None:
        return redirect("home")

    if request.session.get("patient_id") != patient_id:
        request.session["patient_id"] = patient_id

    documents = DischargeDocument.objects.filter(patient_id=patient_id)
    selected_id_raw = request.GET.get("doc_id")
    selected_document = None

    if documents.exists():
        if selected_id_raw and selected_id_raw.isdigit():
            selected_document = documents.filter(id=int(selected_id_raw)).first()
        if selected_document is None:
            selected_document = documents.first()

    selected_pdf_url = None
    if selected_document and selected_document.s3_object_key:
        try:
            selected_pdf_url = get_presigned_s3_url(
                object_key=selected_document.s3_object_key
            )
        except Exception:
            selected_pdf_url = None

    return render(
        request,
        "companion/patient_documents.html",
        {
            "documents": documents,
            "patient_id": patient_id,
            "selected_document": selected_document,
            "selected_pdf_url": selected_pdf_url,
        },
    )


@xframe_options_sameorigin
def patient_discharge_pdf(request, doc_id):
    """
    Stream PDF only if DischargeDocument.pk belongs to this user's linked PatientID.
    """
    patient_id = _authorized_patient_id(request)
    if patient_id is None:
        raise Http404()
    doc = get_object_or_404(
        DischargeDocument,
        pk=doc_id,
        patient_id=patient_id,
    )
    pdf_bytes = discharge_pdf_bytes(
        s3_object_key=doc.s3_object_key or None,
        document_text=doc.document or "",
    )
    return HttpResponse(
        pdf_bytes,
        content_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="discharge-{doc.id}.pdf"'},
    )


def logout_view(request):
    # Placeholder: for now, just redirect to home page
    return redirect("home")


def settings_view(request):
    return render(request, "companion/settings.html")


def discharge_view(request):
    doc = DischargeDocument.objects.get(id=4)

    return render(
        request,
        "companion/patient_documents.html",
        {"pdf_url": get_presigned_s3_url(object_key=doc.s3_object_key)},
    )
