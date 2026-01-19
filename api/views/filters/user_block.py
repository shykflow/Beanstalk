from rest_framework import filters

class UserBlockFilterBackend(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        queryset = queryset.exclude(created_by__in=request.user.blocks.all()) \
            .exclude(created_by__blocks=request.user)
        return queryset
