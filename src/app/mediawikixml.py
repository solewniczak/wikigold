import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

from tqdm import tqdm


class MediaWikiXml:
    def __init__(self, xml_filepath, parser):
        self._xml_filepath = xml_filepath
        self._xmlns = 'http://www.mediawiki.org/xml/export-0.10/'
        self._namespaces = {'xmlns': self._xmlns}

        self.parser = parser

        self.links_labels = Counter()
        self.link_titles = defaultdict(Counter)
        self.links_titles_freq = Counter()

    @staticmethod
    def normalize_title(title):
        return title.strip().replace(' ', '_')

    def _iterate_articles(self):
        # get an iterable
        context = ET.iterparse(self._xml_filepath, events=("start", "end"))
        # turn it into an iterator
        context = iter(context)
        # get the root element
        event, root = next(context)

        for event, elem in context:
            if event == 'end' and elem.tag == '{%s}page' % self._xmlns:
                page = elem
                ns = page.find('xmlns:ns', self._namespaces).text.strip()
                yield page, ns
                root.clear()

    def parse(self, early_stopping=-1):
        count_articles = 0
        titles_in_ns0 = set()
        print('calculating number of articles in dump ...', end=' ')
        for page, ns in self._iterate_articles():
            count_articles += 1
            if ns == '0':
                title = page.find('xmlns:title', self._namespaces).text
                title = self.normalize_title(title)
                titles_in_ns0.add(title)
        print(count_articles)

        if early_stopping == -1:
            pages_to_process = count_articles
        else:
            pages_to_process = min(count_articles, early_stopping)

        with tqdm(total=pages_to_process) as pbar:
            for page, ns in self._iterate_articles():
                if ns == '0':
                    redirect = page.find('xmlns:redirect', self._namespaces)
                    if redirect is not None:
                        title = page.find('xmlns:title', self._namespaces).text
                        title = self.normalize_title(title)
                        redirect_to = self.normalize_title(redirect.attrib['title'])
                        yield title, [], redirect_to
                    else:
                        title = page.find('xmlns:title', self._namespaces).text
                        title = self.normalize_title(title)
                        wikitext = page.find('xmlns:revision/xmlns:text', self._namespaces).text
                        try:
                            wikitext_parsed = self.parser.parse(wikitext)
                            lines = wikitext_parsed['lines']
                            for link in wikitext_parsed['links']:
                                destination = link['destination']
                                # Normalize destination
                                destination = destination.replace(' ', '_')
                                if len(destination) > 1:
                                    destination = destination[0].upper() + destination[1:]
                                else:
                                    destination = destination[0].upper()

                                if destination in titles_in_ns0:
                                    if 'label' not in link:
                                        link_label = lines[link['line']][link['start']:link['start']+link['length']]
                                    else:
                                        link_label = link['label']
                                    self.links_labels[link_label] += 1
                                    self.link_titles[link_label][link['destination']] += 1
                                    self.links_titles_freq[link['destination']] += 1
                            yield title, lines, None
                        except Exception as e:
                            print(f'cannot parse: {title}. skipping ...')
                            print(e)

                    pbar.update(1)
                    pages_to_process -= 1
                    if pages_to_process <= 0:
                        return
