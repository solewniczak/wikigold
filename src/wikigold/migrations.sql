ALTER TABLE wikipedia_decisions
ADD
    source_article_id INT UNSIGNED NOT NULL
    AFTER id;

UPDATE `wikipedia_decisions` INNER JOIN `lines` ON `wikipedia_decisions`.`source_line_id`=`lines`.`id`
                SET `wikipedia_decisions`.`source_article_id` = `lines`.`article_id`
                WHERE `wikipedia_decisions`.`dump_id`=1;

ALTER TABLE `wikipedia_decisions` ADD CONSTRAINT FOREIGN KEY (`source_article_id`) REFERENCES `articles` (`id`);

ALTER TABLE dumps ADD  `articles_count` INT UNSIGNED NOT NULL DEFAULT 0 AFTER `labels_count`;
UPDATE `dumps` SET `articles_count`=(SELECT COUNT(*) FROM articles WHERE `dump_id`=1 AND `redirect_to_title` IS NULL)
                                                WHERE `id`=1

ALTER TABLE dumps ADD  `wikipedia_decisions_count` INT UNSIGNED NOT NULL DEFAULT 0 AFTER `articles_count`;
UPDATE `dumps` SET `wikipedia_decisions_count`=(SELECT COUNT(*) FROM `wikipedia_decisions` WHERE `dump_id`=1)
                                                WHERE `id`=1;