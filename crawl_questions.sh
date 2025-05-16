#!/bin/bash

set -ex

# nohup python -u crawl_tailieumoi_questions.py \
#     --links_folderpath "./data/failed_question_links/tailieumoi/" \
#     --output_folderpath "./data/failed_question_links/tailieumoi/" >> log.txt 2>&1 &


nohup python -u crawl_vietjack_questions.py \
    --links_folderpath "./data/question_links/vietjack/" \
    --output_folderpath "./data/questions/vietjack/" >> log.txt 2>&1 &