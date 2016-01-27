import six
import re

from autotranslate.compat import importlib
from django.conf import settings


def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    Credits: https://github.com/tomchristie/django-rest-framework/blob/master/rest_framework/settings.py#L138
    """
    if val is None:
        return None
    elif isinstance(val, six.string_types):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    try:
        parts = val.split('.')
        module_path, class_name = '.'.join(parts[:-1]), parts[-1]
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError('Could not import {} for API setting {}. {}: {}.'
                          .format(val, setting_name, e.__class__.__name__, e))


TranslatorService = getattr(settings, 'AUTOTRANSLATE_TRANSLATOR_SERVICE',
                            'autotranslate.services.GoSlateTranslatorService')
translator = perform_import(TranslatorService, 'AUTOTRANSLATE_TRANSLATOR_SERVICE')()

translate_string = translator.translate_string
translate_strings = translator.translate_strings


def look_placeholders(msgid, variable, translate_variable):
    for place_holder in re.findall('__(.*?)__~s', msgid):
        if variable == place_holder:
            return 's'

    for place_holder in re.findall('__(.*?)__~d', msgid):
        if variable == place_holder:
            return 'd'
    else:
        return
