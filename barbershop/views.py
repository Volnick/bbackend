from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Appointment
import json

def available_appointments(request):
    appointments = Appointment.objects.filter(is_booked=True)
    data = [
        {
            'start_time': appointment.start_time,
            'end_time': appointment.end_time,
        }
        for appointment in appointments
        
    ]
    return JsonResponse(data, safe=False)

@csrf_exempt  # Deaktiviert CSRF-Überprüfung für einfache Tests
def book_appointment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_name = data.get('customer_name')
            start_time = data.get('start_time')
            end_time = data.get('end_time')

            # Prüfe, ob der Termin verfügbar ist
            if Appointment.objects.filter(start_time=start_time, end_time=end_time, is_booked=True).exists():
                return JsonResponse({'error': 'Der Termin ist bereits gebucht'}, status=400)

            # Neuen Termin anlegen
            appointment = Appointment.objects.create(
                start_time=start_time,
                end_time=end_time,
                customer_name=customer_name,
                is_booked=True,
            )

            return JsonResponse({'message': 'Appointment booked successfully'}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)