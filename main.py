from flask import Flask, render_template_string, request, redirect, url_for
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import os

app = Flask(__name__)

WIKI_BASE_URL = "https://en.wikipedia.org"


def util_load_file(suffix: str) -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), suffix)
    with open(path, encoding='utf-8') as file:
        return file.read()

def http_request(url: str, params: dict = None, headers: dict = None) -> requests.Response | None:
    try:
        response = requests.get(url, params=params or {}, headers=headers or {}, timeout=10)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return None

def extract_grouped_data_by_column(page: str, group_column: str) -> dict:
    url = f"{WIKI_BASE_URL}/wiki/{page}"
    response = http_request(url)
    if not response:
        return {}

    soup = BeautifulSoup(response.text, 'html.parser')
    tables = soup.find_all("table", class_="wikitable")
    grouped = defaultdict(list)

    for table in tables:
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if group_column.lower() not in headers:
            continue

        group_idx = headers.index(group_column.lower())
        name_idx = 0  # assume first column has the animal name

        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) <= max(group_idx, name_idx):
                continue

            name_tag = cols[name_idx].find("a")
            if not name_tag:
                continue
            name = name_tag.get("title")
            href = name_tag.get("href")

            group_values = [v.strip() for v in cols[group_idx].get_text(",").split(",") if v.strip()]

            image_url = get_main_wiki_image(href) if href else ""

            for val in group_values:
                grouped[val].append((name, image_url))

    return grouped

def get_main_wiki_image(href: str) -> str:
    res = http_request(f"{WIKI_BASE_URL}{href}")
    if not res:
        return ""

    soup = BeautifulSoup(res.text, "html.parser")
    img_tag = soup.select_one("table.infobox img")
    if not img_tag:
        img_tag = soup.select_one("div.mw-parser-output figure img")

    return f"https:{img_tag['src']}" if img_tag and img_tag.get("src") else ""

@app.route('/', methods=['GET', 'POST'])
def index():
    grouped_data = None
    html = util_load_file("html_template.html")
    if request.method == 'POST':
        page = request.form['page']
        column = request.form['column']
        grouped_data = extract_grouped_data_by_column(page, column)
    return render_template_string(html, grouped_data=grouped_data)

if __name__ == '__main__':
    app.run(debug=True)
