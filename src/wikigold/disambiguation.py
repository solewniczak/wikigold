def commonness(labels):
    for label in labels:
        most_common_article = max(label['titles'], key=lambda title: title['article_counter'])
        label['disambiguation'] = {
            'article_id': most_common_article['article_id'],
            'rating': most_common_article['article_counter'],
            'features': {
                'commonness': most_common_article['article_counter']
            }
        }
        label['decision'] = label['disambiguation']['article_id']
