from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse


class UserMixin(LoginRequiredMixin):
    
    def get_user(self, **kwargs):
        try:
            user = self.request.user
            return user
        except:
            raise Exception("User does not exist")
            
