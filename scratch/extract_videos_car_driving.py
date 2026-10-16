import json, re

with open(r'C:\Users\Hrushikesh\.gemini\antigravity-ide\brain\cca39500-a570-403b-93fb-d2df04d4c065\.system_generated\steps\91\content.md', 'r', encoding='utf-8') as f:
    text = f.read()

m = re.search(r'\"video\":(\[.*?\])\}\<\/script\>', text)
if m:
    vlist = json.loads(m.group(1))
    for v in vlist:
        print(v.get('name'))
        print('  Desc:', v.get('description'))
        print('  Dur:', v.get('duration'))
        print('  URL:', v.get('contentUrl'))
        print('  Thumb:', v.get('thumbnailUrl'))
        print()
else:
    print("No structured video data found")
