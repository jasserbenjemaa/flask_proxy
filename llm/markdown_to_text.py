from bs4 import BeautifulSoup
from markdown import markdown
import re

def markdown_to_text(markdown_string):
    """Converts a markdown string to plaintext while preserving code blocks."""

    # Convert Markdown to HTML
    html = markdown(markdown_string)

    # Preserve code snippets by replacing <code> with backticks
    html = re.sub(r'<pre><code>(.*?)</code></pre>', r'```\1```', html, flags=re.DOTALL)
    html = re.sub(r'<code>(.*?)</code>', r'`\1`', html)

    # Extract text using BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    text = ''.join(soup.findAll(text=True))
    text= re.sub(r'\b' + re.escape("python") + r'\b', '', text, count=1).strip()

    return text.strip()
