import click
from flask.cli import with_appcontext


def ground_truth_resolve_redirects(ground_truth_decisions):
    from .db import get_db

    db = get_db()
    cursor = db.cursor(dictionary=True)

    for ground_truth_decision in ground_truth_decisions:
        id = ground_truth_decision['destination_article_id']
        title = ground_truth_decision['destination_title']
        while True:
            sql = 'SELECT `redirect_to_id`, `redirect_to_title` FROM `articles` WHERE `id`=%s'
            data = (id, )
            cursor.execute(sql, data)
            result = cursor.fetchone()
            if result['redirect_to_id'] is None:
                break
            id = result['redirect_to_id']
            title = result['redirect_to_title']
        ground_truth_decision['destination_article_id'] = id
        ground_truth_decision['destination_title'] = title

    return ground_truth_decisions


@click.command('evaluate')
@click.argument('evaluate_config_path')
@click.option("-i", "--individual", is_flag=True,
              help="Show individual precision/recall for each ground truth article.")
@click.option("-u", "--unknown-labels", is_flag=True, help="Show unknown labels.")
@click.option("-d", "--disambiguation-errors", is_flag=True,
              help="Show disambiguation errors. The disambiguation error is when the "
                   "algorithm decision and ground truth links to same label but with"
                   " different destination title.")
@click.option("-r", "--resolve-redirects", is_flag=True, help="Resolve redirects for ground truth links.")
@with_appcontext
def evaluate(evaluate_config_path, individual, unknown_labels, disambiguation_errors, resolve_redirects):
    import yaml

    from .db import get_db
    from .helper import get_lines, normalize_algorithm_json, wikification, get_ground_truth_decisions

    db = get_db()
    cursor = db.cursor(dictionary=True)

    with open(evaluate_config_path, 'r') as fp:
        run_config = yaml.safe_load(fp)

    if 'ground_truth_name' in run_config['ground_truth']:
        ground_truth_name = run_config['ground_truth']['ground_truth_name']
        sql = 'SELECT `id` FROM `ground_truth` WHERE `name`=%s'
        data = (ground_truth_name,)
        cursor.execute(sql, data)
        results = cursor.fetchall()
        if len(results) == 0:
            raise Exception(f'cannot find ground truth with name "{ground_truth_name}"')
        elif len(results) > 1:
            raise Exception(f'ground truth name "{ground_truth_name}" ambiguous')
        ground_truth_id = results[0]['id']
    else:
        raise Exception('cannot find specified ground truth')

    # select articles ids for evaluation
    if 'dump_name' in run_config['articles']:
        dump_name = run_config['articles']['dump_name']
        sql = 'SELECT `id` FROM `dumps` WHERE `name`=%s'
        data = (dump_name,)
        cursor.execute(sql, data)
        results = cursor.fetchall()
        if len(results) == 0:
            raise Exception(f'cannot find dump with name "{dump_name}"')
        elif len(results) > 1:
            raise Exception(f'dump name "{dump_name}" ambiguous')
        dump_id = results[0]['id']

        sql = 'SELECT `id`, `title` FROM `articles` WHERE dump_id=%s'
        data = (dump_id,)
        cursor.execute(sql, data)
        articles = cursor.fetchall()
    else:
        raise Exception('cannot find specified dump')

    algorithm_normalized_json_key, algorithm_normalized_json = normalize_algorithm_json(run_config['algorithm'])
    avg_precision = 0.0
    avg_recall = 0.0
    avg_fscore = 0.0
    for article in articles:
        lines = get_lines(article['id'])

        # run algorithm
        algorithm_decisions = wikification(lines, algorithm_normalized_json)
        algorithm_decisions_articles_ids = {algorithm_decision['decision']
                                            for algorithm_decision in algorithm_decisions
                                            if 'decision' in algorithm_decision}
        # get algorithm's decisions titles
        articles_ids_str = ','.join(map(str, algorithm_decisions_articles_ids))
        sql = f'SELECT `id`, `title` FROM `articles` WHERE `id` IN ({articles_ids_str})'
        cursor.execute(sql)
        algorithm_decisions_id_title = {row['id']: row['title'] for row in cursor}

        # map algorithms decisions ids to titles
        algorithm_decisions_label_title = {algorithm_decision['name']:
                                               algorithm_decisions_id_title[algorithm_decision['decision']]
                                           for algorithm_decision in algorithm_decisions
                                           if 'decision' in algorithm_decision}

        ground_truth_decisions = get_ground_truth_decisions(article['id'], ground_truth_id)
        if resolve_redirects:
            ground_truth_resolve_redirects(ground_truth_decisions)
        ground_truth_decisions_ids = {ground_truth_decision['destination_article_id']
                                      for ground_truth_decision in ground_truth_decisions
                                      if 'destination_article_id' in ground_truth_decision}

        # map ground truth labels decisions to titles
        ground_truth_label_title = {ground_truth_decision['label']: ground_truth_decision['destination_title']
                                    for ground_truth_decision in ground_truth_decisions
                                    if 'destination_article_id' in ground_truth_decision}
        true_positives = len(algorithm_decisions_articles_ids & ground_truth_decisions_ids)
        precision = true_positives / len(algorithm_decisions_articles_ids)
        recall = true_positives / len(ground_truth_decisions_ids)
        fscore = 2 * precision * recall / (precision + recall)

        avg_precision += precision
        avg_recall += recall
        avg_fscore += fscore

        if individual:
            print(article['title'])
            print(f'precision: {precision} recall: {recall} fscore: {fscore}')

        if unknown_labels:  # show unknown labels
            unknown_labels = [ground_truth_decision['label']
                              for ground_truth_decision in ground_truth_decisions
                              if ground_truth_decision['label_id'] is None]
            print('unknown labels', unknown_labels)

        if disambiguation_errors:
            for ground_truth_label, groud_truth_title in ground_truth_label_title.items():
                if ground_truth_label in algorithm_decisions_label_title and \
                        algorithm_decisions_label_title[ground_truth_label] != groud_truth_title:
                    algorithm_decision_title = algorithm_decisions_label_title[ground_truth_label]
                    print(f'{ground_truth_label} -> is "{algorithm_decision_title}", should be "{groud_truth_title}"')

    avg_precision /= len(articles)
    avg_recall /= len(articles)
    avg_fscore /= len(articles)

    print(f'avg precision: {avg_precision} avg recall: {avg_recall} avg fscore: {avg_fscore}')


def init_app(app):
    app.cli.add_command(evaluate)
