from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings

from mailing.models import Mailing, MailingAttempt


class Command(BaseCommand):
    help = 'Отправляет рассылку по ID'

    def add_arguments(self, parser):
        parser.add_argument('mailing_id', type=int, help='ID рассылки для отправки')

    def handle(self, *args, **kwargs):
        mailing_id = kwargs['mailing_id']
        try:
            mailing = Mailing.objects.get(pk=mailing_id)
        except Mailing.DoesNotExist:
            raise CommandError('Рассылка с ID {} не существует'.format(mailing_id))

        mailing.status = 'Запущена'
        mailing.save()

        message = mailing.message
        recipients = mailing.recipients.all()

        for recipient in recipients:
            try:
                send_mail(
                    subject=message.subject,
                    message=message.body,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[recipient.email],
                    fail_silently=False,
                )
                MailingAttempt.objects.create(
                    status='Успешно',
                    server_response='Email sent successfully.',
                    mailing=mailing
                )
            except Exception as e:
                MailingAttempt.objects.create(
                    status='Не успешно',
                    server_response=str(e),
                    mailing=mailing
                )
        self.stdout.write(self.style.SUCCESS('Рассылка {} завершена.'.format(mailing_id)))
