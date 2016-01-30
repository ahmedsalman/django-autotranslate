import collections
import six
import re

from autotranslate.compat import goslate, googleapiclient

from django.conf import settings

from yandex_translate import YandexTranslate


class BaseTranslatorService:
    """
    Defines the base methods that should be implemented
    """

    def translate_string(self, text, target_language, source_language='en'):
        """
        Returns a single translated string literal for the target language.
        """
        raise NotImplementedError('.translate_string() must be overridden.')

    def translate_strings(self, strings, target_language, source_language='en', optimized=True):
        """
        Returns a iterator containing translated strings for the target language
        in the same order as in the strings.
        :return:    if `optimized` is True returns a generator else an array
        """
        raise NotImplementedError('.translate_strings() must be overridden.')


class GoSlateTranslatorService(BaseTranslatorService):
    """
    Uses the free web-based API for translating.
    https://bitbucket.org/zhuoqiang/goslate
    """


    def __init__(self):
        self.developer_key = getattr(settings, 'YANDEX_TRANSLATE_KEY', None)
        self.yandex_translate_obj = YandexTranslate(self.developer_key)

        # self.number = self.yandex_translate_obj.translate("_|_number_|_(~d~", 'fr')
        # self.text_item = self.yandex_translate_obj.translate("_|_item_|_(~s~", 'fr')
        # self.character_s = self.yandex_translate_obj.translate("s", 'fr')
        # self.character_d = self.yandex_translate_obj.translate("d", 'fr')

        # assert goslate, '`GoSlateTranslatorService` requires `goslate` package'
        # self.service = goslate.Goslate()

    def translate_string(self, text, target_language, source_language='en'):
        assert isinstance(text, six.string_types), '`text` should a string literal'
        direction = source_language+'-'+target_language
        response = self.yandex_translate_obj.translate(text, direction)
        return response['text'][0]

    def translate_strings(self, strings, target_language, source_language='en', optimized=True):
        assert isinstance(strings, collections.Iterable), '`strings` should a iterable containing string_types'
        direction = source_language+'-'+target_language
        translation_list = strings
        count = 0

        self.number = self.yandex_translate_obj.translate("__number__~d~", direction)
        self.text_item = self.yandex_translate_obj.translate("__item__~s~", direction)
        self.character_d = self.yandex_translate_obj.translate("~d~", direction)
        self.character_s = self.yandex_translate_obj.translate("~s~", direction)

        from autotranslate.utils import look_placeholders
        from .management.commands.translate_messages import fix_translation

        #import time
        #time.sleep(15) # delays for 15 seconds

        for item in strings:
            variable = None
            response = self.yandex_translate_obj.translate(item, direction, 'html')
            translation_response = response['text'][0]
            try:
                translation_response = fix_translation(item,  translation_response)
            except IndexError:
                pass

            if self.number['text'][0] in translation_response:
                translation_response = translation_response.replace(self.number['text'][0], "%d")

            if self.text_item['text'][0] in translation_response:
                translation_response = translation_response.replace(self.text_item['text'][0], "%s")

            if "__item__~s~" in translation_response:
                translation_response = translation_response.replace('__item__~s~', '%s')

            if "__number__~d~" in translation_response:
                translation_response = translation_response.replace('__number__~d~', '%d')

            variables = re.findall('%\((.*?)\)', item)
            translate_variables = re.findall('%\((.*?)\)', translation_response)
            for variable in variables:
                translation_response = re.sub('%\((.*?)\)', '%('+variable+')', translation_response)

            variables = re.findall('__(.*?)__', item)
            translate_variables = re.findall('__(.*?)__', translation_response)
            for translate_variable, variable in zip(translate_variables, variables):
                if look_placeholders(item, variable, translation_response) == 's':
                    translation_response = re.sub(r'__' + re.escape(translate_variable) + r'__', '%(' + variable + ')', translation_response)
                    translation_response = re.sub(re.escape(self.character_s['text'][0]), 's', translation_response, 1)
                    translation_response = re.sub(r'~s~', 's', translation_response, 1)
                elif look_placeholders(item, variable, translation_response) == 'd':
                    translation_response = re.sub(r'__' + re.escape(translate_variable) + r'__', '%(' + variable + ')', translation_response)
                    translation_response = re.sub(re.escape(self.character_d['text'][0]), 'd', translation_response, 1)
                    translation_response = re.sub(r'~d~', 'd', translation_response, 1)
                else:
                    translation_response = re.sub(r'__' + re.escape(translate_variable) + r'__', '%(' + variable + ')', translation_response)

            variables = re.findall('\{(.*?)\}', item)
            translate_variables = re.findall('\{(.*?)\}', translation_response)
            for translate_variable, variable in zip( translate_variables, variables):
                translation_response = re.sub(r'\{' + re.escape(translate_variable) + r'\}', '{' + variable + '}', translation_response )

            if ')_s' in translation_response:
                translation_response = translation_response.replace(')_s', 's')

            if ')_d' in translation_response:
                translation_response = translation_response.replace(')_d', 'd')

            translation_list[count] = translation_response
            count += 1
            print translation_response.encode('utf-8')
            # if self.count > 100:
            #     break
        return translation_list



    # def __init__(self):
    #     assert goslate, '`GoSlateTranslatorService` requires `goslate` package'
    #     self.service = goslate.Goslate()
    #
    # def translate_string(self, text, target_language, source_language='en'):
    #     assert isinstance(text, six.string_types), '`text` should a string literal'
    #     return self.service.translate(text, target_language, source_language)

    # def translate_strings(self, strings, target_language, source_language='en', optimized=True):
    #     assert isinstance(strings, collections.Iterable), '`strings` should a iterable containing string_types'
    #     translations = self.service.translate(strings, target_language, source_language)
    #     return translations if optimized else [_ for _ in translations]


class GoogleAPITranslatorService(BaseTranslatorService):
    """
    Uses the paid Google API for translating.
    https://github.com/google/google-api-python-client
    """

    def __init__(self, max_segments=128):
        assert googleapiclient, '`GoogleAPITranslatorService` requires `google-api-python-client` package'

        self.developer_key = getattr(settings, 'GOOGLE_TRANSLATE_KEY', None)
        assert self.developer_key, ('`GOOGLE_TRANSLATE_KEY` is not configured, '
                                    'it is required by `GoogleAPITranslatorService`')

        from googleapiclient.discovery import build
        self.service = build('translate', 'v2', developerKey=self.developer_key)

        # the google translation API has a limit of max
        # 128 translations in a single request
        # and throws `Too many text segments Error`
        self.max_segments = max_segments
        self.translated_strings = []

    def translate_string(self, text, target_language, source_language='en'):
        assert isinstance(text, six.string_types), '`text` should a string literal'
        response = self.service.translations() \
            .list(source=source_language, target=target_language, q=[text]).execute()
        return response.get('translations').pop(0).get('translatedText')

    def translate_strings(self, strings, target_language, source_language='en', optimized=True):
        assert isinstance(strings, collections.MutableSequence), \
            '`strings` should be a sequence containing string_types'
        assert not optimized, 'optimized=True is not supported in `GoogleAPITranslatorService`'
        if len(strings) <= self.max_segments:
            setattr(self, 'translated_strings', getattr(self, 'translated_strings', []))
            response = self.service.translations() \
                .list(source=source_language, target=target_language, q=strings).execute()
            self.translated_strings.extend([t.get('translatedText') for t in response.get('translations')])
            return self.translated_strings
        else:
            self.translate_strings(strings[0:self.max_segments], target_language, source_language, optimized)
            _translated_strings = self.translate_strings(strings[self.max_segments:],
                                                         target_language, source_language, optimized)

            # reset the property or it will grow with subsequent calls
            self.translated_strings = []
            return _translated_strings
