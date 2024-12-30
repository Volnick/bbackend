from django.urls import path
from . import views

urlpatterns = [
    path('available-appointments/', views.available_appointments, name='available_appointments'),
    path('book-appointment/', views.book_appointment, name='book_appointment')
]