import re

with open(r'C:\Users\Hrushikesh\.gemini\antigravity-ide\brain\cca39500-a570-403b-93fb-d2df04d4c065\.system_generated\steps\183\content.md', 'r', encoding='utf-8') as f:
    text = f.read()

links = re.findall(r'https?://[^\s"\'\)]+', text)
mixkit_links = [l for l in links if 'mixkit' in l]
for l in set(mixkit_links):
    if any(ext in l for ext in ['.mp4', '.webm', 'item', 'video']):
        print(l)
