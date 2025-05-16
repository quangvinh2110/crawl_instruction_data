import json
import re
import pandoc
from bs4 import BeautifulSoup


def read_jsonl(filepath: str):
    data = []
    with open(filepath) as f:
        for line in f:
            data.append(json.loads(line))
    return data


REMOVED_TAG = ["div", "label", re.compile(r"h\d+"), "strong", "span", "a"]
def remove_tag_from_text(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    for tag in REMOVED_TAG:
        for e in soup.find_all(tag):
            e.unwrap()
    return soup.prettify()


def normalize_pandoc_output(text: str) -> str:
    return re.sub(r"\\([^\w\s]+?)", r"\1", text)


def convert_html_to_md(text: str) -> str:
    in_doc = pandoc.read(text, format="html")
    out_doc = pandoc.write(in_doc, format="markdown_mmd", options=["--no-highlight"]).strip()
    return normalize_pandoc_output(out_doc)


VNESE_CHAR = "bĩfáổoằìỷếnắqeẩdlwêăọậặụyèấũảxưéủẵỗúỳaâíộợãjẳơữểồàạễốừùzirựcóớđẽẫumõửỡỏỹỉhởầòềpỵịvsứôệtẻẹgờký"
def normalize_newline(text):
    """
    Normalize text by replacing:
    - Single '\n' with ' '
    - Two or more consecutive '\n' with a single '\n'
    
    Args:
        text (str): Input text to normalize
    
    Returns:
        str: Normalized text
    """
    # Replace multiple consecutive newlines with a single newline
    text = re.sub(r'\n{2,}', '<---newline--->', text)
    
    # Replace single newlines with a space
    text = re.sub(r'[{}\d](\n)[{}\d]'.format(VNESE_CHAR, VNESE_CHAR), '', text)
    text = text.replace('<---newline--->', '\n')
    
    return text.strip()