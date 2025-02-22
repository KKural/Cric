import django_tables2 as tables
from django.contrib.auth import get_user_model

User = get_user_model()

class UserHTMxTable(tables.Table):
    wallet_amount = tables.Column(verbose_name="Wallet Amount", orderable=False)
    # Optionally rename is_staff for clarity:
    # is_staff = tables.Column(verbose_name="Admin")
    
    class Meta:
        model = User
        template_name = "tables/bootstrap_htmx.html"
        fields = ("id", "username", "is_staff", "last login", "role")  # exclude password and email etc.
    
    def render_wallet_amount(self, record):
        wallet = record.wallet_set.first()  # Assumes a one-to-many relation
        return wallet.amount if wallet else "-"