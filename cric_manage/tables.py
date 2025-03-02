import django_tables2 as tables
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.templatetags.static import static
from django.conf import settings
import os

User = get_user_model()

class UserHTMxTable(tables.Table):
    id = tables.Column(verbose_name="ID")
    username = tables.Column(verbose_name="Username")
    role = tables.Column(verbose_name="Role")
    is_staff = tables.BooleanColumn(verbose_name="Staff Status", yesno='✓,✗')
    last_login = tables.Column(verbose_name="Last Login")
    wallet_amount = tables.Column(verbose_name="Wallet Amount", orderable=False)
    
    class Meta:
        model = User
        template_name = "tables/tailwind_table.html"
        fields = ("id", "username", "role", "is_staff", "last_login", "wallet_amount")
        sequence = ("id", "username", "role", "last_login", "is_staff", "wallet_amount")
    
    def render_wallet_amount(self, record):
        wallet = record.wallet_set.first()  
        return wallet.amount if wallet else "-"
        
    def render_role(self, value):
        """Render role with appropriate icon using hardcoded paths"""
        if not value:
            return "-"
            
        value_lower = value.lower() if value else ""
        
        # Use absolute URLs to the static files
        bat_icon_url = "/static/icons/bat.png"
        ball_icon_url = "/static/icons/ball.png"
        
        if value_lower == 'batsman':
            role_html = '<div><img src="{}" class="inline-block w-4 h-4 mr-1" alt="Batsman"/></div>'.format(bat_icon_url)
        elif value_lower == 'bowler':
            role_html = '<div><img src="{}" class="inline-block w-4 h-4 mr-1" alt="Bowler"/></div>'.format(ball_icon_url)
        elif value_lower == 'allrounder':
            role_html = '<div><img src="{}" class="inline-block w-4 h-4 mr-1" alt="Batsman"/><img src="{}" class="inline-block w-4 h-4 mr-1" alt="Bowler"/></div>'.format(bat_icon_url, ball_icon_url)
        else:
            role_html = '<div>{}</div>'.format(value)
            
        return mark_safe(role_html)