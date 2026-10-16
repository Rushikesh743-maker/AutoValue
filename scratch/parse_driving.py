import re

with open(r'C:\Users\Hrushikesh\.gemini\antigravity-ide\brain\cca39500-a570-403b-93fb-d2df04d4c065\.system_generated\steps\130\content.md', 'r', encoding='utf-8') as f:
    text = f.read()

# find json objects with name and contentUrl
matches = re.findall(r'\{"@context":"https://schema.org","@type":"VideoObject"[^}]+\}', text)
print(f"Found {len(matches)} VideoObjects")
for m in matches:
    print(m)

# also find cdn.coverr.co/videos/ urls
urls = re.findall(r'https://cdn\.coverr\.co/videos/[^"\s]+', text)
for u in set(urls):
    if 'thumbnail' in u or '1080p' in u or '720p' in u:
        print(u)
