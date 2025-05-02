import datetime
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from .models import Appointment
from django.utils.timezone import now
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
import requests
from django.core.mail import send_mail
import json
from rest_framework import status
from rest_framework.response import Response


from amazon_paapi import AmazonApi
from django.http import JsonResponse

from .models import Appointment
from .serializers import AppointmentSerializer

from .models import Teilnahme
from .serializers import TeilnahmeSerializer

from .utils import broadcast_appointment_update

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True  # ➕ wichtig für PATCH
        return super().update(request, *args, **kwargs)

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
            services = data.get('services', [])

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
                payment_method=payment_method,
                services = services
            )

            broadcast_appointment_update({
                "action": "created",
                "appointment_id": appointment.id,
                "start_time": start_time,
                "end_time": end_time,
                "customer_name": customer_name,
                "services": services
            })

            return JsonResponse({
                'message': 'Appointment booked successfully',
                'start_time': start_time,
                'end_time': end_time,
                'customer_name': customer_name,
                'appointment_id': appointment.id,
                'is_paid': appointment.is_paid,
                'price': appointment.price,
                'transaction_id': appointment.transaction_id,
                'payment_method': appointment.payment_method,
                'services': appointment.services
            }, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_appointments(request):
    appointments = Appointment.objects.filter(is_booked=True).order_by('start_time')
    data = [{
                "id": a.id,
                "customer_name": a.customer_name,
                "start_time": a.start_time,
                "end_time": a.end_time,
                "is_paid": a.is_paid,
                "price": float(a.price) if a.price else 0.0,
                "services": a.services
            } 
            for a in appointments]
    print(data)
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

        # 🔔 WebSocket-Broadcast nach dem Löschen
        broadcast_appointment_update({
            "action": "deleted",
            "appointment_id": appointment_id
        })

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

def activate_user(request, uid, token):
    response = requests.post('https://salongstudio.de/auth/users/activation/', data={'uid': uid, 'token': token})
    if response.status_code == 204:
        return redirect('https://salongstudio.de/login')
    else:
        return redirect('/error/')  # Fehler bei der Aktivierung
    

@csrf_exempt  # Optional, wenn du keine CSRF-Prüfung machen möchtest
def send_booking_email(request):
    print("send_booking_email aufgerufen")
    if request.method == 'POST':
        try:
            # JSON-Daten aus der Anfrage extrahieren
            data = json.loads(request.body)
            print("Test", data)
            # Extrahiere die Buchungsdetails
            customer_name = data.get('customer_name')
            customer_email = data.get('customer_email')
            start_time = data.get('start_time')
            end_time = data.get('end_time')
            price = data.get('price', 0.0)
            services = data.get('selectedServices', [])

                        # Überprüfe, ob die Zeiten gültig sind
            #if not validate_time_format(start_time):
            #    return JsonResponse({'error': 'Ungültiges Startdatum'}, status=400)

            #if not validate_time_format(end_time):
            #    return JsonResponse({'error': 'Ungültiges Enddatum'}, status=400)

            # Gib die formatierten Zeiten aus
            #print(" halloasdasdasd")
            #print(f"Startzeit: {format_time(start_time)}")
            formatted_date = format_date(start_time)
            formatted_start_time = format_time(start_time)  # Erwartet '08:30'
            formatted_end_time = format_time(end_time) 
            print(start_time)
            # ➡️ Und die Services auflisten:
            service_list = "".join(
                [f"<li>{service['name']} - {service['duration']} Min - {service['cost']} €</li>" for service in services]
            )

            email_subject = 'Buchungsbestätigung'
            email_message = f"""
                <h2>Hallo {customer_name},</h2>
                <p>Vielen Dank für deine Buchung! Hier sind deine Buchungsdetails:</p>
                <ul>Datum: {formatted_date}</ul>
                <ul>Start: {formatted_start_time}</ul>
                <ul>Ende: {formatted_end_time}</ul>
                <p><strong>Ausgewählte Services:</strong></p>
                <ul>{service_list}</ul>
                <p><strong>Gesamtpreis:</strong> {price} €</p>
                <p>Wir freuen uns auf deinen Termin!</p>
            """

            if end_time:
                print(f"Endzeit: {format_time(end_time)}")
            else:
                print("Endzeit: Keine Endzeit angegeben")

            # Sende die E-Mail
            send_mail(
                email_subject,
                '',  # Text-Version der E-Mail (optional, da HTML verwendet wird)
                settings.DEFAULT_FROM_EMAIL,  # Absenderadresse aus den Django-Einstellungen
                [customer_email],  # Empfänger
                html_message=email_message,  # HTML-Nachricht
            )

            return JsonResponse({'message': 'E-Mail erfolgreich gesendet'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'message': 'Invalid request method'}, status=400)

def format_date(date_string):
    try:
        # Entfernt das 'Z' am Ende und konvertiert den String
        date_obj = datetime.datetime.strptime(date_string[:-1], "%Y-%m-%dT%H:%M:%S.%f")
        return date_obj.strftime("%d.%m.%Y")
    except Exception as e:
        return f"Fehler beim Verarbeiten des Datums: {e}"

def format_time(date_string):
    if not date_string:
        return "Keine Zeit angegeben"
    
    try:
        # Entfernt das 'Z' und konvertiert den String
        date_obj = datetime.datetime.strptime(date_string[:-1], "%Y-%m-%dT%H:%M:%S.%f")
        date_obj += timedelta(hours=2)
        return date_obj.strftime("%H:%M")
    except Exception as e:
        return f"Fehler beim Verarbeiten der Zeit: {e}"

@api_view(['POST'])
def teilnahme(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'E-Mail erforderlich.'}, status=status.HTTP_400_BAD_REQUEST)

    if Teilnahme.objects.filter(email=email).exists():
        return Response({'message': 'Du nimmst bereits teil.'}, status=status.HTTP_200_OK)

    serializer = TeilnahmeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Teilnahme erfolgreich!'}, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def search_amazon_products(request):
    asin_list = ["B0C7C67LDZ", "B0B6XYLH26", "B08DBHTXGW", "B08DBSDFF2"]

    amazon = AmazonApi(
        access_key="AKPAZW0SC31746129299",
        secret_key="Od3LbBI/NUG+v/8xKDrcjMeqh6VnQB+7yH0t0eGm",
        partner_tag="dein-tag-21",
        country="DE"
    )

    try:
        results = amazon.get_items(asin_list)
        print("📦 Amazon-Rohantwort:", results)

        items_result = results.get("ItemsResult") if results else None
        if not items_result:
            print("⚠️ Keine ItemsResult enthalten:", results)
            return JsonResponse([], safe=False)

        items = items_result.get("Items", [])

        products = []
        for item in items:
            try:
                title = item.get("ItemInfo", {}).get("Title", {}).get("DisplayValue", "Kein Titel")
                image = item.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL", "")
                url = item.get("DetailPageURL", "")

                if not image:
                    continue

                products.append({
                    "title": title,
                    "image": image,
                    "url": url
                })
            except Exception as e:
                print("⚠️ Fehler bei Item-Verarbeitung:", e)
                continue

        print("🔁 Produkte:", products)
        return JsonResponse(products, safe=False)

    except Exception as e:
        import traceback
        print("❌ Fehler bei Amazon-Abfrage:", e)
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)