import re

with open(r'C:\Users\Hrushikesh\.gemini\antigravity-ide\brain\cca39500-a570-403b-93fb-d2df04d4c065\.system_generated\steps\189\content.md', 'r', encoding='utf-8') as f:
    text = f.read()

items = re.findall(r'href="(/free-stock-video/[^"]+)"', text)
for it in set(items):
    print(it)
