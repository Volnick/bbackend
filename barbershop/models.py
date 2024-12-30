from django.db import models

# Create your models here.
class Appointment(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    customer_name = models.CharField(max_length=100)

    def __str__(self):
        return f"Appointment from {self.start_time} to {self.end_time}"