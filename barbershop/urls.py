from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet

from . import views

router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet)
urlpatterns = [
    path('available-appointments/', views.available_appointments, name='available_appointments'),
    path('get-appointments/', views.get_appointments, name='get_appointment'),
    path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('get-user-appointments/', views.get_user_appointments, name='get_user_appointments'),
    path('delete-appointment/', views.delete_appointment, name='delete_appointment'),
    path('refund-payment/', views.refund_payment, name='refund_payment'),
    path('activate/<uid>/<token>/', views.activate_user, name='activate'),
    path('send-booking-email', views.send_booking_email, name='send_booking_email'),
    path('', include(router.urls)),
    path('teilnahme/', views.teilnahme, name='teilnahme'),
    path('amazon-search/', views.search_amazon_products, name='amazon_search'),
]