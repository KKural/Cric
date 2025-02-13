import django_tables2 as tables
from django_tables2 import TemplateColumn
from .models import Match

class UpcomingMatchTable(tables.Table):
    name = tables.Column(linkify=True)
    actions = TemplateColumn(
        template_code="""
<a href="{% url 'match_detail' record.pk %}">View</a> |
<a href="{% url 'match_delete' record.pk %}" onclick="return confirm('Delete this match and all linked entries?');">
    Delete
</a>
        """,
        orderable=False
    )
    
    class Meta:
        model = Match
        fields = ('name', 'date', 'time', 'duration', 'location', 'actions')
        template_name = "tables/bootstrap_htmx.html"
        attrs = {"class": "table table-striped table-hover"}
