import re

import mwparserfromhell
import logging
from bs4 import BeautifulSoup


class Parser:
    '''No word-ending links. All titles with ":" are removed.'''

    def __init__(self):
        self.name = 'MwParserFromHellLinks'
        self.version = '1.0.0'
        self._special_namespaces = ['File', 'Image']
        self._re_special_link = re.compile(r'\[\[(File|Image):.*?\]\]')

    def parse(self, wikitext):
        wikitext_mwparserfromhell = mwparserfromhell.parse(wikitext)
        return {'lines': self._lines(wikitext_mwparserfromhell), 'links': self._links(wikitext_mwparserfromhell)}

    def _lines(self, wikitext_mwparserfromhell):
        for wikilink in wikitext_mwparserfromhell.filter_wikilinks():
            title = wikilink.title.strip_code().strip()
            if title.startswith('File:') or title.startswith('Image:'):
                try:
                    wikitext_mwparserfromhell.remove(wikilink)
                except ValueError:
                    print(f'cannot remove: {title}. not found')

        strip_code = wikitext_mwparserfromhell.strip_code()
        strip_code = self._re_special_link.sub('', strip_code)
        lines = strip_code.strip().split('\n') # remove empty chars from the begin and end
        lines = list(map(lambda line: line.strip(), lines))  # remove whitespaces
        lines = list(map(lambda line: ' '.join(line.split()), lines))  # normalize whitespaces

        lines_normalized = [lines[0]]
        for i in range(1, len(lines)):
            if lines[i] != '' or (lines[i] == '' and lines[i-1] != ''):
                lines_normalized.append(lines[i])

        return lines_normalized

    def _links(self, wikitext_mwparserfromhell):
        links = []
        for wikilink in wikitext_mwparserfromhell.filter_wikilinks():
            title = wikilink.title.strip_code().strip()
            if len(title) == 0:
                logging.info(f"Ignoring empty title: {wikilink.title}")
                continue

            # check if title goes to existing page
            title_underscored = title.replace(' ', '_')
            if len(title_underscored) > 1:
                title_underscored = title_underscored[0].upper() + title_underscored[1:]
            else:
                title_underscored = title_underscored[0].upper()
            # if title_underscored not in self._titles_in_ns0:
            #     logging.info(f"Not in titles_in_ns0: {title} IGNORING")
            #     continue

            if wikilink.text is None:
                text = title
            else:
                text = wikilink.text.strip_code().strip()

                # check if text still contains some unnecessery tags
                if text.find('<') != -1:
                    new_text = BeautifulSoup(text).text
                    logging.info(f"BeautifulSoup from {text} to {new_text}")
                    text = new_text
                # remove some artifacts
                new_text = text.replace("'''", "")
                new_text = new_text.replace("''", "")
                if text != new_text:
                    logging.info(f"Artifacts removal from {text} to {new_text}")
                text = new_text

            links.append({'label': text, 'destination': title_underscored})

        return links
