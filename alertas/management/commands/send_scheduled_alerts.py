from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from alertas.models import EmailAlertConfig
from alertas.services import send_alert_email
import logging

logger = logging.getLogger('alertas')

class Command(BaseCommand):
    help = 'Envía alertas programadas según la configuración de cada usuario'

    def handle(self, *args, **options):
        now = timezone.now()
        configs_to_send = []
        
        # Obtener todas las configuraciones activas
        active_configs = EmailAlertConfig.objects.filter(active=True)
        
        self.stdout.write(f"Configuraciones activas encontradas: {active_configs.count()}")
        
        for config in active_configs:
            should_send = False
            reason = ""
            
            # Verificar si nunca se ha enviado
            if not config.last_sent:
                should_send = True
                reason = "Nunca enviado"
            else:
                # Calcular el intervalo según la frecuencia
                time_since_last = now - config.last_sent
                
                if config.frequency == 'daily':
                    if config.last_sent.date() < now.date():
                        should_send = True
                        reason = f"Último envío hace {time_since_last.days} días"
                    else:
                        reason = f"Enviado hoy a las {config.last_sent.strftime('%H:%M')}"
                        
                elif config.frequency == 'weekly':
                    if config.last_sent + timedelta(days=7) <= now:
                        should_send = True
                        reason = f"Último envío hace {time_since_last.days} días"
                    else:
                        reason = f"Enviado hace {time_since_last.days} días (esperar {7 - time_since_last.days} días más)"
                        
                elif config.frequency == 'monthly':
                    if config.last_sent + timedelta(days=30) <= now:
                        should_send = True
                        reason = f"Último envío hace {time_since_last.days} días"
                    else:
                        reason = f"Enviado hace {time_since_last.days} días (esperar {30 - time_since_last.days} días más)"
            
            self.stdout.write(f"Config '{config.name}' ({config.get_frequency_display()}): {reason}")
            
            if should_send:
                configs_to_send.append(config)
        
        self.stdout.write(f"\nConfiguraciónes a enviar: {len(configs_to_send)}")
        
        # Enviar las alertas
        successful_sends = 0
        failed_sends = 0
        
        for config in configs_to_send:
            self.stdout.write(f"\nEnviando '{config.name}' a {config.email}...")
            try:
                success = send_alert_email(config, config.user)
                if success:
                    config.last_sent = now
                    config.save()
                    successful_sends += 1
                    self.stdout.write(self.style.SUCCESS(f'✓ Alertas enviadas exitosamente'))
                else:
                    failed_sends += 1
                    self.stdout.write(self.style.WARNING(f'⚠ No hay alertas para enviar'))
            except Exception as e:
                failed_sends += 1
                logger.error(f'Error enviando alertas para {config.email}: {str(e)}')
                self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
        
        # Resumen
        self.stdout.write(
            self.style.SUCCESS(
                f'\n====== RESUMEN ======\n'
                f'Envíos exitosos: {successful_sends}\n'
                f'Fallos: {failed_sends}\n'
                f'Total procesado: {len(configs_to_send)}'
            )
        )