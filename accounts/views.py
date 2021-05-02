import os
from importlib import import_module

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.shortcuts import redirect, render, resolve_url
from django.urls import reverse_lazy
from django.views import generic
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

def get_user(identity):
    User = get_user_model()
    print(identity)
    user, created = User.objects.get_or_create(username=identity['preferred_username'])
    for group in identity['groups']:
        my_group = Group.objects.filter(name=group).first()
        if my_group:
            my_group.user_set.add(user)
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    return user


class SignUpView(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'auth/signup.html'

    def post(self, request, *args, **kwargs):
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            user_group = Group.objects.get(name='students')
            user.groups.add(user_group)
            return redirect('login')
        else:
            return render(request, self.template_name, {'form': form})


from django.urls import reverse

from django.utils.http import is_safe_url

from .auth import get_server

try:
    LOGIN_REDIRECT_URL = settings.LOGIN_REDIRECT_URL
except AttributeError:
    LOGIN_REDIRECT_URL = '/'

try:
    LOGOUT_REDIRECT_URL = settings.LOGOUT_REDIRECT_URL
except AttributeError:
    LOGOUT_REDIRECT_URL = '/'

try:
    AUTH_SCOPE = settings.AUTH_SCOPE
except AttributeError:
    AUTH_SCOPE = ('openid',)


try:
    ALLOWED_REDIRECTION_HOSTS = [host for host in os.getenv('ALLOWED_REDIRECTION_HOSTS', '').split(',') if
                                 host] or settings.ALLOWED_REDIRECTION_HOSTS
except AttributeError:
    ALLOWED_REDIRECTION_HOSTS = []


def _import_object(path, def_name):
    try:
        mod, cls = path.split(':', 1)
    except ValueError:
        mod = path
        cls = def_name

    return getattr(import_module(mod), cls)


def login(request, return_path=None):
    if return_path is None:
        return_path = request.GET.get(auth.REDIRECT_FIELD_NAME, "")

    request.session['login_attempt'] = request.session.get('login_attempt', 0) + 1

    return redirect(get_server().authorize(
        redirect_uri=request.build_absolute_uri(reverse("login-done")),
        state=return_path,
        scope=AUTH_SCOPE,
    ))


class LoginFailed(Exception):
    pass


def login_again(request, return_path=None):
    if request.session.get('login_attempt', 5) < 3:
        return login(request, return_path)
    else:
        raise LoginFailed(f"Login failed after trying {request.session.get('login_attempt')} times.")


def callback(request):
    return_path = request.GET.get("state")
    code = request.GET.get("code")

    if not code:
        return login_again(request, return_path)

    res = get_server().request_token(
        redirect_uri=request.build_absolute_uri(reverse("login-done")),
        code=request.GET["code"],
    )

    user = get_user(res.id)
    if not user or not user.is_authenticated:
        return login_again(request, return_path)

    del request.session['login_attempt']
    auth.login(request, user)
    request.session['openid_token'] = res.id_token
    request.session['openid'] = res.id

    url_is_safe = is_safe_url(
        url=return_path,
        allowed_hosts={request.get_host(), *ALLOWED_REDIRECTION_HOSTS},
    )
    if not url_is_safe:
        return redirect(resolve_url(LOGIN_REDIRECT_URL))
    return redirect(return_path)


def logout(request):
    open_id_token = request.session.get('openid_token', '')
    auth.logout(request)

    if open_id_token:
        server = get_server()
        if server.end_session_endpoint:
            return redirect(server.end_session(
                post_logout_redirect_uri=request.build_absolute_uri(LOGOUT_REDIRECT_URL),
                state='',
                id_token_hint=open_id_token,
            ))
        else:
            return redirect(request.build_absolute_uri(LOGOUT_REDIRECT_URL))

    return redirect(request.build_absolute_uri(LOGOUT_REDIRECT_URL))

