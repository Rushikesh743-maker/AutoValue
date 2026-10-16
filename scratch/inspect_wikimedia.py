import urllib.request
import json

headers = {'User-Agent': 'AutoValueBot/1.0 (educational coding research)'}

files = [
    "File:Cars driving at night.webm",
    "File:Traffic at dusk (time lapse).webm",
    "File:Traffic on bridge at night.webm",
    "File:Cars Passing by at Night.webm",
    "File:Marina Coastal Expressway, Singapore - 20141231.webm"
]

for title in files:
    url = f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}&prop=imageinfo&iiprop=url|size|mime|extmetadata&format=json"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            pages = data['query']['pages']
            for pid, pdata in pages.items():
                if 'imageinfo' in pdata:
                    info = pdata['imageinfo'][0]
                    print(title)
                    print("  URL:", info.get('url'))
                    print("  Size:", round(info.get('size', 0) / (1024*1024), 2), "MB")
                    print("  Mime:", info.get('mime'))
                    print("  Thumb:", info.get('thumburl'))
                    meta = info.get('extmetadata', {})
                    print("  License:", meta.get('LicenseShortName', {}).get('value'))
                    print()
    except Exception as e:
        print(f"Error on {title}: {e}")
