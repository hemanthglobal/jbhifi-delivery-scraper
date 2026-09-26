@echo off
REM ---------------------------------------------------------------------
REM  OPTIONAL LOCAL BACKUP of PRIMARY CYCLE 1 - collector v2.2.0 (FROZEN)
REM  The official Cycle 1 runs on GitHub Actions. Use this only if you want
REM  a second, independent copy on this PC (it doubles the load on the site).
REM
REM  Cycle 1: Sat 26 Sep 12:00 -> Sun 27 Sep 11:30 (Adelaide), 40 slots x 49
REM  postcodes. Its run_id ends in _local, so it can never be merged with
REM  the GitHub copy (_gha).
REM
REM  Export (refreshed after every pass, COMPLETE after the last pass):
REM    %OUT%\ASSIGNMENT_DATASET_cycle1_LOCAL_20260926\
REM
REM  Start by DOUBLE-CLICKING (not from any AI tool). Keep the window open,
REM  laptop plugged in, lid open. If it stops, double-click again: finished
REM  observations are skipped, nothing is duplicated.
REM ---------------------------------------------------------------------
cd /d "%~dp0"
title JB Hi-Fi LOCAL BACKUP cycle 1 v2.2.0 - DO NOT CLOSE
set OUT=%USERPROFILE%\Desktop\jbhifi_data\local_backup_v2.2.0_20260926
echo Output folder: %OUT%
"..\jbhifi_env\Scripts\python.exe" "..\frozen_v2.2.0\scraper.py" --study primary --cycle-date 2026-09-26 --slots 0-39 --max-wait-min 60 --export-names "ASSIGNMENT_DATASET_cycle1_LOCAL" --out-dir "%OUT%"
echo.
echo Collector exited with code %ERRORLEVEL%  (0 = finished, 3 = site blocked/rate limited - see scraper.log)
pause
