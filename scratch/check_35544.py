import urllib.request

urls = [
    ("720p", "https://assets.mixkit.co/videos/35544/35544-720.mp4"),
    ("1080p", "https://assets.mixkit.co/videos/35544/35544-1080.mp4"),
    ("thumb", "https://assets.mixkit.co/videos/35544/35544-thumb-720-0.jpg")
]

req_headers = {'User-Agent': 'Mozilla/5.0'}

for name, url in urls:
    try:
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req) as resp:
            sz = resp.headers.get('Content-Length')
            sz_mb = int(sz)/(1024*1024) if sz else 0
            print(f"{name}: status={resp.status}, size={sz_mb:.2f} MB, type={resp.headers.get('Content-Type')}")
    except Exception as e:
        print(f"{name} error: {e}")
