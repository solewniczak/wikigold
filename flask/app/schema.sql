CREATE TABLE `dumps` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(256) NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `articles` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `title` VARCHAR(256) NOT NULL,
    `parser_name` VARCHAR(256) NOT NULL,
    `dump_id` INT UNSIGNED NULL,
    CONSTRAINT `fk_articles_dumps`
        FOREIGN KEY (`dump_id`) REFERENCES `dumps` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `lines` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `nr` INT UNSIGNED NOT NULL,
    `content` TEXT NOT NULL,
    `article_id` INT UNSIGNED NOT NULL,
    CONSTRAINT `fk_lines_articles`
        FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE `edls` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `method` VARCHAR(256) NOT NULL,
    `params` VARCHAR(1024) NOT NULL,
    `author` VARCHAR(256) NOT NULL,
    `article_id` INT UNSIGNED NOT NULL,
    CONSTRAINT `fk_edls_articles`
        FOREIGN KEY (`article_id`) REFERENCES `articles` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;


CREATE TABLE `decisions` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `edl_id` INT UNSIGNED NOT NULL,
    `target_line_id` INT UNSIGNED NOT NULL,
    `start` INT UNSIGNED NOT NULL,
    `length` INT UNSIGNED NOT NULL,
    CONSTRAINT `fk_decisions_lines`
        FOREIGN KEY (`target_line_id`) REFERENCES `lines` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    CONSTRAINT `fk_decisions_edls`
        FOREIGN KEY (`edl_id`) REFERENCES `edls` (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;


CREATE TABLE `labels` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `label` VARCHAR(256) NOT NULL,
    `counter` INT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
