/*M!999999\- enable the sandbox mode */
-- MariaDB dump 10.19-11.4.5-MariaDB, for Win64 (AMD64)
--
-- Host: 127.0.0.1    Database: KurikoneCbBot
-- ------------------------------------------------------
-- Server version	11.4.5-MariaDB-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Table structure for table `channel`
--

DROP TABLE IF EXISTS `channel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `channel` (
  `channel_id` bigint(20) unsigned NOT NULL,
  `guild_id` bigint(20) unsigned NOT NULL,
  `channel_type` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`channel_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `channel_message`
--

DROP TABLE IF EXISTS `channel_message`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `channel_message` (
  `channel_id` bigint(20) unsigned NOT NULL,
  `message_id` bigint(20) unsigned NOT NULL,
  PRIMARY KEY (`channel_id`),
  UNIQUE KEY `channel_message_pk` (`channel_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `clan_battle_boss`
--

DROP TABLE IF EXISTS `clan_battle_boss`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `clan_battle_boss` (
  `clan_battle_boss_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(250) NOT NULL,
  `description` varchar(250) DEFAULT NULL,
  `image_path` varchar(250) NOT NULL,
  `position` int(11) NOT NULL,
  PRIMARY KEY (`clan_battle_boss_id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=56 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `clan_battle_boss_book`
--

DROP TABLE IF EXISTS `clan_battle_boss_book`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `clan_battle_boss_book` (
  `clan_battle_boss_book_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `clan_battle_boss_entry_id` bigint(20) unsigned NOT NULL,
  `guild_id` bigint(20) unsigned NOT NULL,
  `player_id` bigint(20) unsigned NOT NULL,
  `player_name` varchar(2000) NOT NULL,
  `attack_type` varchar(20) NOT NULL,
  `damage` bigint(20) unsigned DEFAULT NULL,
  `clan_battle_overall_entry_id` int(11) DEFAULT NULL,
  `leftover_time` int(11) DEFAULT NULL,
  `entry_date` datetime NOT NULL,
  PRIMARY KEY (`clan_battle_boss_book_id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `clan_battle_boss_entry`
--

DROP TABLE IF EXISTS `clan_battle_boss_entry`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `clan_battle_boss_entry` (
  `clan_battle_boss_entry_id` int(11) NOT NULL AUTO_INCREMENT,
  `guild_id` bigint(20) unsigned NOT NULL,
  `message_id` bigint(20) unsigned NOT NULL,
  `clan_battle_period_id` int(11) NOT NULL,
  `clan_battle_boss_id` int(11) NOT NULL,
  `name` varchar(2000) NOT NULL,
  `image_path` varchar(2000) NOT NULL,
  `boss_round` bigint(20) unsigned NOT NULL,
  `current_health` bigint(20) unsigned NOT NULL,
  `max_health` bigint(20) unsigned NOT NULL,
  PRIMARY KEY (`clan_battle_boss_entry_id`)
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `clan_battle_boss_health`
--

DROP TABLE IF EXISTS `clan_battle_boss_health`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `clan_battle_boss_health` (
  `clan_battle_boss_health_id` int(11) NOT NULL AUTO_INCREMENT,
  `position` int(11) NOT NULL,
  `round_from` int(11) NOT NULL,
  `round_to` int(11) NOT NULL,
  `health` bigint(20) unsigned NOT NULL,
  PRIMARY KEY (`clan_battle_boss_health_id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `clan_battle_overall_entry`
--

DROP TABLE IF EXISTS `clan_battle_overall_entry`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `clan_battle_overall_entry` (
  `clan_battle_overall_entry_id` int(11) NOT NULL AUTO_INCREMENT,
  `guild_id` bigint(20) unsigned NOT NULL,
  `clan_battle_period_id` int(11) NOT NULL,
  `clan_battle_boss_id` int(11) NOT NULL,
  `player_id` bigint(20) unsigned NOT NULL,
  `player_name` varchar(2000) NOT NULL,
  `boss_round` int(11) NOT NULL,
  `damage` int(11) NOT NULL,
  `attack_type` varchar(20) NOT NULL,
  `leftover_time` int(11) DEFAULT NULL,
  `overall_leftover_entry_id` int(11) DEFAULT NULL,
  `entry_date` datetime NOT NULL,
  PRIMARY KEY (`clan_battle_overall_entry_id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `clan_battle_period`
--

DROP TABLE IF EXISTS `clan_battle_period`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `clan_battle_period` (
  `clan_battle_period_id` int(11) NOT NULL AUTO_INCREMENT,
  `clan_battle_period_name` varchar(2000) NOT NULL,
  `date_from` datetime NOT NULL,
  `date_to` datetime NOT NULL,
  `boss1_id` int(11) NOT NULL,
  `boss2_id` int(11) NOT NULL,
  `boss3_id` int(11) NOT NULL,
  `boss4_id` int(11) NOT NULL,
  `boss5_id` int(11) NOT NULL,
  PRIMARY KEY (`clan_battle_period_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `clan_battle_report_message`
--

DROP TABLE IF EXISTS `clan_battle_report_message`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `clan_battle_report_message` (
  `clan_battle_report_message_id` int(11) NOT NULL AUTO_INCREMENT,
  `guild_id` bigint(20) unsigned NOT NULL,
  `clan_battle_period_id` int(11) NOT NULL,
  `day` int(11) NOT NULL,
  `message_id` bigint(20) unsigned NOT NULL,
  PRIMARY KEY (`clan_battle_report_message_id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `error_log`
--

DROP TABLE IF EXISTS `error_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `error_log` (
  `error_log_id` int(11) NOT NULL AUTO_INCREMENT,
  `guild_id` bigint(20) unsigned NOT NULL,
  `identifier` varchar(200) NOT NULL,
  `stacktrace` varchar(2000) NOT NULL,
  PRIMARY KEY (`error_log_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `guild`
--

DROP TABLE IF EXISTS `guild`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `guild` (
  `guild_id` bigint(20) unsigned NOT NULL,
  `guild_name` varchar(2000) NOT NULL,
  PRIMARY KEY (`guild_id`),
  UNIQUE KEY `UNIQUE` (`guild_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `guild_player`
--

DROP TABLE IF EXISTS `guild_player`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `guild_player` (
  `guild_id` bigint(20) unsigned NOT NULL,
  `player_id` bigint(20) unsigned NOT NULL,
  `player_name` varchar(200) NOT NULL,
  PRIMARY KEY (`guild_id`,`player_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2025-04-15 11:50:47
