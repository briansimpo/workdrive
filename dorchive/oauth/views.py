from authlib.integrations.django_client import OAuth
from django.shortcuts import redirect
from django.utils.crypto import get_random_string
from django.contrib import auth
from dorchive.users.models import User
from dorchive.oauth import config

oauth = OAuth()

oauth.register(
    name=config.OAUTH_NAME,
    client_id=config.OAUTH_CLIENT_ID,
    client_secret=config.OAUTH_CLIENT_SECRET,
    access_token_url=config.OAUTH_TOKEN_URL,
    access_token_params=None,
    authorize_url=config.OAUTH_AUTHORIZE_URL,
    authorize_params=None,
    client_kwargs={'scope': 'view-user'},
)

def login(request):
    redirect_uri = config.OAUTH_REDIRECT_URL
    state = get_random_string(config.STATE_CODE_LENGTH)
    request.session['session_state'] = state
    extra_para = {'state': state}
    return oauth.luanar.authorize_redirect(request, redirect_uri, **extra_para)

def logout(request):
    auth.logout(request)
    return redirect('index')

def authorize(request): 
    userinfo_url = config.OAUTH_USERINFO_URL 
    token = oauth.luanar.authorize_access_token(request)
    response = oauth.luanar.get(userinfo_url, token=token)
    response.raise_for_status()
    userinfo = response.json()
    
    user = User.objects.filter(email=userinfo['email']).first()
    if not user:
        user = create_user(userinfo)
    else:
        user = update_user(user, userinfo)
    auth.login(request, user)
    return redirect('account')
  
def create_user(userinfo):
    name = userinfo['name']
    email = userinfo['email']

    user = User.objects.create_user(
        email=email, 
        username=email,
        name=name,
        is_staff=True 
    )
    
    user.set_password(None)
    user.save()
    return user

def update_user(user, userinfo):
    name = userinfo['name']
    user.name=name
    user.save()
    return user
