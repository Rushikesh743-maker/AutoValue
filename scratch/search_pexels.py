import urllib.request
import re
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}

url = "https://www.pexels.com/search/videos/dark%20car%20night%20city/"
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8', errors='ignore')
        print(f"Fetched {len(html)} chars")
        # Look for video files or video links
        video_links = re.findall(r'/video/([^"]+)', html)
        print("Found video links:", len(video_links))
        for vl in list(set(video_links))[:10]:
            print("  https://www.pexels.com/video/" + vl)
except Exception as e:
    print("Error:", e)
