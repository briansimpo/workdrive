from django.template import Library

register = Library()

@register.filter(name='can_access')
def can_access(user, file):
    return user.can_access(file)

@register.filter(name='can_read')
def can_read(user, file):
    return user.can_read(file)
    
@register.filter(name='can_write')
def can_write(user, file):
    return user.can_write(file)
    
@register.filter(name='can_delete')
def can_delete(user, file):
    return user.can_delete(file)
    
@register.filter(name='can_share')
def can_share(user, file):
    return user.can_share(file)

@register.filter(name='is_group_admin')
def is_group_admin(user, group):
    return user.is_group_admin(group)

@register.simple_tag(takes_context=True)
def file_owner(context, file):
    request = context['request']
    user = request.user
    owner = file.owner
    if user == owner:
        return "Me"
    else:
        return owner

@register.filter(name='is_file_admin')
def is_file_admin(user, file):
    return user.is_file_admin(file)

@register.filter(name='is_file_author')
def is_file_author(user, file):
    return user.is_file_author(file)

