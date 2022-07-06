from .cache import get_cached_label
from flask import current_app
from nltk.corpus import stopwords


def count_tokens_in_lines(lines):
    return sum([len(line['tokens']) for line in lines])


def apply_links_to_text_ratio(lines, labels, rate_keywords_by, links_to_text_ratio):
    """Left only the labels with the highest `rate_keywords_by` attribute.
    The number of selected labels is defined as a ratio between plain text and linked text.
    The function doesn't clean the overlapping links.
    If there is several links over one token they are counted as one when the ratio is applied."""

    tokens_in_text = count_tokens_in_lines(lines)
    tokens_to_links = int(links_to_text_ratio * tokens_in_text)
    labels_sorted = sorted(labels, key=lambda label: label['keyphraseness'], reverse=True)
    labels_overlap = {}  # store information about labels overlapping
    labels_left = []
    for label in labels_sorted:
        # mark label's tokens as overlaps
        for ngram_idx in range(label['start'], label['start'] + label['ngrams']):
            if (label['line'], ngram_idx) not in labels_overlap:
                labels_overlap[label['line'], ngram_idx] = True
                tokens_to_links -= 1
        labels_left.append(label)
        if tokens_to_links <= 0:
            break

    return labels_left


def get_label_titles_dict(candidate_labels, algorithm_normalized_json):
    """Return a dictionary for all labels found in the article. The dictionary gets the labels' statistics from the cache.
    The dictionary maps label_name to {'label_counter': int, 'keyphraseness': int, 'articles': {...}}"""
    candidate_labels_unique = set(map(lambda candidate_label: candidate_label['name'], candidate_labels))
    label_articles_dict = {}
    for label_name in candidate_labels_unique:
        label = get_cached_label(label_name)
        if label is not None:
            if label['appeared_in'] != 0:
                label['keyphraseness'] = label['as_link_in']/label['appeared_in']
            else:
                label['keyphraseness'] = 0.0
            if label['label_counter'] >= algorithm_normalized_json['min_label_count'] and \
                    label['keyphraseness'] >= algorithm_normalized_json['min_keyphraseness']:
                label_articles_dict[label_name] = label

    # apply filter on min L-A counter
    for label in label_articles_dict.values():
        label['articles'] = {article_id: article for article_id, article in label['articles'].items()
                             if article['label_article_counter'] >= algorithm_normalized_json['min_label_articles_count']}

    # Remove labels with empty titles
    label_articles_dict = {label_name: label for label_name, label in label_articles_dict.items()
                           if len(label['articles']) > 0}

    # it's more natural for JS to have articles as list, not dictionary
    for label in label_articles_dict.values():
        label['articles'] = [{'article_id': article_id,
                              'article_counter': article['article_counter'],
                              'label_article_counter': article['label_article_counter'],
                              } for article_id, article in label['articles'].items()]

    return label_articles_dict


def get_labels_exact(lines, algorithm_normalized_json):
    stops = set(stopwords.words('english'))

    candidate_labels = []
    for ngrams in range(1, current_app.config['MAX_NGRAMS'] + 1):
        for line_nr, line in enumerate(lines):
            line_content = line['content']
            line_tokens = line['tokens']
            for token_nr, token in enumerate(line_tokens):
                # cannot construct ngram of length "ngrams" starting from "token"
                if token_nr + ngrams > len(line_tokens):
                    break

                # continuous ngram model
                label_start = line_tokens[token_nr][0]  # begin of the first gram
                label_end = line_tokens[token_nr + ngrams - 1][1]  # end of the last gram
                label = line_content[label_start:label_end]

                if algorithm_normalized_json['skip_stop_words'] and label in stops:
                    continue

                candidate_labels.append({
                    'name': label,
                    'line': line_nr,
                    'start': token_nr,
                    'ngrams': ngrams,
                })

    label_titles_dict = get_label_titles_dict(candidate_labels, algorithm_normalized_json)
    labels = []
    for candidate_label in candidate_labels:
        label_name = candidate_label['name']
        if label_name in label_titles_dict:
            candidate_label['label_counter'] = label_titles_dict[label_name]['label_counter']
            candidate_label['articles'] = label_titles_dict[label_name]['articles']
            # put here label from the labels dictionary to all lables
            candidate_label['keyphraseness'] = label_titles_dict[label_name]['keyphraseness']
            labels.append(candidate_label)

    # Apply keyword ratings if specified
    if algorithm_normalized_json['rate_keywords_by'] != '':
        labels = apply_links_to_text_ratio(lines, labels, algorithm_normalized_json['rate_keywords_by'], algorithm_normalized_json['links_to_text_ratio'])

    return labels
