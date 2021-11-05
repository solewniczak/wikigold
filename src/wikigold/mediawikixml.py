import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

from mwparallelparser import Parser
from tqdm import tqdm


def normalize_title(title):
    title = '_'.join(title.split())
    if len(title) > 0:
        title = title[0].upper() + title[1:]
    return title


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


def iterate_xml_dump_parsed(source, metadata, early_stopping=-1):
    titles_in_ns0 = metadata['titles_in_ns0']

    if early_stopping == -1:
        pages_to_process = len(titles_in_ns0)
    else:
        pages_to_process = min(len(titles_in_ns0), early_stopping)

    parser = Parser()
    with tqdm(total=pages_to_process) as pbar:
        for tag in iterate_xml_dump(source, ('ns', 'redirect', 'title', 'revision/text')):
            ns = tag['ns'].text.strip()
            if ns == '0':
                if tag['redirect'] is not None:
                    title = normalize_title(tag['title'].text)
                    redirect_to = normalize_title(tag['redirect'].attrib['title'])
                    yield title, [], redirect_to, {}
                else:
                    title = tag['title'].text
                    title = normalize_title(title)
                    wikitext = tag['revision/text'].text
                    wikipedia_decisions = defaultdict(list)  # line: [link]
                    try:
                        wikitext_parsed = parser.parse(wikitext)
                        lines = wikitext_parsed['lines']
                        for parallel_tag in wikitext_parsed['tags']:
                            if parallel_tag['type'] == 'link':
                                destination = normalize_title(parallel_tag['attributes']['destination'])
                                line = parallel_tag['spans'][0]['line']
                                start = parallel_tag['spans'][0]['start']
                                length = parallel_tag['spans'][0]['length']
                                label = lines[line][start:start + length]
                                link = {
                                    'source': title,
                                    'destination': destination,
                                    'line': line,
                                    'start': start,
                                    'length': length,
                                    'label': label
                                }
                                wikipedia_decisions[line].append(link)
                        yield title, lines, None, wikipedia_decisions
                    except Exception as e:
                        print(f'cannot parse: {title}')

                pbar.set_description(f'parsing: {title[:25]: <25}')
                pbar.update(1)
                pages_to_process -= 1
                if pages_to_process <= 0:
                    return
