import operator
from functools import reduce
from rest_framework import filters
from django.db.models import Q

from lgr import models

class QuickSearchFilter(filters.SearchFilter):
    def filter_queryset(self, request, queryset, view):
        search_terms = self.get_search_terms(request)
        for search_term in search_terms:
            if search_term.startswith('!user:'):
                queryset = models.Barcode.objects.filter(
                    loans__status=models.Loan.TAKEN,
                    loans__person__nickname__iexact=search_term[6:]
                )
                return queryset
            if search_term.startswith('!item:'):
                queryset = models.Barcode.objects.filter(
                    item__name__iexact=search_term[6:]
                )
                return queryset
            if search_term.startswith('!'):
                queryset = models.Barcode.objects.filter(code=search_term[1:])
                return queryset
        return super().filter_queryset(request, queryset, view)


def field_search_filter(field):
    class FieldSearchFilter(filters.SearchFilter):
        def filter_queryset(self, request, queryset, view):
            search_terms = self.get_search_terms(request)
            if search_terms:
                search_terms = [Q(**{field: i}) for i in search_terms]
                queryset = queryset.filter(reduce(operator.or_, search_terms))
            return queryset
    return FieldSearchFilter



