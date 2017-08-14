#!/bin/bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR

# refresh the input source of file auditing
./get_latest_source.sh

cd ../
# re-index with the refreshed input
./run_pcawg_file_audit.py audit

# generate overall summary report
./run_pcawg_file_audit.py summary

cd $DIR
./generate_reports.sh
