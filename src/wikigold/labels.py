from .cache import get_cached_label, get_cached_label_titles, add_label_titles_to_cache
from .db import get_db
from flask import current_app, g
from nltk.corpus import stopwords


def get_label_titles_dict(dump_id, candidate_labels, min_label_count=1, min_label_articles_count=1):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    candidate_labels_unique = set(map(lambda candidate_label: candidate_label['name'], candidate_labels))
    candidate_labels_dict = {}

    for label_name in candidate_labels_unique:
        label_data = get_cached_label(label_name)
        if label_data is not None:
            label_id, label_counter = label_data
            if label_counter >= min_label_count:
                candidate_labels_dict[label_id] = {'label_name': label_name, 'label_counter': label_counter}

    no_cached_labels_ids = []
    label_titles_dict = {}
    # loads label_titles from cache
    for label_id, label_data in candidate_labels_dict.items():
        label_name = label_data['label_name']
        label_counter = label_data['label_counter']

        label_titles = get_cached_label_titles(label_name)
        if label_titles is None:
            no_cached_labels_ids.append(label_id)
        else:
            label_titles_dict[label_name] = {
                'counter': label_counter,
                'titles': label_titles
            }

    if len(no_cached_labels_ids) > 0:
        no_cached_labels_ids_str = ','.join([str(label_id) for label_id in no_cached_labels_ids])

        sql = f'''SELECT `labels_articles`.`label_id`, `labels_articles`.`article_id`, `labels_articles`.`title`,
                        `labels_articles`.`counter` AS `label_title_counter`, `articles`.`counter` AS `article_counter`,
                        `articles`.`caption`, `articles`.`redirect_to_title`
                        FROM `labels_articles` JOIN `articles` ON `articles`.`id` = `labels_articles`.`article_id`
                        WHERE `labels_articles`.`label_id` IN ({no_cached_labels_ids_str})'''
        cursor.execute(sql)

        label_titles_from_db_dict = {}
        for row in cursor:
            label_data = candidate_labels_dict[row['label_id']]
            label_name = label_data['label_name']
            label_counter = label_data['label_counter']

            if label_name not in label_titles_from_db_dict:
                label_titles_from_db_dict[label_name] = {
                    'counter': label_counter,
                    'titles': []
                }

            title = {
                'article_id': row['article_id'],
                'title': row['title'],
                'label_title_counter': row['label_title_counter'],
                'article_counter': row['article_counter'],
                'caption': row['caption'],
                'redirect_to_title': row['redirect_to_title']
            }
            if title['caption'] is not None:
                title['caption'] = title['caption'].decode('utf-8')
            label_titles_from_db_dict[label_name]['titles'].append(title)
        cursor.close()

        # add missing label_titles to cache
        for label_name, label_data in label_titles_from_db_dict.items():
            add_label_titles_to_cache(label_name, label_data['titles'])

        label_titles_dict.update(label_titles_from_db_dict)

    # apply filter on min L-A counter
    for label_data in label_titles_dict.values():
        label_data['titles'] = [title for title in label_data['titles'] if title['label_title_counter'] >= min_label_articles_count]

    # Remove labels with empty titles
    label_titles_dict = {label_name: label_data for label_name, label_data in label_titles_dict.items()
                         if len(label_data['titles']) > 0}

    return label_titles_dict


def get_labels_exact(lines, knowledge_base, skip_stop_words=False, min_label_count=1, min_label_articles_count=1):
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
                label_end = line_tokens[token_nr + ngrams - 1][1] # end of the last gram
                label = line_content[label_start:label_end]

                if skip_stop_words and label in stops:
                    continue

                candidate_labels.append({
                    'name': label,
                    'line': line_nr,
                    'start': token_nr,
                    'ngrams': ngrams,
                })

    label_titles_dict = get_label_titles_dict(knowledge_base, candidate_labels, min_label_count, min_label_articles_count)
    labels = []
    for candidate_label in candidate_labels:
        label_name = candidate_label['name']
        if label_name in label_titles_dict:
            candidate_label['counter'] = label_titles_dict[label_name]['counter']
            candidate_label['titles'] = label_titles_dict[label_name]['titles']
            labels.append(candidate_label)

    return labels
