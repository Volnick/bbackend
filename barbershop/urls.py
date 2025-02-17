from django.urls import path
from . import views

urlpatterns = [
    path('available-appointments/', views.available_appointments, name='available_appointments'),
    path('get-appointments/', views.get_appointments, name='get_appointment'),
    path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('get-user-appointments/', views.get_user_appointments, name='get_user_appointments'),
    path('delete-appointment/', views.delete_appointment, name='delete_appointment'),
    path('refund-payment/', views.refund_payment, name='refund_payment'),
]