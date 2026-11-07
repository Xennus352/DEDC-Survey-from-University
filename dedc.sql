-- MySQL dump 10.13  Distrib 8.0.46, for Linux (x86_64)
--
-- Host: localhost    Database: dedc
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `dedc`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `dedc` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `dedc`;

--
-- Table structure for table `ministry`
--

DROP TABLE IF EXISTS `ministry`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ministry` (
  `ministryId` int NOT NULL AUTO_INCREMENT,
  `ministryName` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`ministryId`),
  UNIQUE KEY `ministryName` (`ministryName`)
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ministry`
--

LOCK TABLES `ministry` WRITE;
/*!40000 ALTER TABLE `ministry` DISABLE KEYS */;
INSERT INTO `ministry` VALUES (5,'á€€á€¬á€€á€½á€šá€ºá€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(24,'á€€á€»á€”á€ºá€¸á€™á€¬á€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(18,'á€…á€€á€ºá€™á€¾á€¯á€”á€¾á€„á€·á€º á€¡á€žá€±á€¸á€…á€¬á€¸áŠ á€¡á€œá€á€ºá€…á€¬á€¸ á€…á€®á€¸á€•á€½á€¬á€¸á€›á€±á€¸á€œá€¯á€•á€ºá€„á€”á€ºá€¸á€™á€»á€¬á€¸ á€–á€½á€¶á€·á€–á€¼á€­á€¯á€¸á€á€­á€¯á€¸á€á€€á€ºá€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(14,'á€…á€­á€¯á€€á€ºá€•á€»á€­á€¯á€¸á€›á€±á€¸áŠ á€™á€½á€±á€¸á€™á€¼á€°á€›á€±á€¸á€”á€¾á€„á€·á€º á€†á€Šá€ºá€™á€¼á€±á€¬á€„á€ºá€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(21,'á€…á€®á€¸á€•á€½á€¬á€¸á€›á€±á€¸á€”á€¾á€„á€·á€º á€€á€°á€¸á€žá€”á€ºá€¸á€›á€±á€¬á€„á€ºá€¸á€á€šá€ºá€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(28,'á€†á€±á€¬á€€á€ºá€œá€¯á€•á€ºá€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(10,'á€á€­á€¯á€„á€ºá€¸á€›á€„á€ºá€¸á€žá€¬á€¸á€œá€°á€™á€»á€­á€¯á€¸á€™á€»á€¬á€¸á€›á€±á€¸á€›á€¬á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(4,'á€’á€…á€ºá€‚á€»á€…á€ºá€á€šá€ºá€–á€½á€¶á€·á€–á€¼á€­á€¯á€¸á€á€­á€¯á€¸á€á€€á€ºá€›á€±á€¸á€”á€¾á€„á€·á€º á€†á€€á€ºá€žá€½á€šá€ºá€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(9,'á€”á€šá€ºá€…á€•á€ºá€›á€±á€¸á€›á€¬á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(7,'á€”á€­á€¯á€„á€ºá€„á€¶á€á€¼á€¬á€¸á€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(31,'á€”á€­á€¯á€„á€ºá€„á€¶á€á€±á€¬á€ºá€žá€™á€¹á€™á€á€›á€¯á€¶á€¸'),(1,'á€”á€­á€¯á€„á€ºá€„á€¶á€á€±á€¬á€ºá€žá€™á€¹á€™á€á€›á€¯á€¶á€¸ á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(22,'á€•á€Šá€¬á€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(3,'á€•á€­á€¯á€·á€†á€±á€¬á€„á€ºá€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(6,'á€•á€¼á€Šá€ºá€‘á€²á€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(12,'á€•á€¼á€”á€ºá€€á€¼á€¬á€¸á€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(8,'á€˜á€á€¹á€á€¬á€›á€±á€¸á€”á€¾á€„á€·á€º á€¡á€á€½á€”á€ºá€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(27,'á€œá€°á€„á€šá€ºá€›á€±á€¸á€›á€¬á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(29,'á€œá€°á€™á€¾á€¯á€á€”á€ºá€‘á€™á€ºá€¸áŠ á€€á€šá€ºá€†á€šá€ºá€›á€±á€¸á€”á€¾á€„á€·á€º á€•á€¼á€”á€ºá€œá€Šá€ºá€”á€±á€›á€¬á€á€»á€‘á€¬á€¸á€›á€±á€¸á€á€”á€ºá€€á€¼á€®á€¸á€Œá€¬á€”'),(19,'á€œá€°... (line truncated to 2000 chars)
/*!40000 ALTER TABLE `ministry` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ministryquestion`
--

DROP TABLE IF EXISTS `ministryquestion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ministryquestion` (
  `mQId` int NOT NULL AUTO_INCREMENT,
  `mQDetail` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `qTID` int DEFAULT NULL,
  `yID` int NOT NULL,
  PRIMARY KEY (`mQId`),
  KEY `FK_ministryquestion_questiontitle` (`qTID`),
  KEY `fk_ministryquestion_year` (`yID`),
  CONSTRAINT `FK_ministryquestion_questiontitle` FOREIGN KEY (`qTID`) REFERENCES `questiontitle` (`qTID`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_ministryquestion_year` FOREIGN KEY (`yID`) REFERENCES `year` (`yID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ministryquestion`
--

LOCK TABLES `ministryquestion` WRITE;
/*!40000 ALTER TABLE `ministryquestion` DISABLE KEYS */;
/*!40000 ALTER TABLE `ministryquestion` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ministrysurvey`
--

DROP TABLE IF EXISTS `ministrysurvey`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ministrysurvey` (
  `mSurveyId` int NOT NULL AUTO_INCREMENT,
  `ministryId` int NOT NULL,
  `mQId` int NOT NULL,
  `hasItem` tinyint(1) NOT NULL,
  `itemCount` int DEFAULT NULL,
  `surveyDescription` text COLLATE utf8mb4_unicode_ci,
  `remark` text COLLATE utf8mb4_unicode_ci,
  `submittedAt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updatedAt` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`mSurveyId`),
  KEY `idx_ministrySurvey_ministryId` (`ministryId`),
  KEY `idx_ministrySurvey_mQId` (`mQId`),
  CONSTRAINT `fk_ministrySurvey_ministry` FOREIGN KEY (`ministryId`) REFERENCES `ministry` (`ministryId`) ON UPDATE CASCADE,
  CONSTRAINT `fk_ministrySurvey_question` FOREIGN KEY (`mQId`) REFERENCES `ministryquestion` (`mQId`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ministrysurvey`
--

LOCK TABLES `ministrysurvey` WRITE;
/*!40000 ALTER TABLE `ministrysurvey` DISABLE KEYS */;
/*!40000 ALTER TABLE `ministrysurvey` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `questiontitle`
--

DROP TABLE IF EXISTS `questiontitle`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `questiontitle` (
  `qTID` int NOT NULL AUTO_INCREMENT,
  `qTDetail` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`qTID`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `questiontitle`
--

LOCK TABLES `questiontitle` WRITE;
/*!40000 ALTER TABLE `questiontitle` DISABLE KEYS */;
INSERT INTO `questiontitle` VALUES (1,'á€œá€°á€·á€…á€½á€™á€ºá€¸á€¡á€¬á€¸á€¡á€›á€„á€ºá€¸á€¡á€™á€¼á€…á€º á€–á€½á€¶á€·á€–á€¼á€­á€¯á€¸á€á€­á€¯á€¸á€á€€á€ºá€›á€±á€¸á€†á€±á€¬á€„á€ºá€›á€½á€€á€ºá€™á€¾á€¯á€™á€»á€¬á€¸\n(Human Capital)',NULL),(2,'á€á€»á€­á€á€ºá€†á€€á€ºá€†á€±á€¬á€„á€ºá€›á€½á€€á€ºá€”á€­á€¯á€„á€ºá€™á€¾á€¯á€™á€»á€¬á€¸ (Connectivity)',NULL),(3,'á€’á€®á€‚á€»á€…á€ºá€á€šá€ºá€”á€Šá€ºá€¸á€•á€Šá€¬á€”á€¾á€„á€·á€º á€•á€±á€«á€„á€ºá€¸á€…á€•á€ºá€†á€±á€¬á€„á€ºá€›á€½á€€á€ºá€™á€¾á€¯á€™á€»á€¬á€¸\n(Integration of Digital Technology)',NULL),(4,'á€¡á€™á€»á€¬á€¸á€žá€¯á€¶á€¸á€’á€®á€‚á€»á€…á€ºá€á€šá€ºá€á€”á€ºá€†á€±á€¬á€„á€ºá€™á€¾á€¯á€™á€»á€¬á€¸\n(Digital Public Services)',NULL);
/*!40000 ALTER TABLE `questiontitle` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `uniquestion`
--

DROP TABLE IF EXISTS `uniquestion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `uniquestion` (
  `uQId` int NOT NULL AUTO_INCREMENT,
  `uQDetail` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `qTID` int DEFAULT NULL,
  `yID` int NOT NULL,
  PRIMARY KEY (`uQId`),
  KEY `FK_uniquestion_questiontitle` (`qTID`),
  KEY `fk_uniquestion_year` (`yID`),
  CONSTRAINT `FK_uniquestion_questiontitle` FOREIGN KEY (`qTID`) REFERENCES `questiontitle` (`qTID`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_uniquestion_year` FOREIGN KEY (`yID`) REFERENCES `year` (`yID`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `uniquestion`
--

LOCK TABLES `uniquestion` WRITE;
/*!40000 ALTER TABLE `uniquestion` DISABLE KEYS */;
INSERT INTO `uniquestion` VALUES (1,'á€™á€½á€±á€¸á€‘á€¯á€á€ºá€•á€±á€¸á€žá€Šá€·á€º IT á€˜á€½á€²á€·á€› á€€á€»á€±á€¬á€„á€ºá€¸á€žá€¬á€¸á€¦á€¸á€›á€± (á‚á€áá€ á€á€¯á€”á€¾á€…á€º á€™á€¾ á‚á€áá… á€á€¯á€”á€¾á€…á€ºáŠ á€™á€á€ºá€œá€‘á€­) (Bachelor á€˜á€½á€²á€·/ Master á€˜á€½á€²á€·/ Ph.D á€˜á€½á€²á€·/  Diploma á€˜á€½á€²á€· á€…á€žá€Šá€ºá€–á€¼á€„á€·á€º  á€á€½á€²áá€¼á€¬á€¸á€–á€±á€¬á€ºá€•á€¼á€›á€”á€º)',1,1),(2,'á€’á€®á€‚á€»á€…á€ºá€á€šá€ºá€€á€»á€½á€™á€ºá€¸á€€á€»á€„á€ºá€™á€¾á€¯ á€žá€„á€ºá€á€”á€ºá€¸á€™á€»á€¬á€¸á€–á€½á€„á€·á€ºá€œá€¾á€…á€ºá€•á€±á€¸á€”á€­á€¯á€„á€ºá€™á€¾á€¯á€¡á€á€¼á€±á€¡á€”á€±',1,1),(3,'á€’á€®á€‚á€»á€…á€ºá€á€šá€ºá€€á€»á€½á€™á€ºá€¸á€€á€»á€„á€ºá€™á€¾á€¯ á€žá€€á€ºá€™á€½á€±á€¸á€•á€Šá€¬ á€œá€±á€·á€€á€»á€„á€·á€ºá€›á€±á€¸ á€¡á€…á€®á€¡á€…á€‰á€ºá€™á€»á€¬á€¸á€á€½á€„á€º á€•á€«á€á€„á€ºá€žá€Šá€·á€ºá€žá€„á€ºá€á€”á€ºá€¸á€žá€¬á€¸ á€¡á€›á€±á€¡á€á€½á€€á€ºá‹ (Certificate á€žá€„á€ºá€á€”á€ºá€¸á€™á€»á€¬á€¸)',1,1),(4,'á€’á€®á€‚á€»á€…á€ºá€á€šá€ºá€…á€®á€¸á€•á€½á€¬á€¸á€›á€±á€¸á€œá€¯á€•á€ºá€„á€”á€ºá€¸á€™á€»á€¬á€¸á€á€½á€„á€º á€¡á€œá€¯á€•á€ºá€¡á€€á€­á€¯á€„á€ºá€›á€›á€¾á€­á€™á€¾á€¯ á€¡á€›á€±á€¡á€á€½á€€á€º',1,1),(5,'á€†á€›á€¬áŠá€†á€›á€¬á€™á€™á€»á€¬á€¸á€¡á€¬á€¸ á€’á€®á€‚á€»á€…á€ºá€á€šá€ºá€•á€Šá€¬á€›á€•á€ºá€”á€¾á€„á€·á€º á€”á€Šá€ºá€¸á€•á€Šá€¬á€˜á€¬á€žá€¬á€›á€•á€º á€žá€„á€ºá€€á€¼á€¬á€¸á€™á€¾á€¯á€…á€½á€™á€ºá€¸á€›á€Šá€ºá€¡á€á€½á€€á€º Capacity Building á€žá€„á€ºá€á€”á€ºá€¸á€™á€»á€¬á€¸ á€žá€„á€ºá€€á€¼á€¬á€¸á€•á€±á€¸á€”á€­á€¯á€„á€ºá€™á€¾á€¯á€¡á€á€¼á€±á€¡á€”á€±',1,1),(6,'á€•á€¼á€Šá€ºá€žá€°á€™á€»á€¬á€¸á€¡á€€á€¼á€¬á€¸ á€’á€®á€‚á€»á€…á€ºá€á€šá€ºá€á€á€ºá€™á€¼á€±á€¬á€€á€ºá€™á€¾á€¯ á€™á€¼á€¾á€„á€·á€ºá€á€„á€ºá€›á€”á€º á€¡á€žá€­á€•á€Šá€¬á€•á€±á€¸ á€†á€±á€¬á€„á€ºá€›á€½á€€á€ºá€™á€¾á€¯á€™á€»á€¬á€¸',1,1),(7,'á€á€€á€¹á€€á€žá€­á€¯á€œá€ºá€˜á€¬á€žá€¬á€›á€•á€ºá€™á€»á€¬á€¸á€á€½á€„á€º Industrial Placement á€¡á€…á€®á€¡á€…á€‰á€ºá€•á€«á€á€„á€ºá€žá€Šá€·á€º á€˜á€¬á€žá€¬á€›á€•á€ºá€™á€»á€¬á€¸á€€á€­á€¯á€‘á€Šá€·á€ºá€žá€½á€„á€ºá€¸á€žá€„á€ºá€€á€¼á€¬á€¸á€”á€­á€¯á€„á€ºá€™á€¾á€¯',1,1),(8,'á€€á€»á€±á€¬á€„... (line truncated to 2000 chars)
/*!40000 ALTER TABLE `uniquestion` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `unisurvey`
--

DROP TABLE IF EXISTS `unisurvey`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `unisurvey` (
  `uniSurveyId` int NOT NULL AUTO_INCREMENT,
  `uniId` int NOT NULL,
  `uQId` int NOT NULL,
  `hasItem` tinyint(1) NOT NULL,
  `itemCount` int DEFAULT NULL,
  `surveyDescription` text COLLATE utf8mb4_unicode_ci,
  `remark` text COLLATE utf8mb4_unicode_ci,
  `submittedAt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updatedAt` datetime DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`uniSurveyId`),
  KEY `idx_uniSurvey_uniId` (`uniId`),
  KEY `idx_uniSurvey_uQId` (`uQId`),
  CONSTRAINT `fk_uniSurvey_question` FOREIGN KEY (`uQId`) REFERENCES `uniquestion` (`uQId`) ON UPDATE CASCADE,
  CONSTRAINT `fk_uniSurvey_university` FOREIGN KEY (`uniId`) REFERENCES `university` (`uniId`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `unisurvey`
--

LOCK TABLES `unisurvey` WRITE;
/*!40000 ALTER TABLE `unisurvey` DISABLE KEYS */;
/*!40000 ALTER TABLE `unisurvey` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `university`
--

DROP TABLE IF EXISTS `university`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `university` (
  `uniId` int NOT NULL AUTO_INCREMENT,
  `uniType` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `uniName` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`uniId`),
  UNIQUE KEY `uniName` (`uniName`)
) ENGINE=InnoDB AUTO_INCREMENT=111 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `university`
--

LOCK TABLES `university` WRITE;
/*!40000 ALTER TABLE `university` DISABLE KEYS */;
INSERT INTO `university` VALUES (1,'CU','á€€á€½á€”á€ºá€•á€»á€°á€á€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€›á€”á€ºá€€á€¯á€”á€º)'),(2,'CU','á€€á€½á€”á€ºá€•á€»á€°á€á€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€™á€”á€¹á€á€œá€±á€¸)'),(3,'CU','á€€á€½á€”á€ºá€•á€»á€°á€á€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€™á€€á€½á€±á€¸)'),(4,'TU','á€›á€”á€ºá€€á€¯á€”á€ºá€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º'),(5,'TU','á€™á€”á€¹á€á€œá€±á€¸á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º'),(6,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€á€±á€¬á€„á€ºá€„á€°)'),(7,'TU','á€¡á€”á€±á€¬á€€á€ºá€›á€”á€ºá€€á€¯á€”á€ºá€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º'),(8,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€žá€”á€ºá€œá€»á€„á€º)'),(9,'TU','á€€á€»á€±á€¬á€€á€ºá€†á€Šá€ºá€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º'),(10,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€™á€¾á€±á€¬á€ºá€˜á€®)'),(11,'TU','á€”á€±á€•á€¼á€Šá€ºá€á€±á€¬á€ºá€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º'),(12,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€œá€¬á€¸á€›á€¾á€­á€¯á€¸)'),(13,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€™á€­á€á€¹á€‘á€®á€œá€¬)'),(14,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€™á€¡á€°á€•á€„á€º)'),(15,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€Ÿá€„á€ºá€¹á€žá€¬á€)'),(16,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€™á€¼á€…á€ºá€€á€¼á€®á€¸á€”á€¬á€¸)'),(17,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€—á€”á€ºá€¸á€™á€±á€¬á€º)'),(18,'TU','á€•á€¼á€Šá€ºá€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º'),(19,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€™á€¯á€¶á€›á€½á€¬)'),(20,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€€á€œá€±á€¸)'),(21,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€˜á€¬á€¸á€¡á€¶)'),(22,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€…á€…á€ºá€€á€­á€¯á€„á€ºá€¸)'),(23,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€™á€¯á€¶á€›á€½á€¬)'),(24,'TU','á€”á€Šá€ºá€¸á€•á€Šá€¬á€á€€á€¹á€€á€žá€­á€¯á€œá€º (á€€á€»á€­á€¯á€„á€ºá€¸á€... (line truncated to 2000 chars)
/*!40000 ALTER TABLE `university` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `userId` int NOT NULL AUTO_INCREMENT,
  `roleId` int NOT NULL,
  `uniId` int DEFAULT NULL,
  `ministryId` int DEFAULT NULL,
  `userName` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `passwordHash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `isActive` tinyint(1) NOT NULL DEFAULT '1',
  `createdAt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`userId`),
  UNIQUE KEY `userName` (`userName`),
  KEY `idx_user_roleId` (`roleId`),
  KEY `idx_user_uniId` (`uniId`),
  KEY `idx_user_ministryId` (`ministryId`),
  CONSTRAINT `fk_user_ministry` FOREIGN KEY (`ministryId`) REFERENCES `ministry` (`ministryId`) ON UPDATE CASCADE,
  CONSTRAINT `fk_user_role` FOREIGN KEY (`roleId`) REFERENCES `userrole` (`roleId`) ON UPDATE CASCADE,
  CONSTRAINT `fk_user_university` FOREIGN KEY (`uniId`) REFERENCES `university` (`uniId`) ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user`
--

LOCK TABLES `user` WRITE;
/*!40000 ALTER TABLE `user` DISABLE KEYS */;
INSERT INTO `user` VALUES (1,1,NULL,NULL,'captain','pbkdf2_sha256$600000$1065e105dda4be698232de5ef05d3aca$59fadf30ca6f06b7e38874149235059679f2f0b063c8e36af3cd58e6000ed86a',1,'2026-11-06 16:31:05');
/*!40000 ALTER TABLE `user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `userrole`
--

DROP TABLE IF EXISTS `userrole`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `userrole` (
  `roleId` int NOT NULL AUTO_INCREMENT,
  `roleName` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`roleId`),
  UNIQUE KEY `roleName` (`roleName`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `userrole`
--

LOCK TABLES `userrole` WRITE;
/*!40000 ALTER TABLE `userrole` DISABLE KEYS */;
INSERT INTO `userrole` VALUES (1,'Admin');
/*!40000 ALTER TABLE `userrole` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `year`
--

DROP TABLE IF EXISTS `year`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `year` (
  `yID` int NOT NULL AUTO_INCREMENT,
  `yearFrom` date DEFAULT NULL,
  `yearTo` date DEFAULT NULL,
  `status` tinyint DEFAULT '1',
  PRIMARY KEY (`yID`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `year`
--

LOCK TABLES `year` WRITE;
/*!40000 ALTER TABLE `year` DISABLE KEYS */;
INSERT INTO `year` VALUES (1,'2010-01-01','2015-12-31',1);
/*!40000 ALTER TABLE `year` ENABLE KEYS */;
UNLOCK TABLES;

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!400014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-08 00:00:00