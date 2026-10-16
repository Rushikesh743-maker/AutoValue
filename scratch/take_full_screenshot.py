import subprocess
import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
screenshot_dir = r"C:\Users\Hrushikesh\OneDrive\Desktop\autovalue\scratch\screenshots"
full_path = os.path.join(screenshot_dir, "desktop_full_page.png")

cmd = [
    chrome_path,
    "--headless=new",
    f"--screenshot={full_path}",
    "--window-size=1440,2400",
    "--virtual-time-budget=3000",
    "--hide-scrollbars",
    "http://localhost:5173/"
]
subprocess.run(cmd, check=True)
print("Full page captured:", os.path.exists(full_path))
