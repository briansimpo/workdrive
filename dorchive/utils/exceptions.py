import os
from django.shortcuts import render

from utils.helpers import get_template_name


class ExceptionHandlingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def get_app_name(self, request):
        resolver_match = getattr(request, 'resolver_match', None)
        return resolver_match.app_name


    def process_exception(self, request, exception):
        app_name = self.get_app_name(request)

        error_title = "Error"
        error_message = str(exception)

        template_name = get_template_name("error.html", "drive")

        context = {
            'title': error_title,
            'message': error_message,
        }
        return render(request=request, template_name=template_name, context=context)

