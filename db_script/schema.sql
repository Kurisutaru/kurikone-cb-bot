create or replace table channel
(
    channel_id   bigint unsigned not null,
    guild_id     bigint unsigned not null,
    channel_type varchar(200)    null,
    constraint `PRIMARY`
        primary key (channel_id)
);

create or replace table channel_message
(
    channel_id bigint unsigned not null,
    message_id bigint unsigned not null,
    constraint `PRIMARY`
        primary key (channel_id),
    constraint channel_message_pk
        unique (channel_id)
);

create or replace table clan_battle_boss
(
    clan_battle_boss_id int auto_increment
        primary key,
    name                varchar(250) not null,
    description         varchar(250) null,
    image_path          varchar(250) not null,
    position            int          not null
);

create or replace table clan_battle_boss_book
(
    clan_battle_boss_book_id     bigint unsigned auto_increment
        primary key,
    clan_battle_boss_entry_id    bigint unsigned not null,
    guild_id                     bigint unsigned not null,
    player_id                    bigint unsigned not null,
    player_name                  varchar(2000)   not null,
    attack_type                  varchar(20)     not null,
    damage                       bigint unsigned null,
    clan_battle_overall_entry_id int             null,
    leftover_time                int             null,
    entry_date                   datetime        not null
);

create or replace table clan_battle_boss_entry
(
    clan_battle_boss_entry_id int auto_increment
        primary key,
    guild_id                  bigint unsigned not null,
    message_id                bigint unsigned not null,
    clan_battle_period_id     int             not null,
    clan_battle_boss_id       int             not null,
    name                      varchar(2000)   not null,
    image_path                varchar(2000)   not null,
    boss_round                bigint unsigned not null,
    current_health            bigint unsigned not null,
    max_health                bigint unsigned not null
);

create or replace table clan_battle_boss_health
(
    clan_battle_boss_health_id int auto_increment
        primary key,
    position                   int             not null,
    round_from                 int             not null,
    round_to                   int             not null,
    health                     bigint unsigned not null
);

create or replace table clan_battle_overall_entry
(
    clan_battle_overall_entry_id int auto_increment
        primary key,
    guild_id                     bigint unsigned not null,
    clan_battle_period_id        int             not null,
    clan_battle_boss_id          int             not null,
    player_id                    bigint unsigned not null,
    player_name                  varchar(2000)   not null,
    boss_round                   int             not null,
    damage                       int             not null,
    attack_type                  varchar(20)     not null,
    leftover_time                int             null,
    overall_leftover_entry_id    int             null,
    entry_date                   datetime        not null
);

create or replace table clan_battle_period
(
    clan_battle_period_id   int auto_increment
        primary key,
    clan_battle_period_name varchar(2000) not null,
    date_from               datetime      not null,
    date_to                 datetime      not null,
    boss1_id                int           not null,
    boss2_id                int           not null,
    boss3_id                int           not null,
    boss4_id                int           not null,
    boss5_id                int           not null
);

create or replace table clan_battle_report_message
(
    clan_battle_report_message_id int auto_increment
        primary key,
    guild_id                      bigint unsigned not null,
    clan_battle_period_id         int             not null,
    message_id                    bigint unsigned not null,
    day                           int             not null
);

create or replace table guild
(
    guild_id   bigint unsigned not null,
    guild_name varchar(2000)   not null,
    constraint `PRIMARY`
        primary key (guild_id),
    constraint `UNIQUE`
        unique (guild_id)
);

create or replace table guild_player
(
    guild_id    bigint unsigned not null,
    player_id   bigint unsigned not null,
    player_name varchar(200)    not null,
    constraint `PRIMARY`
        primary key (guild_id, player_id)
);

