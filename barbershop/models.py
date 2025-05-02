from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class Appointment(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    customer_name = models.CharField(max_length=100)
    
    # Optionaler Bezug auf eingeloggten Benutzer
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointments",
        null=True,
        blank=True
    )

    is_paid = models.BooleanField(default=False)  # Zahlung erfolgt?
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    services = models.JSONField(default=list)  # Liste der gewählten Services
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Appointment from {self.start_time} to {self.end_time} - Booked by {self.user.username if self.user else 'Guest'}"


class CustomUser(AbstractUser):
    # E-Mail als eindeutiger Login-Identifier
    email = models.EmailField(unique=True)

    # Pflichtfelder für jeden User
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    telefonnummer = models.CharField(max_length=20, unique=True)

    # Authentifizierung über E-Mail statt Username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'telefonnummer']

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"

class Teilnahme(models.Model):
    email = models.EmailField(unique=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email