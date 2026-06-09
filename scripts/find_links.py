import urllib.request
import re

urls = [
    "https://download.eclipse.org/eclipse/updates/4.39/R-4.39-202602260420/",
    "https://download.eclipse.org/modeling/emf/emf/builds/release/2.45.0/",
    "https://download.eclipse.org/tools/gef/classic/release/3.27.0/",
    "https://download.eclipse.org/tools/cdt/releases/12.4/cdt-12.4.0/"
]

for url in urls:
    print(f"Checking {url}")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        links = re.findall(r'href=[\'"]?([^\'" >]+)', html)
        found = False
        for link in links:
            if "github" in link or "commit" in link or "git" in link:
                print("  ->", link)
                found = True
        if not found:
            print("  -> No git links found")
    except Exception as e:
        print(f"  -> Error: {e}")
    print()
