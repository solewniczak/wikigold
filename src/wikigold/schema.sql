CREATE TABLE `users` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(255) UNIQUE NOT NULL,
  `password` CHAR(120) NOT NULL,
  `superuser` BOOLEAN DEFAULT FALSE,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `dumps` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `lang` CHAR(10) NOT NULL,
    `date` CHAR(8) NOT NULL,
    `parser_name` CHAR(30) NOT NULL,
    `parser_version` CHAR(30) NOT NULL,
    `timestamp` TIMESTAMP NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `articles` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `caption` LONGTEXT NULL,
    `redirect_to_title` VARCHAR(255) NULL,
    `redirect_to_id` INT UNSIGNED NULL,
    `dump_id` INT UNSIGNED NULL,
    `counter` INT UNSIGNED NOT NULL DEFAULT 0,
    FOREIGN KEY (`dump_id`) REFERENCES `dumps` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`redirect_to_id`) REFERENCES `articles` (`id`) ON DELETE CASCADE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE INDEX articles_ix_title ON articles(title);

CREATE TABLE `lines` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `nr` INT UNSIGNED NOT NULL,
    `content` LONGTEXT NOT NULL,
    `article_id` INT UNSIGNED NOT NULL,
    FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`) ON DELETE CASCADE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `edls` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `algorithm` JSON NOT NULL,
    `timestamp` TIMESTAMP NOT NULL,
    `user_id` INT UNSIGNED NOT NULL,
    `article_id` INT UNSIGNED NOT NULL,
    `knowledge_base_id` INT UNSIGNED NOT NULL,
    FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`knowledge_base_id`) REFERENCES `dumps`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `decisions` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `edl_id` INT UNSIGNED NOT NULL,
    `source_line_id` INT UNSIGNED NOT NULL,
    `start` INT UNSIGNED NOT NULL,
    `length` INT UNSIGNED NOT NULL,
    `destination_article_id` INT UNSIGNED NULL,
    FOREIGN KEY (`source_line_id`) REFERENCES `lines` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`edl_id`) REFERENCES `edls` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`destination_article_id`) REFERENCES `articles` (`id`) ON DELETE CASCADE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `wikipedia_decisions` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `source_line_id` INT UNSIGNED NOT NULL,
    `start` INT UNSIGNED NOT NULL,
    `length` INT UNSIGNED NOT NULL,
    `destination_title` VARCHAR(255) NOT NULL,
    `destination_article_id` INT UNSIGNED NULL,
    `dump_id` INT UNSIGNED NULL,
    FOREIGN KEY (`source_line_id`) REFERENCES `lines` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`destination_article_id`) REFERENCES `articles` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`dump_id`) REFERENCES `dumps` (`id`) ON DELETE CASCADE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `labels` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `label` VARCHAR(255) NOT NULL,
    `dump_id` INT UNSIGNED NULL,
    `counter` INT UNSIGNED NOT NULL DEFAULT 0,
    FOREIGN KEY (`dump_id`) REFERENCES `dumps` (`id`) ON DELETE CASCADE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `labels_articles` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `label_id` INT UNSIGNED NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `article_id` INT UNSIGNED NULL,  # we can have links to not existing articles
    `counter` INT UNSIGNED NOT NULL DEFAULT 0,
    FOREIGN KEY (`label_id`) REFERENCES `labels` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`) ON DELETE CASCADE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
