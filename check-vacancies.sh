#!/bin/bash
# Vacancy check script for cron

cd /opt/job-hunter
source venv/bin/activate
python -m app.main
