import aiohttp
import asyncio
import time
import json
import argparse
import glob
from bs4 import BeautifulSoup
from src.question_crawlers import BaseCrawler

start_time = time.time()


def parse_args():
    parser = argparse.ArgumentParser(
        description=""
    )
    parser.add_argument(
        "--links_folderpath",
        type=str,
        default=None,
        help="The absolute path to link file."
    )
    parser.add_argument(
        "--output_folderpath",
        type=str,
        default=None,
        help="The absolute path to output file"
    )
    args = parser.parse_args()

    # Sanity checks
    if args.links_folderpath is None or args.output_folderpath is None:
        raise ValueError("Need both a links folder and a output folder")
    
    return args


class TailieumoiCrawler(BaseCrawler):

    def process_one_webpage(self, webpage):
        soup = BeautifulSoup(webpage, "html.parser")
        choices = soup.find(
            "div", {"class": "question-answers"}
        ).find_all(
            "div", {"class": "answer-content"}
        )
        correct_choice = soup.find(
            "div", {"class": "question-answers"}
        ).find(
            "div", {"class": "option-choices js-answer answer-correct"}
        ).find(
            "div", {"class": "answer-content"}
        )
        question = soup.find("div", {"class": "question-content"})
        reason = soup.find("div", {"class": "question-reason"})
        choices = [choice.prettify() for choice in choices] if choices else [""]
        correct_choice = correct_choice.prettify() if correct_choice else ""
        question = question.prettify() if question else ""
        reason = reason.prettify() if reason else ""
        return {
            "question": question,
            "choices": choices,
            "correct_choice": correct_choice,
            "reason": reason
        }
    


if __name__ == "__main__":
    args = parse_args()
    crawler = TailieumoiCrawler(
        input_folderpath=args.links_folderpath,
        output_folderpath=args.output_folderpath
    )
    crawler.crawl()
    print("--- %s seconds ---" % (time.time() - start_time))