import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBSITES = [
    {
        "name": "NECA",
        "base_url": "https://neca.org.ng/",
        "pages": [
            "https://neca.org.ng/",
            "https://neca.org.ng/who-we-are/",
            "https://neca.org.ng/learning-and-development-department/",
            "https://neca.org.ng/neca-talent-network/",
            "https://neca.org.ng/faq/",
            "https://neca.org.ng/membership-requirements/",
            "https://neca.org.ng/membership-fees/",
            "https://neca.org.ng/benefits-of-membership/",
            "https://neca.org.ng/apply/",
            "https://neca.org.ng/contacts/",
            "https://neca.org.ng/category/news/",
            "https://neca.org.ng/downloads/"
        ]
    },
    {
        "name": "NECA ICT Academy",
        "base_url": "https://www.necaictacademy.org/",
        "pages": [
            "https://www.necaictacademy.org/",
            "https://www.necaictacademy.org/courses",
            "https://www.necaictacademy.org/programprocess",
            "https://www.necaictacademy.org/faq"
        ]
    }
]


headers = {"User-Agent": "Mozilla/5.0"}


def scrape_page(url):
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove elements that do not contain useful knowledge
    for element in soup([
        "script",
        "style",
        "noscript",
        "svg",
        "iframe",
        "nav",
        "footer"
    ]):
        element.decompose()

    # Prefer the main page content
    main_content = soup.find("main")

    if main_content:
        content = main_content
    else:
        content = soup.body

    if not content:
        return ""

    # Extract useful text
    text = content.get_text(separator="\n")

    # Clean whitespace
    lines = []

    for line in text.splitlines():
        line = " ".join(line.split())

        if line:
            lines.append(line)

    # Remove repeated consecutive lines
    cleaned_lines = []

    for line in lines:
        if not cleaned_lines or line != cleaned_lines[-1]:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def main():
    all_text = []
    seen_content = set()

    for website in WEBSITES:
        print(f"\n===== Scraping {website['name']} =====")

        for page in website["pages"]:
            url = urljoin(website["base_url"], page)

            print(f"Scraping: {url}")

            try:
                text = scrape_page(url)

                if text:
                    # Normalize text before checking for duplicates
                    normalized_text = " ".join(text.split()).lower()

                    # Check if this page's content is already present
                    if normalized_text in seen_content:
                        print(f"Duplicate skipped: {url}")
                        continue

                    # Add content to the set of already-seen pages
                    seen_content.add(normalized_text)

                    all_text.append("=" * 80)
                    all_text.append(f"ORGANISATION: {website['name']}")
                    all_text.append(f"PAGE: {url}")
                    all_text.append("=" * 80)
                    all_text.append(text)
                    all_text.append("")

                    print(f"Success: {len(text)} characters extracted")

                else:
                    print("No text found")

            except Exception as e:
                print(f"Error scraping {url}: {e}")

    with open("neca_data.txt", "w", encoding="utf-8") as file:
        file.write("\n".join(all_text))

    print("\nScraping complete.")
    print("Saved to: neca_data.txt")


if __name__ == "__main__":
    main()