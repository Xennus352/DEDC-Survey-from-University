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

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `dedc` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

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
INSERT INTO `ministry` VALUES (5,'ကာကွယ်ရေးဝန်ကြီးဌာန'),(24,'ကျန်းမာရေးဝန်ကြီးဌာန'),(18,'စက်မှုနှင့် အသေးစား၊ အလတ်စား စီးပွားရေးလုပ်ငန်းများ ဖွံ့ဖြိုးတိုးတက်ရေးဝန်ကြီးဌာန'),(14,'စိုက်ပျိုးရေး၊ မွေးမြူရေးနှင့် ဆည်မြောင်းဝန်ကြီးဌာန'),(21,'စီးပွားရေးနှင့် ကူးသန်းရောင်းဝယ်ရေးဝန်ကြီးဌာန'),(28,'ဆောက်လုပ်ရေးဝန်ကြီးဌာန'),(10,'တိုင်းရင်းသားလူမျိုးများရေးရာဝန်ကြီးဌာန'),(4,'ဒစ်ဂျစ်တယ်ဖွံ့ဖြိုးတိုးတက်ရေးနှင့် ဆက်သွယ်ရေးဝန်ကြီးဌာန'),(9,'နယ်စပ်ရေးရာဝန်ကြီးဌာန'),(7,'နိုင်ငံခြားရေးဝန်ကြီးဌာန'),(31,'နိုင်ငံတော်သမ္မတရုံး'),(1,'နိုင်ငံတော်သမ္မတရုံး ဝန်ကြီးဌာန'),(22,'ပညာရေးဝန်ကြီးဌာန'),(3,'ပို့ဆောင်ရေးဝန်ကြီးဌာန'),(6,'ပြည်ထဲရေးဝန်ကြီးဌာန'),(12,'ပြန်ကြားရေးဝန်ကြီးဌာန'),(8,'ဘဏ္ဍာရေးနှင့် အခွန်ဝန်ကြီးဌာန'),(27,'လူငယ်ရေးရာဝန်ကြီးဌာန'),(29,'လူမှုဝန်ထမ်း၊ ကယ်ဆယ်ရေးနှင့် ပြန်လည်နေရာချထားရေးဝန်ကြီးဌာန'),(19,'လူဝင်မှုကြီးကြပ်ရေးနှင့် ပြည်သူ့အင်အားဝန်ကြီးဌာန'),(17,'လျှပ်စစ်နှင့် စွမ်းအင်ဝန်ကြီးဌာန'),(15,'သမဝါယမနှင့် ကျေးလက်ဖွံ့ဖြိုးရေးဝန်ကြီးဌာန'),(16,'သယံဇာတနှင့် သဘာဝပတ်ဝန်းကျင်ထိန်းသိမ်းရေးဝန်ကြီးဌာန'),(13,'သာသနာရေးဝန်ကြီးဌာန'),(23,'သိပ္ပံနှင့် နည်းပညာဝန်ကြီးဌာန'),(30,'ဟိုတယ်၊ ခရီးသွားလာရေးနှင့် ယဉ်ကျေးမှုဝန်ကြီးဌာန'),(25,'အမျိုးသမီးရေးရာဝန်ကြီးဌာန'),(2,'အမျိုးသားစီမံကိန်း၊ ရင်းနှီးမြှုပ်နှံမှုနှင့် နိုင်ငံခြားစီးပွားဆက်သွယ်ရေးဝန်ကြီးဌာန'),(20,'အလုပ်သမားဝန်ကြီးဌာန'),(26,'အားကစားရေးရာဝန်ကြီးဌာန'),(11,'ဥပဒေရေးရာဝန်ကြီးဌာန');
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
INSERT INTO `questiontitle` VALUES (1,'လူ့စွမ်းအားအရင်းအမြစ် ဖွံ့ဖြိုးတိုးတက်ရေးဆောင်ရွက်မှုများ\n(Human Capital)',NULL),(2,'ချိတ်ဆက်ဆောင်ရွက်နိုင်မှုများ (Connectivity)',NULL),(3,'ဒီဂျစ်တယ်နည်းပညာနှင့် ပေါင်းစပ်ဆောင်ရွက်မှုများ\n(Integration of Digital Technology)',NULL),(4,'အများသုံးဒီဂျစ်တယ်ဝန်ဆောင်မှုများ\n(Digital Public Services)',NULL);
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
INSERT INTO `uniquestion` VALUES (1,'မွေးထုတ်ပေးသည့် IT ဘွဲ့ရ ကျောင်းသားဦးရေ (၂၀၁၀ ခုနှစ် မှ ၂၀၁၅ ခုနှစ်၊ မတ်လထိ) (Bachelor ဘွဲ့/ Master ဘွဲ့/ Ph.D ဘွဲ့/  Diploma ဘွဲ့ စသည်ဖြင့်  ခွဲခြားဖော်ပြရန်)',1,1),(2,'ဒီဂျစ်တယ်ကျွမ်းကျင်မှု သင်တန်းများဖွင့်လှစ်ပေးနိုင်မှုအခြေအနေ',1,1),(3,'ဒီဂျစ်တယ်ကျွမ်းကျင်မှု သက်မွေးပညာ လေ့ကျင့်ရေး အစီအစဉ်များတွင် ပါဝင်သည့်သင်တန်းသား အရေအတွက်။ (Certificate သင်တန်းများ)',1,1),(4,'ဒီဂျစ်တယ်စီးပွားရေးလုပ်ငန်းများတွင် အလုပ်အကိုင်ရရှိမှု အရေအတွက်',1,1),(5,'ဆရာ၊ဆရာမများအား ဒီဂျစ်တယ်ပညာရပ်နှင့် နည်းပညာဘာသာရပ် သင်ကြားမှုစွမ်းရည်အတွက် Capacity Building သင်တန်းများ သင်ကြားပေးနိုင်မှုအခြေအနေ',1,1),(6,'ပြည်သူများအကြား ဒီဂျစ်တယ်တတ်မြောက်မှု မြှင့်တင်ရန် အသိပညာပေး ဆောင်ရွက်မှုများ',1,1),(7,'တက္ကသိုလ်ဘာသာရပ်များတွင် Industrial Placement အစီအစဉ်ပါဝင်သည့် ဘာသာရပ်များကိုထည့်သွင်းသင်ကြားနိုင်မှု',1,1),(8,'ကျောင်းသူ/ ကျောင်းသားများ အတွက် Internship Program များစီစဉ်ဆောင်ရွက်နိုင်မှု (ဝန်ကြီးဌာနများ/ ပြင်ပကုမ္ပဏီများနှင့် ချိတ်ဆက်သွားရောက်နိုင်မှုအား ခွဲခြားရေးသားပေးပါရန်)',1,1),(9,'LMS အသုံးပြုနိုင်ရန် Digital Content များဖန်တီးနိုင်မှု',1,1),(10,'ပြည်ပမှ Educational Digital Content များအသုံးပြုနိုင်ရန် ဆောင်ရွက်နိုင်မှုအခြေအနေ',1,1),(11,'တက္ကသိုလ်များတွင် ဖိုင်ဘာကွန်ရက်၊ အင်တာနက်ကွန်ရက် ချိတ်ဆက်ပြီးစီးမှု အခြေအနေ',2,1),(12,'တက္ကသိုလ်များတွင် ဒီဂျစ်တယ် အခြေခံအဆောက်အဦများ တည်ထောင်နိုင်မှု အခြေအနေ\n(4G အသုံးချမှုနှင့် Mobile/ Broadband၊ Cloud Computing နှင့် Data Center အခြေခံအဆောက်အဦများ)',2,1),(13,'နည်းပညာအသုံးပြုမှု တီထွင်ဖန်တီးနိုင်မှုနှင့် စွန့်ဦးတီထွင်နိုင်မှု စွမ်းရည်များတိုးတက်လာစေရန် သုတေသနဌာနများ၊ Innovation Center များဖွင့်လှစ်ဆောင်ရွက်နိုင်မှု အခြေအနေ',3,1),(14,'နည်းပညာနှင့် စွန့်ဦးတီထွင်မှုစွမ်းရည် ပြပွဲ၊ ပြိုင်ပွဲများ ကျင်းပနိုင်မှု အခြေအနေ',3,1),(15,'နည်းပညာရပ်များဖွံ့ဖြိုးတိုးတက်ရန် နိုင်ငံတကာနှင့်  MOUရေးထိုးနိုင်ရေး စီစဉ်ဆောင်ရွက်နိုင်မှုအခြေအနေ (ဆောင်ရွက်ပြီး/ ဆောင်ရွက်ဆဲ)',3,1),(16,'နိုင်ငံတကာအဖွဲ့အစည်းများနှင့် ပူးပေါင်း၍ နည်းပညာရပ်ဆိုင်ရာ Affiliation Project များ၊ Joint Program များ၊ Online Class များ ဆောင်ရွက်နိုင်မှုအခြေအနေ',3,1),(17,'နည်းပညာဆိုင်ရာ စွန့်ဦးတီထွင်မှုများ မြှင့်တင်နိုင်ရန်နှင့် နောက်ဆုံးပေါ် နည်းပညာအသစ်များကို စမ်းသပ်သုတေသန ပြုလုပ်ရန်အကောင်အထည် ဖော်နိုင်မှုအခြေအနေ',3,1),(18,'AI နှင့် အလိုအလျောက်စနစ် အသုံးပြုမှုများ',3,1),(19,'ဒီဂျစ်တယ်အခြေခံအဆောက်အအုံနှင့် ကာဗွန်ခြေရာ လျော့ပါး သက်သာစေရေး ဆောင်ရွက်ချက်များ',3,1),(20,'အစိမ်းရောင် စီးပွားရေး လုပ်ငန်းများအတွက် သုတေသနဆောင်ရွက်ချက်များ',3,1),(21,'Data Integration အတွက် စံသတ်မှတ်ရေးစနစ် (Standardization) ထားရှိ ဆောင်ရွက်ချက်များ \n(ISO 8000 နှင့် သတင်းအချက်အလက်လုံခြုံရေး စီမံခန့်ခွဲမှု အတွက် ISO 27001 ကဲ့သို့သော နိုင်ငံတကာစံနှုန်းများကို အကောင်အထည်ဖော်မှု အခြေအနေ)',3,1),(22,'e-Government နှင့် ဒီဂျစ်တယ်ဝန်ဆောင်မှု ဆောင်ရွက်ထားရှိမှုများ\n(ဥပမာ၊ ဒီဂျစ်တယ် ID စနစ်များ၊ Online ငွေပေးချေမှုစနစ်များ)',4,1),(23,'နည်းပညာအသုံးပြုမှုများနှင့် ဝန်ဆောင်မှုများတွင် ဒီဂျစ်တယ်အသွင်ပြောင်းဆောင်ရွက်မှုများ',4,1),(24,'ကိုယ်ရေးကိုယ်တာအချက်အလက်များနှင့် ဆိုက်ဘာတိုက်ခိုက်မှုများ ကာကွယ်ရန် ဆောင်ရွက်မှုများ',4,1),(25,'ဥပဒေ၊ နည်းဥပဒေများပြဋ္ဌာန်းပြီး ယင်းဥပဒေ၊ နည်းဥပဒေများကို Enforce လုပ်နိုင်ရန် အကောင်အထည် ဖော်ဆောင်ရွက်နိုင်မှုအခြေအနေ',4,1);
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
INSERT INTO `university` VALUES (1,'CU','ကွန်ပျူတာတက္ကသိုလ် (ရန်ကုန်)'),(2,'CU','ကွန်ပျူတာတက္ကသိုလ် (မန္တလေး)'),(3,'CU','ကွန်ပျူတာတက္ကသိုလ် (မကွေး)'),(4,'TU','ရန်ကုန်နည်းပညာတက္ကသိုလ်'),(5,'TU','မန္တလေးနည်းပညာတက္ကသိုလ်'),(6,'TU','နည်းပညာတက္ကသိုလ် (တောင်ငူ)'),(7,'TU','အနောက်ရန်ကုန်နည်းပညာတက္ကသိုလ်'),(8,'TU','နည်းပညာတက္ကသိုလ် (သန်လျင်)'),(9,'TU','ကျောက်ဆည်နည်းပညာတက္ကသိုလ်'),(10,'TU','နည်းပညာတက္ကသိုလ် (မှော်ဘီ)'),(11,'TU','နေပြည်တော်နည်းပညာတက္ကသိုလ်'),(12,'TU','နည်းပညာတက္ကသိုလ် (လားရှိုး)'),(13,'TU','နည်းပညာတက္ကသိုလ် (မိတ္ထီလာ)'),(14,'TU','နည်းပညာတက္ကသိုလ် (မအူပင်)'),(15,'TU','နည်းပညာတက္ကသိုလ် (ဟင်္သာတ)'),(16,'TU','နည်းပညာတက္ကသိုလ် (မြစ်ကြီးနား)'),(17,'TU','နည်းပညာတက္ကသိုလ် (ဗန်းမော်)'),(18,'TU','ပြည်နည်းပညာတက္ကသိုလ်'),(19,'TU','နည်းပညာတက္ကသိုလ် (မုံရွာ)'),(20,'TU','နည်းပညာတက္ကသိုလ် (ကလေး)'),(21,'TU','နည်းပညာတက္ကသိုလ် (ဘားအံ)'),(22,'TU','နည်းပညာတက္ကသိုလ် (စစ်ကိုင်း)'),(23,'TU','နည်းပညာတက္ကသိုလ် (ကျိုင်းတုံ)'),(24,'TU','နည်းပညာတက္ကသိုလ် (လွိုင်ကော်)'),(25,'TU','နည်းပညာတက္ကသိုလ် (မော်လမြိုင်)'),(26,'TU','နည်းပညာတက္ကသိုလ် (တောင်ကြီး)'),(27,'TU','နည်းပညာတက္ကသိုလ် (စစ်တွေ)'),(28,'TU','နည်းပညာတက္ကသိုလ် (ပင်လုံ)'),(29,'TU','နည်းပညာတက္ကသိုလ် (ရမည်းသင်း)'),(30,'TU','နည်းပညာတက္ကသိုလ် (ပခုက္ကူ)'),(31,'TU','နည်းပညာတက္ကသိုလ် (မကွေး)'),(32,'TU','နည်းပညာတက္ကသိုလ် (ပုသိမ်)'),(33,'TU','နည်းပညာတက္ကသိုလ် (ဟားခါး)'),(34,'TU','ရတနာပုံဆိုက်ဘာစီးတီးနည်းပညာတက္ကသိုလ်'),(35,'PTU','Polytechnic University (မြိတ်)'),(36,'PTU','Polytechnic University (ထားဝယ်)'),(37,'AU','ရန်ကုန်တက္ကသိုလ်'),(38,'AU','မန္တလေးတက္ကသိုလ်'),(39,'AU','ဒဂုံတက္ကသိုလ်'),(40,'AU','ပုသိမ်တက္ကသိုလ်'),(41,'AU','ရတနာပုံတက္ကသိုလ်'),(42,'AU','ဘားအံတက္ကသိုလ်'),(43,'AU','ရွှေဘိုတက္ကသိုလ်'),(44,'AU','ဗန်းမော်တက္ကသိုလ်'),(45,'AU','မြစ်ကြီးနားတက္ကသိုလ်'),(46,'AU','ဟင်္သာတတက္ကသိုလ်'),(47,'AU','တောင်ငူတက္ကသိုလ်'),(48,'AU','အရှေ့ရန်ကုန်တက္ကသိုလ်'),(49,'AU','မအူပင်တက္ကသိုလ်'),(50,'AU','မြိတ်တက္ကသိုလ်'),(51,'AU','မော်လမြိုင်တက္ကသိုလ်'),(52,'AU','တောင်ကြီးတက္ကသိုလ်'),(53,'AU','မိတ္ထီလာတက္ကသိုလ်'),(54,'AU','လားရှိုးတက္ကသိုလ်'),(55,'AU','ပြည်တက္ကသိုလ်'),(56,'AU','ပခုက္ကူတက္ကသိုလ်'),(57,'AU','လွိုင်ကော်တက္ကသိုလ်'),(58,'AU','စစ်တွေတက္ကသိုလ်'),(59,'AU','ပဲခူးတက္ကသိုလ်'),(60,'AU','စစ်ကိုင်းတက္ကသိုလ်'),(61,'AU','ပင်လုံတက္ကသိုလ်'),(62,'AU','မကွေးတက္ကသိုလ်'),(63,'AU','မုံရွာတက္ကသိုလ်'),(64,'AU','ကျောက်ဆည်တက္ကသိုလ်'),(65,'AU','ကျိုင်းတုံတက္ကသိုလ်'),(66,'AU','ကလေးတက္ကသိုလ်'),(67,'AU','ထားဝယ်တက္ကသိုလ်'),(68,'AU','အနောက်ရန်ကုန်တက္ကသိုလ်'),(69,'AU','မိုင်းဖြတ်တက္ကသိုလ်'),(70,'AU','မိုးညှင်းတက္ကသိုလ်'),(71,'AU','မြောင်းမြတက္ကသိုလ်'),(72,'AU','ရေနံချောင်းတက္ကသိုလ်'),(73,'AU','မင်းဘူးတက္ကသိုလ်'),(74,'AU','ဟားခါးတက္ကသိုလ်'),(75,'EDU','ရန်ကုန်ပညာရေးတက္ကသိုလ်'),(76,'EDU','စစ်ကိုင်းပညာရေးတက္ကသိုလ်'),(77,'FLU','ရန်ကုန်နိုင်ငံခြားဘာသာတက္ကသိုလ်'),(78,'FLU','မန္တလေးနိုင်ငံခြားဘာသာတက္ကသိုလ်'),(79,'ECON','ရန်ကုန်စီးပွားရေးတက္ကသိုလ်'),(80,'ECON','မုံရွာစီးပွားရေးတက္ကသိုလ်'),(81,'ECON','မိတ္ထီလာစီးပွားရေးတက္ကသိုလ်'),(82,'DEU','ရန်ကုန်အဝေးသင်တက္ကသိုလ်'),(83,'DEU','မန္တလေးအဝေးသင်တက္ကသိုလ်'),(84,'MU','ဆေးတက္ကသိုလ် (၁) ရန်ကုန်'),(85,'MU','ဆေးတက္ကသိုလ် (၂) ရန်ကုန်'),(86,'MU','ဆေးတက္ကသိုလ် (မန္တလေး)'),(87,'MU','ဆေးတက္ကသိုလ် (မကွေး)'),(88,'MU','ဆေးတက္ကသိုလ် (တောင်ကြီး)'),(89,'DU','သွားဘက်ဆိုင်ရာဆေးတက္ကသိုလ် (ရန်ကုန်)'),(90,'DU','သွားဘက်ဆိုင်ရာဆေးတက္ကသိုလ် (မန္တလေး)'),(91,'NU','သူနာပြုတက္ကသိုလ် (ရန်ကုန်)'),(92,'NU','သူနာပြုတက္ကသိုလ် (မန္တလေး)'),(93,'MTU','ဆေးဘက်ဆိုင်ရာနည်းပညာတက္ကသိုလ် (ရန်ကုန်)'),(94,'MTU','ဆေးဘက်ဆိုင်ရာနည်းပညာတက္ကသိုလ် (မန္တလေး)'),(95,'PU','ဆေးဝါးတက္ကသိုလ် (ရန်ကုန်)'),(96,'PU','ဆေးဝါးတက္ကသိုလ် (မန္တလေး)'),(97,'PHU','ပြည်သူ့ကျန်းမာရေးတက္ကသိုလ် (ရန်ကုန်)'),(98,'CHU','အခြေခံကျန်းမာရေးတက္ကသိုလ် (မကွေး)'),(99,'TMU','တိုင်းရင်းဆေးတက္ကသိုလ် (ရန်ကုန်)'),(100,'AGU','ရေဆင်းစိုက်ပျိုးရေးတက္ကသိုလ်'),(101,'VU','မွေးမြူရေးဆိုင်ရာဆေးတက္ကသိုလ် (ရေဆင်း)'),(102,'MARU','မြန်မာနိုင်ငံရေကြောင်းပညာတက္ကသိုလ်'),(103,'AAEU','မြန်မာနိုင်ငံလေကြောင်းနှင့် အာကာသအင်ဂျင်နီယာတက္ကသိုလ်'),(104,'FESU','သစ်တောနှင့် ပတ်ဝန်းကျင်ဆိုင်ရာသိပ္ပံတက္ကသိုလ်'),(105,'ACU','အမျိုးသားယဉ်ကျေးမှုနှင့် အနုပညာတက္ကသိုလ် (မန္တလေး)'),(106,'ACU','အမျိုးသားယဉ်ကျေးမှုနှင့် အနုပညာတက္ကသိုလ် (ရန်ကုန်)'),(107,'COU','သမဝါယမတက္ကသိုလ် (သန်လျင်)'),(108,'COU','သမဝါယမတက္ကသိုလ် (စစ်ကိုင်း)'),(109,'BU','နိုင်ငံတော်ပရိယတ္တိသာသနာ့တက္ကသိုလ် (ရန်ကုန်)'),(110,'BU','နိုင်ငံတော်ပရိယတ္တိသာသနာ့တက္ကသိုလ် (မန္တလေး)');
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

--
-- Dumping events for database 'dedc'
--

--
-- Dumping routines for database 'dedc'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-06 17:43:06
