@echo off
REM ---------------------------------------------------------------------
REM  JB Hi-Fi PRIMARY study - main run, collector v2.1.0 (FROZEN copy)
REM
REM  Two cycles, Adelaide time:
REM    cycle 1 (weekend)  Sun 27 Sep 07:00 -> Mon 28 Sep 06:00
REM    cycle 2 (weekday)  Mon 28 Sep 07:00 -> Tue 29 Sep 06:00
REM  49 postcodes x 40 slots x 2 cycles = 3,920 observations.
REM
REM  Start it by DOUBLE-CLICKING this file (not from any AI tool), any time
REM  before Sun 07:00. It waits for the first slot by itself.
REM  Keep this window open and the laptop plugged in with the lid open.
REM  Windows is asked not to sleep while it runs.
REM
REM  ASSIGNMENT DATASET = cycle 1 only. It is exported automatically to
REM    %OUT%\ASSIGNMENT_DATASET_cycle1_20260927\
REM  refreshed after every pass on Sunday (STATUS.txt says IN PROGRESS) and
REM  marked COMPLETE (CYCLE_COMPLETE.txt) at about Mon 28 Sep 06:22.
REM  Cycle 2 is optional replication/backup only (BACKUP_replication_cycle2_*).
REM
REM  If it stops for any reason, double-click it again: finished
REM  observations are skipped (resume), past slots are skipped, and
REM  nothing is duplicated.
REM ---------------------------------------------------------------------
cd /d "%~dp0"
title JB Hi-Fi MAIN RUN v2.1.0 - DO NOT CLOSE
set OUT=%USERPROFILE%\Desktop\jbhifi_data\main_v2.1.0_20260927
echo Output folder: %OUT%
"..\jbhifi_env\Scripts\python.exe" frozen_v2.1.0\scraper.py --study primary --cycle-date 2026-09-27 --cycles 2 --slots 0-39 --max-wait-min 1440 --export-names "ASSIGNMENT_DATASET_cycle1,BACKUP_replication_cycle2" --out-dir "%OUT%"
echo.
echo Collector exited with code %ERRORLEVEL%  (0 = finished, 3 = site blocked/rate limited - see scraper.log)
pause
