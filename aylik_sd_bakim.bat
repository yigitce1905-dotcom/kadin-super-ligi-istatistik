@echo off
rem AYLIK BAKIM — Gorev Zamanlayici'dan ayda bir cagirin.
rem Gorev Zamanlayici > Gorev Olustur > Eylem: bu .bat dosyasi
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
python aylik_sd_bakim.py >> aylik_bakim_log.txt 2>&1
