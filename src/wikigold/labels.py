from .cache import get_cached_label
from flask import current_app
from nltk.corpus import stopwords


def get_label_titles_dict(candidate_labels, min_label_count=1, min_label_articles_count=1):
    candidate_labels_unique = set(map(lambda candidate_label: candidate_label['name'], candidate_labels))
    label_articles_dict = {}
    for label_name in candidate_labels_unique:
        label = get_cached_label(label_name)
        if label is not None and label['label_counter'] >= min_label_count:
            label_articles_dict[label_name] = label

    # apply filter on min L-A counter
    for label in label_articles_dict.values():
        label['articles'] = {article_id: article for article_id, article in label['articles'].items()
                             if article['label_article_counter'] >= min_label_articles_count}

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

    # get articles titles and captions from db
    # TODO: Maybe it will be better to replace it with ajax
    # db = get_db()
    # cursor = db.cursor(dictionary=True)
    # unique_articles_ids = set()
    # for label in label_articles_dict.values():
    #     unique_articles_ids.update(label['articles'].keys())
    #
    # article_ids_str = ','.join(map(str, unique_articles_ids))
    # sql = f'SELECT `id`, `title`, `caption` FROM `articles` WHERE `id` IN ({article_ids_str})'
    # cursor.execute(sql)
    # articles_dict = {row['id']: row for row in cursor}
    # label_titles_dict = {}
    # for label_name, label in label_articles_dict.items():
    #     titles = []
    #     for article_id, article in label['articles'].items():
    #         title = {
    #             'article_id': article_id,
    #             'title': articles_dict[article_id]['title'],
    #             'label_title_counter': article['label_article_counter'],
    #             'article_counter': article['article_counter'],
    #             'caption': articles_dict[article_id]['caption'],
    #         }
    #         if title['caption'] is not None:
    #             title['caption'] = title['caption'].decode('utf-8')
    #         titles.append(title)
    #     label_titles_dict[label_name] = {
    #         'counter': label['label_counter'],
    #         'titles': titles
    #     }
    #
    # return label_titles_dict


def get_labels_exact(lines, skip_stop_words=False, min_label_count=1, min_label_articles_count=1):
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

                if skip_stop_words and label in stops:
                    continue

                candidate_labels.append({
                    'name': label,
                    'line': line_nr,
                    'start': token_nr,
                    'ngrams': ngrams,
                })

    label_titles_dict = get_label_titles_dict(candidate_labels, min_label_count, min_label_articles_count)
    labels = []
    for candidate_label in candidate_labels:
        label_name = candidate_label['name']
        if label_name in label_titles_dict:
            candidate_label['label_counter'] = label_titles_dict[label_name]['label_counter']
            candidate_label['articles'] = label_titles_dict[label_name]['articles']
            labels.append(candidate_label)

    return labels
