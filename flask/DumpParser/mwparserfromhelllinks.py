import mwparserfromhell
import logging
from bs4 import BeautifulSoup

class MWParserFromHellLinks:
    '''No word-ending links. All titles with ":" are removed.'''
    def __init__(self, wikitext, titles_in_ns0):
        self._wikicode = mwparserfromhell.parse(wikitext)
        self._titles_in_ns0 = titles_in_ns0

    def get_wikicode(self):
        return self._wikicode

    def get_links(self):
        links = []
        for wikilink in self._wikicode.filter_wikilinks():
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
            if title_underscored not in self._titles_in_ns0:
                logging.info(f"Not in titles_in_ns0: {title} IGNORING")
                continue

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

            links.append({'text': text, 'title': title_underscored})

        return links