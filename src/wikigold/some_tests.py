import bz2
import json
import os
import sys
import xml.etree.ElementTree as ET

# https://stackoverflow.com/questions/7171140/using-python-iterparse-for-large-xml-files
from collections import Counter, defaultdict

from mwparallelparser import Parser
from tqdm import tqdm


def iterate_xml_dump(source, tags):

    context = ET.iterparse(source, events=("start", "end"))
    context = iter(context)
    event, root = next(context)

    mediawiki_namespace = 'http://www.mediawiki.org/xml/export-0.10/'
    namespaces = {'mediawiki': mediawiki_namespace}

    for event, element in context:
        if event == 'end' and element.tag == '{%s}page' % mediawiki_namespace:
            return_elements = {}
            for tag in tags:
                tag_path = tag.split('/')
                tag_path_prefixed = ['mediawiki:' + path_element for path_element in tag_path]
                tag_path_full = '/'.join(tag_path_prefixed)
                return_element = element.find(tag_path_full, namespaces)
                return_elements[tag] = return_element
            yield return_elements
            root.clear()

lang='en'
dump_date='20211001'

filename = f'{lang}wiki-{dump_date}-pages-meta-current.xml'
filename_bz2 = f'{lang}wiki-{dump_date}-pages-meta-current.xml.bz2'
filename_metadata = f'{lang}wiki-{dump_date}-metadata.json'


homedir = os.path.expanduser("~/")
if homedir == "~/":
    raise ValueError('could not find a default download directory')

download_dir = os.path.join(homedir, 'wikigold_data')

filepath = os.path.join(download_dir, filename)
filepath_bz2 = os.path.join(download_dir, filename_bz2)
filepath_metadata = os.path.join(download_dir, filename_metadata)

with open(filepath_metadata, 'r') as file:
    metadata = json.load(file)
metadata['titles_in_ns0'] = set(metadata['titles_in_ns0'])

# source = open(filepath)
source = bz2.open(filepath_bz2)
parser = Parser()
pages_to_process=len(metadata['titles_in_ns0'])

# with tqdm(total=pages_to_process) as pbar:
#     for tag in iterate_xml_dump(source, ('ns', 'redirect', 'title', 'revision/text')):
#         ns = tag['ns'].text.strip()
#         if ns == '0':
#             wikitext = tag['revision/text'].text
#             parser.parse(wikitext)
#             pbar.update(1)

links_labels = Counter()
link_titles = defaultdict(Counter)
links_titles_freq = Counter()
wikipedia_decisions = []

titles_in_ns0=metadata['titles_in_ns0']
with tqdm(total=pages_to_process) as pbar:
    for tag in iterate_xml_dump(source, ('ns', 'redirect', 'title', 'revision/text')):
        if tag['redirect'] is not None:
            pass
        else:
            title = tag['title'].text
            # title = normalize_title(title)
            wikitext = tag['revision/text'].text

            wikitext_parsed = parser.parse(wikitext)
            lines = wikitext_parsed['lines']
            for parallel_tag in wikitext_parsed['tags']:
                if parallel_tag['type'] == 'link':
                    link = {
                        'source': title,
                        'destination': parallel_tag['attributes']['destination'],
                        'line': parallel_tag['spans'][0]['line'],
                        'start': parallel_tag['spans'][0]['start'],
                        'length': parallel_tag['spans'][0]['length'],
                    }
                    wikipedia_decisions.append(link)

                    if link['destination'] in titles_in_ns0:
                        link_label = lines[link['line']][link['start']:link['start'] + link['length']]
                        links_labels[link_label] += 1
                        link_titles[link_label][link['destination']] += 1
                        links_titles_freq[link['destination']] += 1

        links_labels_mem = sys.getsizeof(links_labels)/(1024*1024)
        link_titles_mem = sys.getsizeof(link_titles)/(1024*1024)
        links_titles_freq_mem = sys.getsizeof(links_titles_freq)/(1024*1024)
        wikipedia_decisions_mem = sys.getsizeof(wikipedia_decisions)/(1024*1024)
        pbar.set_description(f'link_labels: {links_labels_mem:.2f} MiB.'
                             f' link_titles: {link_titles_mem:.2f} MiB.'
                             f' links_titles_freq: {links_titles_freq_mem:.2f} MiB.'
                             f' wikipedia_decisions: {wikipedia_decisions_mem:.2f} MiB.')
        pbar.update(1)

source.close()