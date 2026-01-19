from collections import OrderedDict
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

def get_page_size_from_request(request: Request, default_size:int) -> int:
    """
    Retrieves the page size from the `request` query parameters.
    Returns `default_size` if no page size is specified.

    Raises if the page size is not able to be converted to an int or it is not
    1 to `settings.MAX_PAGINATION_PAGE_SIZE`.
    """
    page_size = request.query_params.get('page_size')
    if page_size is None:
        return default_size
    page_size = int(page_size)
    if not 0 < page_size <= settings.MAX_PAGINATION_PAGE_SIZE:
        raise SuspiciousOperation()
    return page_size


class AppPageNumberPagination(PageNumberPagination):
    """
    Page number pagination that defaults to a page size of 20
    and returns next and previous page numbers intead of full URLs.
    The appropriate page will be returned from the "page=123" query
    parameter in the request object, defaults to "page=1".
    ---

    To use on an action set `pagination_class` in the action decorator.
    Then paginate using `self`.

    ```
    @action(detail=True, methods=['get'], pagination_class=AppPageNumberPagination)
    def my_view(self, request, pk):
        page = self.paginate_queryset(queryset_to_paginate) # Do not have to pass request
        serializer = MySerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    ```

    ---

    To use a page size that is not 20, first instantiate with `page_size`.
    Then paginate using the instantiated object.
    Page sizes must be 1 to `settings.MAX_PAGINATION_PAGE_SIZE`.

    ```
    paginator = AppPageNumberPagination(page_size=8)
    page = paginator.paginate_queryset(queryset_to_paginate, request) # Make sure to pass request here as well
    serializer = MySerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)
    ```
    """

    def __init__(self, page_size=20):
        if not 0 < page_size <= settings.MAX_PAGINATION_PAGE_SIZE:
            raise SuspiciousOperation()
        self.page_size = page_size
        super().__init__()

    # override
    def get_paginated_response(self, data) -> Response:
        previous_page_number = None
        next_page_number = None
        if self.page.has_previous():
            previous_page_number = self.page.previous_page_number()
        if self.page.has_next():
            next_page_number = self.page.next_page_number()
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next_page', next_page_number),
            ('previous_page', previous_page_number),
            ('results', data)
        ]))
