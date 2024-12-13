import json
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
from mailing.models import Recipient, Message, Mailing, MailingAttempt


class CustomJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        return super().default(obj)


class Command(BaseCommand):
    help = 'Exports mailing data to a JSON file'

    def handle(self, *args, **kwargs):
        data = {
            'recipients': list(Recipient.objects.values()),
            'messages': list(Message.objects.values()),
            'mailings': list(Mailing.objects.values()),
            'mailing_attempts': list(MailingAttempt.objects.values()),
        }

        with open('mailing.json', 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4, cls=CustomJSONEncoder)

        self.stdout.write(self.style.SUCCESS('Data exported successfully to mailing.json'))
