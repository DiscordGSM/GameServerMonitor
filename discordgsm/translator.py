from __future__ import annotations

import json
import os
import sys
from argparse import ArgumentParser
from collections import OrderedDict
from typing import Dict, Optional

from discord import Locale, app_commands

path = os.path.dirname(os.path.realpath(__file__))
translations: Dict[str, Dict[str, str]] = {}

for locale in Locale:
    file = os.path.join(path, 'translations', f'{locale}.json')

    if os.path.isfile(file):
        with open(file, 'rb') as f:
            translations[locale.value] = json.loads(f.read())
    else:
        with open(file, 'w') as f:
            f.write('{}')

        translations[locale.value] = {}


def t(locale_str: str, locale: Locale):
    """Returns the translated string, default: en-US"""
    return translations.get(str(locale), translations['en-US']).get(locale_str, locale_str)


class Translator(app_commands.Translator):
    def __init__(self):
        self.translations = translations

    async def load(self):
        pass

        # import aiofiles
        # path = os.path.dirname(os.path.realpath(__file__))

        # for locale in Locale:
        #     async with aiofiles.open(os.path.join(path, 'translations', f'{locale}.json'), 'rb') as f:
        #         self.translations[locale.value] = json.loads(await f.read())

    async def unload(self):
        pass

    async def translate(
            self,
            locale_str: app_commands.locale_str,
            locale: Locale,
            context: app_commands.TranslationContext
    ) -> Optional[str]:
        return self.translations.get(locale.value, self.translations['en-US']).get(locale_str.message, locale_str.message)


if __name__ == '__main__':
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest='subparser_name')
    subparsers.add_parser('update', description='Update all locale json files base on en-US.json')

    args = parser.parse_args()

    if len(sys.argv) <= 1:
        parser.print_help(sys.stderr)
        sys.exit(-1)

    if args.subparser_name == 'update':
        with open(os.path.join(path, 'translations', 'en-US.json'), 'rb') as f:
            enUS: OrderedDict[str, str] = json.loads(f.read(), object_pairs_hook=OrderedDict)

        for locale in Locale:
            results: OrderedDict[str, str] = OrderedDict()
            translation = translations[locale.value]

            for key, value in enUS.items():
                results[key] = translation[key] if key in translation else value

            file = os.path.join(path, 'translations', f'{locale}.json')

            with open(file, 'w', encoding='utf8') as f:
                f.write(json.dumps(results, indent=4, ensure_ascii=False))
