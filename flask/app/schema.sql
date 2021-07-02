CREATE TABLE `dumps` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `name` varchar(255) NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `articles` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `title` varchar(255) NOT NULL,
    `parser_name` varchar(255) NOT NULL,
    `dump_id` int(11) NULL,
    CONSTRAINT `fk_articles_dumps`
        FOREIGN KEY (`dump_id`) REFERENCES `dumps` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `lines` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `nr` int(11) NOT NULL,
    `article_id` int(11) NOT NULL,
    CONSTRAINT `fk_lines_articles`
        FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `tokens` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `nr` int(11) NOT NULL,
    `token` varchar(255) NOT NULL,
    `line_id` int(11) NOT NULL,
    CONSTRAINT `fk_tokens_lines`
        FOREIGN KEY (`line_id`) REFERENCES `lines` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `edls` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `method` varchar(255) NOT NULL,
    `params` varchar(1024) NOT NULL,
    `author` varchar(255) NOT NULL,
    `article_id` int(11) NOT NULL,
    CONSTRAINT `fk_edls_articles`
        FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;


CREATE TABLE `decisions` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `target_article_id` int(11) NOT NULL,
    `edl_id` int(11) NOT NULL,
    CONSTRAINT `fk_decisions_articles`
        FOREIGN KEY (`target_article_id`) REFERENCES `articles` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    CONSTRAINT `fk_decisions_edls`
        FOREIGN KEY (`edl_id`) REFERENCES `edls` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `tokens_decisions` (
    `token_id` int(11) NOT NULL,
    `decision_id` int(11) NOT NULL,
    CONSTRAINT `fk_token_decision_token`
        FOREIGN KEY (`token_id`) REFERENCES `tokens` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    CONSTRAINT `fk_tokens_decisions_decisions`
        FOREIGN KEY (`decision_id`) REFERENCES `decisions` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`token_id`, `decision_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `labels` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `label` varchar(255) NOT NULL,
    `counter` int(11) NOT NULL DEFAULT 0,
    `article_id` int(11) NOT NULL,
    CONSTRAINT `fk_labels_articles`
        FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
