import urllib.request

urls = [
    ("1080p", "https://cdn.coverr.co/videos/coverr-black-suv-on-the-road-4297/1080p.mp4"),
    ("720p", "https://cdn.coverr.co/videos/coverr-black-suv-on-the-road-4297/720p.mp4"),
    ("poster", "https://cdn.coverr.co/videos/coverr-black-suv-on-the-road-4297/thumbnail?width=1920"),
]

req_headers = {'User-Agent': 'Mozilla/5.0'}

for name, url in urls:
    try:
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req) as resp:
            size = resp.headers.get('Content-Length')
            ctype = resp.headers.get('Content-Type')
            print(f"{name}: status={resp.status}, size={int(size)/1024/1024:.2f} MB, type={ctype}")
    except Exception as e:
        print(f"{name} error: {e}")
