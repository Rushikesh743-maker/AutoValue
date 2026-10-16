import re

with open(r'C:\Users\Hrushikesh\.gemini\antigravity-ide\brain\cca39500-a570-403b-93fb-d2df04d4c065\.system_generated\steps\70\content.md', 'r', encoding='utf-8') as f:
    text = f.read()

urls = re.findall(r'https://cdn\.coverr\.co/videos/[^"\s]+', text)
unique_urls = sorted(list(set(urls)))
for u in unique_urls:
    print(u)
