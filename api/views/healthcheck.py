from django.http import HttpResponse
from rest_framework.request import Request

def healthcheck(request: Request) -> HttpResponse:
   return HttpResponse()
