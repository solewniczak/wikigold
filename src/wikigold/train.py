import random

import click
from flask.cli import with_appcontext


@click.command('wikipediaminer-select-random-articles')
@click.argument('articles_path')
@click.argument('dump_id', type=int)
@click.argument('ground_truth_id', type=int)
@click.option('-n', '--number-of-articles', type=int, default=700, help="number of articles to retrieve")
@click.option('-m', '--min-links-count', type=int, default=50,
              help="minimal number of links in article to include it in the result")
@click.option('--skip-lists/--no-skip-lists', default=True, help="skip list and disambiguation pages")
@click.option('-s', '--seed', type=int, default=None, help="random seed")
@with_appcontext
def wikipediaminer_select_random_articles(articles_path, dump_id, ground_truth_id, number_of_articles, min_links_count, skip_lists, seed):
    import json

    from .db import get_db
    from .helper import get_ground_truth_decisions
    from tqdm import tqdm

    db = get_db()
    cursor = db.cursor(dictionary=True)
    sql = 'SELECT `id` FROM `articles` WHERE redirect_to_title IS NULL AND dump_id=%s'
    data = (dump_id,)
    cursor.execute(sql, data)
    articles_ids = [row['id'] for row in cursor]
    print(f'total articles: {len(articles_ids)}')

    random.seed(seed)
    random.shuffle(articles_ids)

    articles = []
    with tqdm(total=number_of_articles) as pbar:
        for article_id in articles_ids:
            # lines = get_lines(article_id)
            ground_truth_decisions = get_ground_truth_decisions(article_id, ground_truth_id)
            if len(ground_truth_decisions) >= min_links_count:
                articles.append(ground_truth_decisions)
                number_of_articles -= 1
                pbar.update(1)
            if number_of_articles == 0:
                break

    with open(articles_path, 'w') as fp:
        json.dump(articles, fp)


@click.command('wikipediaminer-train-disambiguator')
@click.argument('model_path')
@click.argument('articles_path')
@click.option('-m', '--min-sense-probability', type=float, default=0.02,
              help="don't consider senses below this threshold")
@click.option('-t', '--train-split', type=float, default=0.8,
              help="fraction of article used as train data")
@with_appcontext
def wikipediaminer_train_disambiguator(model_path, articles_path, min_sense_probability, train_split):
    import json

    from .helper import normalize_algorithm_json
    from .retrieval import get_label_titles_dict
    from .disambiguation import apply_relatedness_to_label_titles_dict

    print(model_path)
    with open(articles_path, 'r') as fp:
        articles = json.load(fp)

    data = []
    labels = []
    _, algorithm_normalized_json = normalize_algorithm_json({'min_sense_probability': min_sense_probability})
    for article_ground_truth_decisions in articles:
        # use article ground truths as entity retrieval stage
        ground_truth_label_title = {ground_truth_decision['label']: ground_truth_decision['destination_title']
                                    for ground_truth_decision in article_ground_truth_decisions}
        candidate_labels = [{'name': label} for label in ground_truth_label_title.keys()]
        labels_titles_dict = get_label_titles_dict(candidate_labels, algorithm_normalized_json)
        try:
            apply_relatedness_to_label_titles_dict(labels_titles_dict)
        except Exception:
            print('no context terms for the article')
            continue



def init_app(app):
    app.cli.add_command(wikipediaminer_select_random_articles)
    app.cli.add_command(wikipediaminer_train_disambiguator)
