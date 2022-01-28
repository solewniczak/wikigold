def commonness(labels):
    for label in labels:
        most_common_article = max(label['titles'], key=lambda title: title['article_counter'])
        label['decision'] = most_common_article['article_id']