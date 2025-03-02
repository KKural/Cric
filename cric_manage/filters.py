from decimal import Decimal
from django.db.models import Q
import django_filters
from cric_users.models import User, Match, Team, Payment, Attendance, Wallet


class UserFilter(django_filters.FilterSet):
    query = django_filters.CharFilter(method='universal_search', label='Search')


    class Meta:
        model = User
        fields = ['query']

    def universal_search(self, queryset, name, value):
        return queryset.filter(Q(username__icontains=value) | Q(first_name__icontains=value) | Q(last_name__icontains=value))
    
    