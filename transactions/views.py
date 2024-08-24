from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMultiAlternatives
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from accounts.models import UserBankAccount

from .constants import DEPOSIT, LOAN, LOAN_PAID, TRANSFER_MONEY, WITHDRAW
from .forms import DepositForm, LoanRequestForm, TransferMoneyForm, WithdrawForm
from .models import TransactionModel

# Create your views here.from django.views import generic


def send_transaction_email(user, amount, subject, template):
    message = render_to_string(
        template,
        {
            "user": user,
            "amount": amount,
        },
    )
    send_email = EmailMultiAlternatives(subject, "", to=[user.email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()


class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = "transactions/transaction.html"
    model = TransactionModel
    title = ""
    success_url = reverse_lazy("transaction_report")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"account": self.request.user.account})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context.update({"title": self.title})
        return context


class TransferMoneyView(TransactionCreateMixin):
    form_class = TransferMoneyForm
    template_name = "transactions/transfermoney.html"
    title = "Transfer Money"
    success_url = reverse_lazy("transaction_report")

    def get_initial(self):
        initial = {"transaction_type": TRANSFER_MONEY}
        return initial

    def form_valid(self, form):
        account_number = form.cleaned_data.get("account_number")
        amount = form.cleaned_data.get("amount")
        sender = self.request.user.account

        try:
            reciver = UserBankAccount.objects.get(account_number=account_number)
            if sender.balance < amount:
                messages.error(self.request, "Insufficient Balance")
                return super().form_invalid(form)
            reciver.balance += amount
            sender.balance -= amount
            reciver.save(update_fields=["balance"])
            sender.save(update_fields=["balance"])
            messages.success(self.request, "Send Money Successful")
            send_transaction_email(
                self.request.user,
                amount,
                "Money Transfer Message",
                "transactions/deposite_mail.html",
            )
            send_transaction_email(
                reciver.user,
                amount,
                "Money Revived Message",
                "transactions/deposite_mail.html",
            )

            return super().form_valid(form)
        except UserBankAccount.DoesNotExist:
            messages.error(self.request, "Invalid Account No")
            return super().form_invalid(form)
