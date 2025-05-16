from abc import ABC, abstractmethod
from typing import List
import aiohttp
import asyncio
import time
import json
import glob
from multiprocessing import Pool

from tqdm.asyncio import tqdm

start_time = time.time()


class BaseCrawler(ABC):
    def __init__(self, input_folderpath: str, output_folderpath: str):
        self.input_folderpath = input_folderpath
        self.output_folderpath = output_folderpath


    async def get_page_content(self, session, url):
        try:
            async with session.get(url) as resp:
                page_content = await resp.text()
                return (page_content, True)
        except Exception as err:
            return (f"{err}", False)
        

    async def get_questions(self, urls):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in urls:
                tasks.append(asyncio.ensure_future(self.get_page_content(session, url)))

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
        

    @abstractmethod
    def process_one_webpage(self, webpage: str) -> dict:
        pass


    def process_webpages(self, webpages: str, num_procs: int = 128) -> List[dict]:
        with Pool(num_procs) as p:
            processed_webpages = list(p.imap(
                self.process_one_webpage, 
                webpages
            ))
        return processed_webpages


    def crawl_from_file(self, input_filepath, output_filepath):
        print(f"Get questions links from file: `{input_filepath}`")
        with open(input_filepath, "r") as f:
            urls = f.read().strip().split("\n")
        data, failed_urls = asyncio.run(self.get_questions(urls))
        # log failed urls
        failed_urls_path = "/".join(output_filepath.split("/")[:-1]) + "/failed_links.txt"
        if failed_urls_path:
            print(f"Save {len(failed_urls)} failed question links to file: `{failed_urls_path}`")
            with open(failed_urls_path, "a") as f:
                for url in failed_urls:
                    f.write("%s\n" % url)
        # process webpages
        processed_webpages = self.process_webpages(
            [s["content"] for s in data],
            num_procs=128
        )
        # save processed webpages to file
        print(f"Save crawled questions to file: `{output_filepath}`")
        with open(output_filepath, "w") as f:
            for s, processed_webpage in zip(data, processed_webpages):
                if not processed_webpage["question"]:
                    continue
                processed_webpage["url"] = s["url"]
                d = json.dumps(processed_webpage, ensure_ascii=False) + "\n"
                f.write(d)

    
    def crawl(self):    
        for input_filepath in glob.glob(self.input_folderpath.strip("/")+"/*"):
            filename = input_filepath.split("/")[-1]
            output_filepath = self.output_folderpath.strip("/")+"/"+filename[:-10]+"_questions.jsonl"
            self.crawl_from_file(input_filepath, output_filepath)