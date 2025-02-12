from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Appointment
from django.utils.timezone import now

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_appointments(request):
    appointments = Appointment.objects.filter(is_booked=True).order_by('start_time')
    data = [{"id": a.id, "customer_name": a.customer_name, "start_time": a.start_time} for a in appointments]
    return JsonResponse({"appointments": data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_appointments(request):
    """ Gibt nur zukünftige Termine des eingeloggten Benutzers zurück """
    
    # Filtern nach eingeloggtem Nutzer & nur Termine in der Zukunft
    appointments = Appointment.objects.filter(
        customer_name=request.user.username, 
        is_booked=True,
        start_time__gte=now()  # 🔥 Filtern nach Terminen in der Zukunft
    ).order_by('start_time')

    # JSON-Antwort formatieren
    data = [
        {
            "id": a.id,
            "customer_name": a.customer_name,
            "start_time": a.start_time.isoformat(),  # 🔥 ISO-Format für JSON
            "end_time": a.end_time.isoformat(),  # 🔥 Endzeit hinzufügen
        } 
        for a in appointments
    ]
    
    return JsonResponse({"appointments": data}, safe=False)

@api_view(['POST'])  # 🔥 POST-Request zum Löschen eines Termins
@permission_classes([IsAuthenticated])
def delete_appointment(request):
    """
    Löscht einen Termin des eingeloggten Users basierend auf der Termin-ID.
    """
    try:
        appointment_id = request.data.get("appointment_id")
        if not appointment_id:
            return JsonResponse({'error': 'Termin-ID fehlt'}, status=400)

        # 🔍 Prüfe, ob der Termin existiert und zum eingeloggten Nutzer gehört
        appointment = Appointment.objects.filter(id=appointment_id, customer_name=request.user.username).first()

        if not appointment:
            return JsonResponse({'error': 'Termin nicht gefunden oder nicht berechtigt'}, status=403)

        appointment.delete()  # 🗑️ Lösche den Termin
        return JsonResponse({'message': 'Termin erfolgreich gelöscht'}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)