CREATE TABLE `dump` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `name` varchar(255) COLLATE utf8_bin NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=1 ;

CREATE TABLE `article` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `title` varchar(255) COLLATE utf8_bin NOT NULL,
    `parser_name` varchar(255) COLLATE utf8_bin NOT NULL,
    `dump_id` int(11) NULL,
    CONSTRAINT `fk_article_dump`
        FOREIGN KEY (`dump_id`) REFERENCES dump (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=1 ;

CREATE TABLE `line` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `nr` int(11) NOT NULL,
    `article_id` int(11) NOT NULL,
    CONSTRAINT `fk_line_article`
        FOREIGN KEY (`article_id`) REFERENCES article (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=1 ;

CREATE TABLE `token` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `nr` int(11) NOT NULL,
    `token` varchar(255) COLLATE utf8_bin NOT NULL,
    `line_id` int(11) NOT NULL,
    CONSTRAINT `fk_token_line`
        FOREIGN KEY (`line_id`) REFERENCES line (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=1 ;

CREATE TABLE `edl` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `method` varchar(255) COLLATE utf8_bin NOT NULL,
    `params` varchar(1024) COLLATE utf8_bin NOT NULL,
    `author` varchar(255) COLLATE utf8_bin NOT NULL,
    `article_id` int(11) NOT NULL,
    CONSTRAINT `fk_edl_article`
        FOREIGN KEY (`article_id`) REFERENCES article (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=1 ;


CREATE TABLE `decision` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `target_article_id` int(11) NOT NULL,
    `edl_id` int(11) NOT NULL,
    CONSTRAINT `fk_decision_article`
        FOREIGN KEY (`target_article_id`) REFERENCES article (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    CONSTRAINT `fk_decision_edl`
        FOREIGN KEY (`edl_id`) REFERENCES edl (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=1 ;

CREATE TABLE `label` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `label` varchar(255) COLLATE utf8_bin NOT NULL,
    `counter` int(11) NOT NULL DEFAULT 0,
    `article_id` int(11) NOT NULL,
    CONSTRAINT `fk_edl_article`
        FOREIGN KEY (`article_id`) REFERENCES article (`id`)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=1 ;