from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.urls import reverse
from .models import User, Notification


@receiver(post_save, sender=User)
def notify_user_created(sender, instance, created, **kwargs):
    if created:
        admins = User.objects.filter(role__name='Администратор')
        for admin in admins:
            Notification.objects.create(
                user=admin,
                message=f'Добавлен новый пользователь: {instance.lastname} {instance.firstname}',
                link=reverse('admin:uchet_user_change', args=[instance.id])
            )


@receiver(post_delete, sender=User)
def notify_user_deleted(sender, instance, **kwargs):
    admins = User.objects.filter(role__name='Администратор')
    for admin in admins:
        Notification.objects.create(
            user=admin,
            message=f'Удалён пользователь: {instance.lastname} {instance.firstname}',
            link=''
        )