import click
from flask.cli import with_appcontext


@click.command('evaluate')
@click.argument('evaluate_config_path')
@with_appcontext
def evaluate(evaluate_config_path):
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
        data = (ground_truth_name, )
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

        sql = 'SELECT `id` FROM `articles` WHERE dump_id=%s'
        data = (dump_id,)
        cursor.execute(sql, data)
        articles_ids = [row['id'] for row in cursor]
    else:
        raise Exception('cannot find specified dump')

    algorithm_normalized_json_key, algorithm_normalized_json = normalize_algorithm_json(run_config['algorithm'])
    avg_precision = 0.0
    avg_recall = 0.0
    avg_fscore = 0.0
    for article_id in articles_ids:
        lines = get_lines(article_id)
        labels = wikification(lines, algorithm_normalized_json)
        labels_decisions_ids = {label['decision'] for label in labels if 'decision' in label}

        ground_truth_decisions = get_ground_truth_decisions(article_id, ground_truth_id)
        ground_truth_decisions_ids = {ground_truth_decision['destination_article_id']
                                      for ground_truth_decision in ground_truth_decisions
                                      if 'destination_article_id' in ground_truth_decision}

        true_positives = len(labels_decisions_ids & ground_truth_decisions_ids)
        precision = true_positives/len(labels_decisions_ids)
        recall = true_positives/len(ground_truth_decisions_ids)
        fscore = 2 * precision * recall / (precision+recall)
        print(f'precision: {precision} recall: {recall} fscore: {fscore}')

        avg_precision += precision
        avg_recall += recall
        avg_fscore += fscore

    avg_precision /= len(articles_ids)
    avg_recall /= len(articles_ids)
    avg_fscore /= len(articles_ids)

    print(f'avg precision: {avg_precision} avg recall: {avg_recall} avg fscore: {avg_fscore}')

def init_app(app):
    app.cli.add_command(evaluate)
