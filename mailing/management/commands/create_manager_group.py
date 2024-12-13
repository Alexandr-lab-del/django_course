from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = 'Создает группу "Менеджеры" и назначает ей необходимые разрешения'

    def handle(self, *args, **kwargs):
        group, created = Group.objects.get_or_create(name='Менеджеры')
        if created:
            self.stdout.write(self.style.SUCCESS('Группа "Менеджеры" успешно создана'))
        else:
            self.stdout.write('Группа "Менеджеры" уже существует')

        permissions = Permission.objects.filter(codename__in=[
            'view_recipient',
            'view_mailing',
            'view_message',
            'view_mailingattempt',
        ])

        group.permissions.set(permissions)
        group.save()
        self.stdout.write(self.style.SUCCESS('Разрешения назначены группе "Менеджеры"'))
