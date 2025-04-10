from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Appointment(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    customer_name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointments", null=True, blank=True)
    is_paid = models.BooleanField(default=False) #Zahlung erfolgt?
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    services = models.JSONField(default=list) 
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"Appointment from {self.start_time} to {self.end_time} - Booked by {self.user.username if self.user else 'Guest'}"
