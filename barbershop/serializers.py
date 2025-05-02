from rest_framework import serializers
from djoser.serializers import (
    UserCreateSerializer as BaseUserCreateSerializer,
    UserSerializer as BaseUserSerializer,
)
from django.contrib.auth import get_user_model
from .models import Appointment, Teilnahme

# Hole das CustomUser-Modell
CustomUser = get_user_model()

# ✅ Benutzerregistrierung (username wird vom Frontend übergeben!)
class UserCreateSerializer(BaseUserCreateSerializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    telefonnummer = serializers.CharField(required=True)
    username = serializers.CharField(required=True)

    class Meta(BaseUserCreateSerializer.Meta):
        model = CustomUser
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "telefonnummer",
            "password",
            "username",  # Wird jetzt explizit vom Frontend erwartet
        )

# 👤 Nutzerprofil: Daten des aktuellen Users anzeigen
class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        model = CustomUser
        fields = ("id", "username", "email", "telefonnummer")

# 🔥 Optional: Erweiterung für Adminzwecke
class CustomUserSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        model = CustomUser
        fields = UserSerializer.Meta.fields + ("is_superuser",)

# 📆 Terminserialisierung (z. B. für Buchungen)
class AppointmentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Appointment
        fields = "__all__"

class TeilnahmeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teilnahme
        fields = ['email']