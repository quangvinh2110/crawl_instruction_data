import aiohttp
import asyncio
import time
import json
import argparse
import glob
from bs4 import BeautifulSoup
from multiprocessing import Pool

from tqdm.asyncio import tqdm

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
        raise ValueError("Need both a links file and a output file")
    
    return args


async def get_page_content(session, url):
    
    try:
        async with session.get(url) as resp:
            page_content = await resp.text()
            return (page_content, True)
    except Exception as err:
        return (f"{err}", False)


async def get_questions(urls):

    async with aiohttp.ClientSession() as session:

        tasks = []
        for url in urls:
            tasks.append(asyncio.ensure_future(get_page_content(session, url)))

        results = await tqdm.gather(*tasks)
        data = []
        failed_urls = []
        for url, (page_content, succeed) in zip(urls, results):
            if succeed:
                data.append(
                    {"url": url, "content": page_content}
                )
            else:
                failed_urls.append(url)

        return data, failed_urls


def process_tailieumoi_webpage(webpage):
    soup = BeautifulSoup(webpage, "html.parser")
    choices = soup.find("div", {"class": "question-answers"})
    question = soup.find("div", {"class": "question-content"})
    reason = soup.find("div", {"class": "question-reason"})
    choices = choices.prettify() if choices else ""
    question = question.prettify() if question else ""
    reason = reason.prettify() if reason else ""
    return question, choices, reason
    


def main(urls, output_path):
    data, failed_urls = asyncio.run(get_questions(urls))
    # log failed urls
    failed_urls_path = "/".join(output_path.split("/")[:-1]) + "/failed_links.txt"
    if failed_urls_path:
        with open(failed_urls_path, "a") as f:
            for url in failed_urls:
                # write each item on a new line
                f.write("%s\n" % url)
    # preprocess webpages
    num_procs = 128
    with Pool(num_procs) as p:
        filtered_webpages = list(p.imap(
            process_tailieumoi_webpage, 
            [s["content"] for s in data]
        ))
    print(f"Save crawled questions to file: `{output_path}`")
    with open(output_path, "w") as f:
        for s, (question, choices, reason) in zip(data, filtered_webpages):
            d = json.dumps({
                "url": s["url"],
                "question": question,
                "choices": choices,
                "reason": reason
            }, ensure_ascii=False) + "\n"
            f.write(d)


if __name__ == "__main__":
    args = parse_args()
    for links_filepath in glob.glob(args.links_folderpath.strip("/")+"/*"):
        print(f"Get questions links from file: `{links_filepath}`")
        with open(links_filepath, "r") as f:
            urls = f.read().strip().split("\n")
        filename = links_filepath.split("/")[-1]
        questions_filepath = args.output_folderpath.strip("/")+"/"+filename[:-10]+"_questions.jsonl"
        main(urls, questions_filepath)
    print("--- %s seconds ---" % (time.time() - start_time))