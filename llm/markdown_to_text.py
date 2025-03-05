import re

def markdown_to_text(markdown_string):
    """Converts a markdown string to plaintext while preserving code blocks."""

    text=markdown_string.replace('`', '')
    text= re.sub(r'\b' + re.escape("python") + r'\b', '', text, count=1).strip()

    return text.strip()
