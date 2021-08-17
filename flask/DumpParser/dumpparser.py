import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

from tqdm import tqdm
from DumpParser.mwparserfromhelllinks import MWParserFromHellLinks


class DumpParser:
    def __init__(self):
        self.parser_name = 'DumpParser v0.0.1'
        self.links_labels = Counter()
        self.link_titles = defaultdict(Counter)
        self.links_titles_freq = Counter()
        self.titles_redirects = {}

    def parse_xml(self, xml_filepath, all_titles_in_ns0, all_titles_count, early_stopping=None):
        xmlns = 'http://www.mediawiki.org/xml/export-0.10/'
        namespaces = {'xmlns': xmlns}
        # get an iterable
        context = ET.iterparse(xml_filepath, events=("start", "end"))
        # turn it into an iterator
        context = iter(context)
        # get the root element
        event, root = next(context)

        processed_pages = 0

        all_titles_in_ns0 = set(all_titles_in_ns0)
        with tqdm(total=all_titles_count) as pbar:
            for event, elem in context:
                if event == 'end' and elem.tag == '{%s}page' % xmlns:
                    page = elem
                    ns = page.find('xmlns:ns', namespaces).text.strip()
                    if ns != '0':
                        continue

                    redirect = page.find('xmlns:redirect', namespaces)
                    if redirect is not None:
                        title = page.find('xmlns:title', namespaces).text.strip().replace(' ', '_')
                        redirect_to = redirect.attrib['title'].strip().replace(' ', '_')
                        self.titles_redirects[title] = redirect_to
                    else:
                        title = page.find('xmlns:title', namespaces).text
                        wikitext = page.find('xmlns:revision/xmlns:text', namespaces).text.strip()
                        wikicode = MWParserFromHellLinks(wikitext, all_titles_in_ns0)
                        for link in wikicode.get_links():
                            link_text = link['text']
                            self.links_labels[link_text] += 1
                            self.link_titles[link_text][link['title']] += 1
                            self.links_titles_freq[link['title']] += 1

                        strip_code = wikicode.get_wikicode().strip_code()
                        lines = strip_code.split('\n')
                        lines = list(map(lambda line: ' '.join(line.split()), lines))  # normalize whitespaces
                        yield title, lines

                    root.clear()
                    pbar.update(1)
                    processed_pages += 1
                    if early_stopping is not None and processed_pages >= early_stopping:
                        return
