import subprocess
import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
screenshot_dir = r"C:\Users\Hrushikesh\OneDrive\Desktop\autovalue\scratch\screenshots"
os.makedirs(screenshot_dir, exist_ok=True)

desktop_path = os.path.join(screenshot_dir, "desktop_hero.png")
mobile_path = os.path.join(screenshot_dir, "mobile_hero.png")

# 1. Desktop view (1440x900)
cmd_desktop = [
    chrome_path,
    "--headless=new",
    f"--screenshot={desktop_path}",
    "--window-size=1440,900",
    "--virtual-time-budget=3000",
    "--hide-scrollbars",
    "http://localhost:5173/"
]
print("Capturing desktop screenshot to:", desktop_path)
res1 = subprocess.run(cmd_desktop, capture_output=True, text=True)
print("Desktop stdout:", res1.stdout)
print("Desktop stderr:", res1.stderr)

# 2. Mobile view (390x844)
cmd_mobile = [
    chrome_path,
    "--headless=new",
    f"--screenshot={mobile_path}",
    "--window-size=390,844",
    "--virtual-time-budget=3000",
    "--hide-scrollbars",
    "http://localhost:5173/"
]
print("Capturing mobile screenshot to:", mobile_path)
res2 = subprocess.run(cmd_mobile, capture_output=True, text=True)
print("Mobile stdout:", res2.stdout)
print("Mobile stderr:", res2.stderr)

print("Desktop file exists:", os.path.exists(desktop_path))
print("Mobile file exists:", os.path.exists(mobile_path))
