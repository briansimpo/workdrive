
from django.shortcuts import render



def get_task_feedback():
    return "You will be notified when completed."


def get_template_name(template_path, app_name=None):
    if app_name is None:
        return template_path
    else:
        return f"{app_name}/{template_path}"


def get_file_path(file_name, app_name=None):
    if app_name is None:
        return file_name
    else:
        return f"{app_name}/{file_name}"
    

def show_feedback(request, message, title=None, redirect_url=None, success=True, app_name=None):
    if not app_name:
        template = "feedback.html"
    else:
        template = get_template_name("feedback.html", app_name)
    context = {
        'message': str(message),
        'success': success,
        'title': title,
        'redirect_url': redirect_url
    }
    return render(request, template, context)


def show_success(request, message, redirect_url=None, app_name=None):
    title = "Successful!"
    return show_feedback(request=request, message=message, title=title, redirect_url=redirect_url, app_name=app_name)


def show_error(request, message, redirect_url=None, app_name=None):
    title = "Oops! there's a problem"
    return show_feedback(request=request, message=message, title=title, redirect_url=redirect_url, success=False, app_name=app_name)

