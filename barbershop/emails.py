from djoser.email import ActivationEmail as DjoserActivationEmail

class CustomActivationEmail(DjoserActivationEmail):
    template_name = "emails/activation.html"