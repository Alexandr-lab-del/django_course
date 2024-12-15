from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Recipient, Message, Mailing, MailingAttempt
from .forms import MailingForm
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page


class OwnerMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object()
        return obj.owner == self.request.user or self.request.user.groups.filter(name='Менеджеры').exists()


@login_required
@cache_page(60 * 15)
def home(request):
    total_mailings = Mailing.objects.filter(owner=request.user).count()
    active_mailings = Mailing.objects.filter(owner=request.user, status='Запущена').count()
    unique_recipients = Recipient.objects.filter(mailing__owner=request.user).distinct().count()
    context = {
        'total_mailings': total_mailings,
        'active_mailings': active_mailings,
        'unique_recipients': unique_recipients,
    }
    return render(request, 'mailing/home.html', context)


class RecipientListView(LoginRequiredMixin, ListView):
    model = Recipient
    template_name = 'mailing/recipient_list.html'
    context_object_name = 'recipients'

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='Менеджеры').exists():
            return Recipient.objects.all()
        return Recipient.objects.filter(mailing__owner=user).distinct()


class RecipientDetailView(LoginRequiredMixin, OwnerMixin, DetailView):
    model = Recipient
    template_name = 'mailing/recipient_detail.html'


class RecipientCreateView(LoginRequiredMixin, CreateView):
    model = Recipient
    fields = ['email', 'full_name', 'comment']
    template_name = 'mailing/recipient_form.html'
    success_url = reverse_lazy('mailing:recipient_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        return response


class RecipientUpdateView(LoginRequiredMixin, OwnerMixin, UpdateView):
    model = Recipient
    fields = ['email', 'full_name', 'comment']
    template_name = 'mailing/recipient_form.html'
    success_url = reverse_lazy('mailing:recipient_list')


class RecipientDeleteView(LoginRequiredMixin, OwnerMixin, DeleteView):
    model = Recipient
    template_name = 'mailing/recipient_confirm_delete.html'
    success_url = reverse_lazy('mailing:recipient_list')


class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    template_name = 'mailing/message_list.html'
    context_object_name = 'messages'

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='Менеджеры').exists():
            return Message.objects.all()
        return Message.objects.filter(mailing__owner=user).distinct()


class MessageDetailView(LoginRequiredMixin, OwnerMixin, DetailView):
    model = Message
    template_name = 'mailing/message_detail.html'


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    fields = ['subject', 'body']
    template_name = 'mailing/message_form.html'
    success_url = reverse_lazy('mailing:message_list')


class MessageUpdateView(LoginRequiredMixin, OwnerMixin, UpdateView):
    model = Message
    fields = ['subject', 'body']
    template_name = 'mailing/message_form.html'
    success_url = reverse_lazy('mailing:message_list')


class MessageDeleteView(LoginRequiredMixin, OwnerMixin, DeleteView):
    model = Message
    template_name = 'mailing/message_confirm_delete.html'
    success_url = reverse_lazy('mailing:message_list')


class MailingListView(LoginRequiredMixin, ListView):
    model = Mailing
    template_name = 'mailing/mailing_list.html'
    context_object_name = 'mailings'

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='Менеджеры').exists():
            return Mailing.objects.all()
        return Mailing.objects.filter(owner=user)


class MailingDetailView(LoginRequiredMixin, OwnerMixin, DetailView):
    model = Mailing
    template_name = 'mailing/mailing_detail.html'


class MailingCreateView(LoginRequiredMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'mailing/mailing_form.html'
    success_url = reverse_lazy('mailing:mailing_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MailingUpdateView(LoginRequiredMixin, OwnerMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'mailing/mailing_form.html'
    success_url = reverse_lazy('mailing:mailing_list')


class MailingDeleteView(LoginRequiredMixin, OwnerMixin, DeleteView):
    model = Mailing
    template_name = 'mailing/mailing_confirm_delete.html'
    success_url = reverse_lazy('mailing:mailing_list')


class MailingAttemptListView(LoginRequiredMixin, ListView):
    model = MailingAttempt
    template_name = 'mailing/mailing_attempt_list.html'

    def get_queryset(self):
        mailing = get_object_or_404(Mailing, pk=self.kwargs['pk'])
        if mailing.owner != self.request.user and not self.request.user.groups.filter(name='Менеджеры').exists():
            raise PermissionDenied
        return MailingAttempt.objects.filter(mailing=mailing)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mailing'] = get_object_or_404(Mailing, pk=self.kwargs['pk'])
        return context


@login_required
def send_mailing(request, pk):
    mailing = get_object_or_404(Mailing, pk=pk)
    if mailing.owner != request.user and not request.user.groups.filter(name='Менеджеры').exists():
        messages.error(request, "У вас нет прав на отправку этой рассылки.")
        return redirect('mailing:mailing_detail', pk=pk)

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
    messages.success(request, "Рассылка завершена.")
    return redirect('mailing:mailing_detail', pk=pk)


@login_required
def mailing_statistics(request):
    user = request.user
    if user.groups.filter(name='Менеджеры').exists():
        mailings = Mailing.objects.all()
    else:
        mailings = Mailing.objects.filter(owner=user)

    stats = {}
    for mailing in mailings:
        attempts = MailingAttempt.objects.filter(mailing=mailing)
        success = attempts.filter(status='Успешно').count()
        fail = attempts.filter(status='Не успешно').count()
        stats[mailing] = {
            'success': success,
            'fail': fail,
            'total': attempts.count(),
        }

    context = {
        'stats': stats
    }
    return render(request, 'mailing/mailing_statistics.html', context)
