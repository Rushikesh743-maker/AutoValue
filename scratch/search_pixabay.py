import urllib.request
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

url = "https://pixabay.com/videos/search/car%20night/"
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8', errors='ignore')
        print(f"Fetched {len(html)} chars")
        video_links = re.findall(r'href="(/videos/[^"]+)"', html)
        print("Found video links:", len(video_links))
        for vl in list(set(video_links))[:10]:
            print("  https://pixabay.com" + vl)
except Exception as e:
    print("Error:", e)
