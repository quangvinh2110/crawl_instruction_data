from typing import List
import json
import google.generativeai as genai
import asyncio
import os
import re
import glob
import string
import time

from tqdm.asyncio import tqdm

from src.utils import read_jsonl, normalize_newline


REWRITE_ANSWER_TEMPLATE = """
Given a question and a corresponding answer, your task is to rewrite provided answer to format: first-reasoning-then-conclusion and make it more detail if necessary. 
Provide your rewritten answer in the ``` brackets.

Example:
Question: Ngành tài chính - ngân hàng không có đặc điểm nào sau đây?
A. Tài chính ngân hàng là một lĩnh vực rất rộng và nhiều hoạt động.
B. Nhu cầu của khách đa dạng, phong phú và thường có tính thời vụ.
C. Sản phẩm thường được thực hiện theo các quy trình nghiêm ngặt.
D. Gồm hai bộ phận khăng khít với nhau là tài chính và ngân hàng.

Provided answer: Đáp án đúng là: B
- Tài chính ngân hàng gồm hai bộ phận khăng khít với nhau là tài chính và ngân hàng.
- Tài chính ngân hàng là một lĩnh vực rất rộng, bao gồm nhiều hoạt động.
- Do tính rủi ro cao và có phản ứng dây chuyền trong hệ thống nên sản phẩm tài chính ngân hàng thường được thực hiện theo những quy trình nghiêm ngặt.

Rewritten answer: ```
Ngành tài chính - ngân hàng có những đặc điểm sau:
- Bao gồm hai bộ phận liên kết chặt chẽ là tài chính và ngân hàng.
- Là một lĩnh vực rất rộng, bao gồm nhiều hoạt động khác nhau.
- Do tính rủi ro cao và có thể gây ra phản ứng dây chuyền trong hệ thống, các sản phẩm tài chính - ngân hàng thường được thực hiện theo các quy trình nghiêm ngặt.
Trong khi đó, đáp án B cho rằng nhu cầu của khách hàng đa dạng, phong phú và thường có tính thời vụ. Tuy nhiên, nhu cầu của khách hàng trong lĩnh vực này không nhất thiết có tính thời vụ, mà thường ổn định và liên tục. Do đó, đáp án B không phải là đặc điểm của ngành tài chính - ngân hàng.

Vì vậy, đáp án đúng là: B.
```

---
Question: {question}

Provided answer: {reason}

Rewritten answer:
""".strip()


GEN_ANSWER_TEMPLATE = """
Provide a Vietnamese first-reasoning-then-conclusion answer for the following question. Return your final choice inside \\boxed{{}}.

Example:
Question: Ngành tài chính - ngân hàng không có đặc điểm nào sau đây?
A. Tài chính ngân hàng là một lĩnh vực rất rộng và nhiều hoạt động.
B. Nhu cầu của khách đa dạng, phong phú và thường có tính thời vụ.
C. Sản phẩm thường được thực hiện theo các quy trình nghiêm ngặt.
D. Gồm hai bộ phận khăng khít với nhau là tài chính và ngân hàng.

Answer: Ngành tài chính - ngân hàng có những đặc điểm sau:
- Bao gồm hai bộ phận liên kết chặt chẽ là tài chính và ngân hàng.
- Là một lĩnh vực rất rộng, bao gồm nhiều hoạt động khác nhau.
- Do tính rủi ro cao và có thể gây ra phản ứng dây chuyền trong hệ thống, các sản phẩm tài chính - ngân hàng thường được thực hiện theo các quy trình nghiêm ngặt.
Trong khi đó, đáp án B cho rằng nhu cầu của khách hàng đa dạng, phong phú và thường có tính thời vụ. Tuy nhiên, nhu cầu của khách hàng trong lĩnh vực này không nhất thiết có tính thời vụ, mà thường ổn định và liên tục. Do đó, đáp án B không phải là đặc điểm của ngành tài chính - ngân hàng.

Vì vậy, đáp án đúng là: \\boxed{{B}}

---
Question: {question}

Answer:
"""

PRED_CHOICE_PATTERN = re.compile(r"\\boxed{(.+)}", flags=re.I)


class GeminiProcessor:
    """
    A class to asynchronously process data samples using the Gemini API.
    """

    def __init__(self, api_key: str=None, model_name: str="gemini-2.0-flash", generation_config: dict = None):
        """
        Initializes the GeminiProcessor with an API key and model name.

        Args:
            api_key (str, optional): Your Gemini API key. Defaults to None.
                                      If None, it tries to get it from the 'GEMINI_API_KEY' environment variable.
            model_name (str, optional): The name of the Gemini model to use. Defaults to "gemini-pro".
        """
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key is None:
                raise ValueError(
                    "API key not provided and 'GEMINI_API_KEY' environment variable not set."
                )
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name,
            generation_config=generation_config,
        )


    async def process_sample_async(self, sample: dict) -> dict:
        """
        Asynchronously processes a single data sample using the Gemini API.

        Args:
            sample (dict): A dictionary representing a data sample with fields like
                           'question', 'choices', etc.

        Returns:
            dict: The updated sample dictionary with an added 'answer' field
                  containing the Gemini API's response.
        """
        # if "question" not in sample or "choices" not in sample:
        #     print(f"Warning: Sample with id '{sample.get('id', 'N/A')}' is missing 'question' or 'choices' fields. Skipping API call.")
        #     return sample  # Return the sample as is if missing required fields
        if "full_reason" in sample and sample["full_reason"]:
            return sample

        question: str = sample["question"].strip()
        choices: List[str] = sample["choices"]
        reason: str = sample["reason"].strip()
        for c in [c+"." for c in string.ascii_lowercase]+[c+"," for c in string.ascii_lowercase]:
            if question.startswith(c):
                updated_sample = sample.copy() # Create a copy to avoid modifying original
                updated_sample["full_reason"] = ""
                return updated_sample
        if len(reason)>1000 and not reason.strip().startswith("Đáp án"):
            updated_sample = sample.copy() # Create a copy to avoid modifying original
            updated_sample["full_reason"] = ""
            return updated_sample
        is_multiple_choices = True
        if not choices:
            choices = []
        for choice in choices+[sample["correct_choice"]]:
            if not choice:
                is_multiple_choices = False
                break

        if len(reason.split())<20 and is_multiple_choices:
            prompt = GEN_ANSWER_TEMPLATE.format(
                question=normalize_newline(question)+"\n"+"\n".join(choices),
            )
        else:
            if not is_multiple_choices:
                choices = []
            prompt = REWRITE_ANSWER_TEMPLATE.format(
                question=normalize_newline(question)+"\n"+"\n".join(choices),
                reason=normalize_newline(reason)
            )


        try:
            response = await self.model.generate_content_async(prompt)
            response.resolve() # Ensure the response is resolved to catch exceptions early

            if hasattr(response, 'text'): # Check if 'text' attribute exists
                answer_text = response.text
            elif response.parts and hasattr(response.parts[0], 'text'): # Fallback for parts-based response
                answer_text = response.parts[0].text
            else:
                answer_text = ""
                print(f"Warning: No text response found in Gemini API output for sample id '{sample.get('id', 'N/A')}'. Full response: {response}")

            if answer_text and len(reason.split())<20 and is_multiple_choices:
                pred_choice = PRED_CHOICE_PATTERN.findall(answer_text)[-1]
                if pred_choice.strip().lower()[0]==sample["correct_choice"].strip().lower()[0]:
                    answer_text = re.sub(r"\\boxed{(.+)}", r"\1", answer_text)
                else:
                    answer_text = ""



            updated_sample = sample.copy()
            updated_sample["full_reason"] = answer_text
            return updated_sample

        except Exception as e:
            error_message = f"Error processing sample id '{sample.get('id', 'N/A')}': {e}"
            print(error_message)
            updated_sample = sample.copy()
            updated_sample["full_reason"] = ""
            return updated_sample


    async def process_dataset_async(self, dataset: list[dict], out_filepath: str) -> list[dict]:
        """
        Asynchronously processes a list of data samples using the Gemini API concurrently.

        Args:
            dataset (list[dict]): A list of dictionaries, where each dictionary is a data sample.

        Returns:
            list[dict]: A list of updated sample dictionaries, each with an 'answer' field.
        """
        req_per_min = 1000
        processed_dataset = []
        for i in range(len(dataset)//req_per_min+1):
            start = i*1000
            end = start+1000 if start+1000<len(dataset) else len(dataset)
            tasks = [self.process_sample_async(sample) for sample in dataset[start:end]]
            batch = await tqdm.gather(*tasks)
            # processed_dataset.extend(batch)
            with open(out_filepath, "a") as f:
                for s in batch:
                    f.write(json.dumps(s, ensure_ascii=False)+"\n")
            time.sleep(60)
        return processed_dataset


# Example Usage (assuming you have 'my_dataset' as a list of dictionaries):
async def main():
    # Initialize the GeminiProcessor (make sure GEMINI_API_KEY is set in environment or pass it directly)
    processor = GeminiProcessor(
        generation_config={
            "temperature": 0,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 4096,
            "response_mime_type": "text/plain",
        }
    ) # or processor = GeminiProcessor(api_key="YOUR_API_KEY")
    # Replace with your actual dataset
    subject_list = [
        "van",
        "lichsu",
        "dialy",
        "gdcd",
        "gdqp",
        "ktpl",
        "lichsudialy"
    ]
    for filepath in glob.glob("./data/processed_questions/tailieumoi/*"):
        filename = filepath.split("/")[-1]
        out_filepath = f"./data/extended_questions/tailieumoi/{filename}"
        if os.path.isfile(out_filepath):
            continue
        # check if data belongs to the subject list or not
        flag = False
        for subject in subject_list:
            if subject in filepath:
                flag = True
                break
        if not flag or not filepath.endswith("jsonl"):
            continue
        # read data
        data = read_jsonl(filepath)
        _ = await processor.process_dataset_async(data, out_filepath)
    


if __name__ == "__main__":
    # Run the asynchronous main function
    asyncio.run(main())