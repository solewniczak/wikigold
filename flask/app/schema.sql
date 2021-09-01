CREATE TABLE `dumps` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `lang` VARCHAR(10) NOT NULL,
    `date` CHAR(8) NOT NULL,
    `parser` VARCHAR(256) NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `articles` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `title` VARCHAR(256) NOT NULL,
    `caption` TEXT NULL,
    `redirect_to_title` VARCHAR(256) NULL,
    `redirect_to_id` INT UNSIGNED NULL,
    `dump_id` INT UNSIGNED NULL,
    `counter` INT UNSIGNED NOT NULL DEFAULT 0,
    FOREIGN KEY (`dump_id`) REFERENCES `dumps` (`id`),
    FOREIGN KEY (`redirect_to_id`) REFERENCES `articles` (`id`),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE INDEX articles_ix_title ON articles(title);

CREATE TABLE `lines` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `nr` INT UNSIGNED NOT NULL,
    `content` TEXT NOT NULL,
    `article_id` INT UNSIGNED NOT NULL,
    FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `edls` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `algorithm` JSON NOT NULL,
    `timestamp` TIMESTAMP NOT NULL,
    `author` VARCHAR(256) NOT NULL,
    `article_id` INT UNSIGNED NOT NULL,
    FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `decisions` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `edl_id` INT UNSIGNED NOT NULL,
    `source_line_id` INT UNSIGNED NOT NULL,
    `start` INT UNSIGNED NOT NULL,
    `length` INT UNSIGNED NOT NULL,
    `destination_article_id` INT UNSIGNED NULL,
    FOREIGN KEY (`source_line_id`) REFERENCES `lines` (`id`),
    FOREIGN KEY (`edl_id`) REFERENCES `edls` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`destination_article_id`) REFERENCES `articles` (`id`),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `labels` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `label` VARCHAR(256) NOT NULL,
    `counter` INT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `labels_articles` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `label_id` INT UNSIGNED NOT NULL,
    `title` VARCHAR(256) NOT NULL,
    `article_id` INT UNSIGNED NULL,  # we can have links to not existing articles
    `counter` INT UNSIGNED NOT NULL DEFAULT 0,
    FOREIGN KEY (`label_id`) REFERENCES `labels` (`id`),
    FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`),
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `config` (
    `name` VARCHAR(256) NOT NULL,
    `value` VARCHAR(1024) NOT NULL,
    PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;