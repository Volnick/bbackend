from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Appointment
from django.utils.timezone import now
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import requests

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
            is_paid = data.get('is_paid', False)  # Standardmäßig False, falls nicht übergeben
            price = data.get('price', 0.0)
            transaction_id = data.get('transaction_id', None)  # Kann None sein
            payment_method = data.get('payment_method', 'Unbekannt')  # Falls nicht gesetzt, 'Unbekannt'

            print("📌 Empfangene Daten:", data)  # Debugging: Zeigt die erhaltenen Daten an

            # Prüfe, ob der Termin bereits gebucht ist
            if Appointment.objects.filter(start_time=start_time, end_time=end_time, is_booked=True).exists():
                return JsonResponse({'error': 'Der Termin ist bereits gebucht'}, status=400)

            # Neuen Termin anlegen mit Zahlungsinformationen
            appointment = Appointment.objects.create(
                start_time=start_time,
                end_time=end_time,
                customer_name=customer_name,
                is_booked=True,
                is_paid=is_paid,
                price=price,
                transaction_id=transaction_id,
                payment_method=payment_method
            )

            return JsonResponse({
                'message': 'Appointment booked successfully',
                'start_time': start_time,
                'end_time': end_time,
                'customer_name': customer_name,
                'appointment_id': appointment.id,
                'is_paid': appointment.is_paid,
                'price': appointment.price,
                'transaction_id': appointment.transaction_id,
                'payment_method': appointment.payment_method
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

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
            "is_paid": a.is_paid,
            "payment_method": a.payment_method,
            "price" : a.price,
            "transaction_id": a.transaction_id

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
    
# PayPal API Credentials aus den Django-Settings
PAYPAL_CLIENT_ID = settings.PAYPAL_CLIENT_ID
PAYPAL_SECRET = settings.PAYPAL_SECRET
PAYPAL_API_URL = "https://api-m.sandbox.paypal.com"  # Falls live: "https://api-m.paypal.com"

def get_paypal_access_token():
    """Holt ein Access Token von PayPal für API-Zugriff"""
    url = f"{PAYPAL_API_URL}/v1/oauth2/token"
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en_US",
    }
    auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, auth=auth, data=data)
    response_data = response.json()

    return response_data.get("access_token")


@csrf_exempt
def refund_payment(request):
    """Handhabt die Rückerstattung einer PayPal-Zahlung"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            transaction_id = data.get("transaction_id")

            if not transaction_id:
                return JsonResponse({"error": "Fehlende Transaction ID"}, status=400)

            access_token = get_paypal_access_token()
            if not access_token:
                return JsonResponse({"error": "PayPal Authentifizierung fehlgeschlagen"}, status=500)

            # 🔍 Termin abrufen und tatsächlichen Betrag holen
            appointment = Appointment.objects.filter(transaction_id=transaction_id).first()
            if not appointment:
                return JsonResponse({"error": "Kein Termin mit dieser Transaction ID gefunden"}, status=404)

            # **Sicherstellen, dass ein gültiger Preis vorhanden ist**
            refund_amount = float(appointment.price) if appointment.price is not None else 0.0
            if refund_amount <= 0:
                return JsonResponse({"error": "Ungültige Rückerstattungssumme"}, status=400)

            print(f"🔄 Rückerstattung für {refund_amount} EUR wird angefordert.")

            refund_url = f"{PAYPAL_API_URL}/v2/payments/captures/{transaction_id}/refund"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }
            refund_payload = {"amount": {"value": f"{refund_amount:.2f}", "currency_code": "EUR"}}

            print("🔄 PayPal Refund Request:", refund_payload)

            refund_response = requests.post(refund_url, headers=headers, json=refund_payload)
            refund_data = refund_response.json()

            print("💰 PayPal Refund Response:", refund_data)

            if refund_response.status_code == 201:
                # Termin in DB als erstattet markieren
                appointment.is_paid = False
                appointment.save()

                return JsonResponse({"success": True, "message": "Rückerstattung erfolgreich"})
            else:
                return JsonResponse({"error": "PayPal-Rückerstattung fehlgeschlagen", "details": refund_data}, status=400)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

