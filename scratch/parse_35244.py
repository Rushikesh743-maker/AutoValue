import re

with open(r'C:\Users\Hrushikesh\.gemini\antigravity-ide\brain\cca39500-a570-403b-93fb-d2df04d4c065\.system_generated\steps\201\content.md', 'r', encoding='utf-8') as f:
    text = f.read()

urls = re.findall(r'https?://[^\s"\'\)]+', text)
for u in set(urls):
    if '35244' in u:
        print(u)
