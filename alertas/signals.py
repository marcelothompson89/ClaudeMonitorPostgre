# alertas/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings

@receiver(post_save, sender=User)
def notify_admin_on_user_registration(sender, instance, created, **kwargs):
    """Enviar correo al administrador cuando se registra un nuevo usuario"""
    if created:  # Solo cuando se crea un usuario nuevo
        # Obtener los detalles del usuario
        username = instance.username
        email = instance.email
        full_name = f"{instance.first_name} {instance.last_name}".strip()
        date_joined = instance.date_joined.strftime('%d/%m/%Y %H:%M:%S')
        
        # Preparar el asunto y mensaje
        subject = f'[Oversia] Nuevo usuario registrado: {username}'
        message = f"""
Se ha registrado un nuevo usuario en Oversia:

Usuario: {username}
Nombre: {full_name}
Email: {email}
Fecha de registro: {date_joined}

Para revisar o eliminar este usuario, ingresa al panel de administración
        """
        
        # Email de destino (puede ser tu correo personal o una lista de administradores)
        admin_email = 'marcelo_thompson@hotmail.com'  # Reemplaza con tu correo
        
        # Enviar el correo
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [admin_email],
            fail_silently=False,
        )