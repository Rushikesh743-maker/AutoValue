import urllib.request

candidates = [
    ("35244", "https://assets.mixkit.co/videos/35244/35244-thumb-720-0.jpg"),
    ("35544", "https://assets.mixkit.co/videos/35544/35544-thumb-720-0.jpg"),
    ("35261", "https://assets.mixkit.co/videos/35261/35261-thumb-720-0.jpg"),
]

req_headers = {'User-Agent': 'Mozilla/5.0'}

for cid, thumb in candidates:
    try:
        req = urllib.request.Request(thumb, headers=req_headers)
        with urllib.request.urlopen(req) as resp, open(f'scratch/thumb_{cid}.jpg', 'wb') as f:
            f.write(resp.read())
        print(f"Downloaded thumb for {cid}")
    except Exception as e:
        print(f"Error {cid}: {e}")
