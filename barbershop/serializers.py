from djoser.serializers import UserSerializer
from django.contrib.auth import get_user_model

from rest_framework import serializers
from .models import Appointment

User = get_user_model()

class AppointmentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Appointment
        fields = "__all__"

class CustomUserSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        print("🔥 CustomUserSerializer wird geladen!")  # Debugging
        model = User
        fields = UserSerializer.Meta.fields + ("is_superuser",)  # `is_superuser` explizit hinzufügen
