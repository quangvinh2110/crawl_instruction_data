import time
import argparse
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


class VietjackCrawler(BaseCrawler):

    def process_one_webpage(self, webpage):
        try:
            soup = BeautifulSoup(webpage, "html.parser")
            choices = soup.find_all("div", {"class": "option-choices js-answer"})
            choices.append(soup.find("div", {"class": "option-choices js-answer answer-correct"}))
            correct_choice = soup.find("div", {"class": "option-choices js-answer answer-correct"})
            question = soup.find("h1", {"class": "title-question overflow-x-el"})
            reason = soup.find("div", {"class": "result"}) 
            choices = [choice.prettify() if choice else None for choice in choices] if choices else [""]
            correct_choice = correct_choice.prettify() if correct_choice else ""
            question = question.prettify() if question else ""
            reason = reason.prettify() if reason else ""
            return {
                "question": question,
                "choices": choices,
                "correct_choice": correct_choice,
                "reason": reason
            }
        except:
            return {
                "question": "",
                "choices": [""],
                "correct_choice": "",
                "reason": ""
            }
            
    


if __name__ == "__main__":
    args = parse_args()
    crawler = VietjackCrawler(
        input_folderpath=args.links_folderpath,
        output_folderpath=args.output_folderpath
    )
    crawler.crawl()
    print("--- %s seconds ---" % (time.time() - start_time))