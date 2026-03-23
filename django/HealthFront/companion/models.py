from django.db import models
from django.contrib.auth.models import User


class PatientUserLink(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient_link")
    patient_id = models.IntegerField(unique=True)

    def __str__(self):
        return f"{self.user.username} -> Patient {self.patient_id}"


class DischargeDocument(models.Model):
    patient_id = models.IntegerField(db_index=True)
    patient_name = models.CharField(max_length=255)
    document = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Discharge doc for {self.patient_name} ({self.patient_id})"
