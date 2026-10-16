import urllib.request
import json

headers = {'User-Agent': 'AutoValueBot/1.0 (educational coding research)'}
# Wikimedia Commons API search for videos
url = "https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srsearch=car+night+driving+filetype:video&srnamespace=6&srlimit=10"
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        for item in data.get('query', {}).get('search', []):
            print(item['title'])
except Exception as e:
    print("Error:", e)
