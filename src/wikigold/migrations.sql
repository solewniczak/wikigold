ALTER TABLE wikipedia_decisions
ADD
    source_article_id INT UNSIGNED NOT NULL
    AFTER id;

UPDATE `wikipedia_decisions` INNER JOIN `lines` ON `wikipedia_decisions`.`source_line_id`=`lines`.`id`
                SET `wikipedia_decisions`.`source_article_id` = `lines`.`article_id`
                WHERE `wikipedia_decisions`.`dump_id`=1;

ALTER TABLE `wikipedia_decisions` ADD CONSTRAINT FOREIGN KEY (`source_article_id`) REFERENCES `articles` (`id`);