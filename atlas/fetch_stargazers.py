# -*- coding: utf-8 -*-
import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
if not TOKEN:
    tf = os.path.join(HERE, "token.txt")
    if os.path.exists(tf):
        TOKEN = open(tf, encoding="utf-8").read().strip()
if not TOKEN:
    sys.exit("no GITHUB_TOKEN env var and no token.txt")
REPO = "jwestraadt/PaperSpine"
OUT = os.path.join(HERE, "stargazers_raw.json")
LOG = os.path.join(HERE, "fetch_progress.txt")

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")

def api(url, retries=3):
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={
            "User-Agent": "paperspine-map",
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (403, 429):
                time.sleep(30 * (attempt + 1))
            else:
                time.sleep(5)
        except Exception:
            time.sleep(5)
    return None

def main():
    logins = []
    page = 1
    while True:
        batch = api(f"https://api.github.com/repos/{REPO}/stargazers?per_page=100&page={page}")
        if batch is None:
            # A None (vs an empty list) means the API was unreachable after
            # retries. Aborting loudly avoids publishing a truncated/empty
            # atlas as if the repo had lost its stargazers.
            sys.exit(f"stargazer fetch failed at page {page} (API unreachable); aborting")
        if not batch:
            break
        logins += [u["login"] for u in batch]
        log(f"stargazer page {page}: total {len(logins)}")
        if len(batch) < 100:
            break
        page += 1
    log(f"all logins fetched: {len(logins)}")

    done = {}
    if os.path.exists(OUT):
        try:
            done = {u["login"]: u for u in json.load(open(OUT, encoding="utf-8"))}
        except Exception:
            done = {}
    todo = [l for l in logins if l not in done]
    log(f"profiles to fetch: {len(todo)} (cached {len(done)})")

    def fetch_user(login):
        u = api(f"https://api.github.com/users/{login}")
        if u is None:
            return {"login": login, "location": None, "company": None, "name": None, "bio": None, "followers": 0}
        return {
            "login": u.get("login", login),
            "location": u.get("location"),
            "company": u.get("company"),
            "name": u.get("name"),
            "bio": u.get("bio"),
            "followers": u.get("followers", 0),
        }

    count = len(done)
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_user, l): l for l in todo}
        for fut in as_completed(futs):
            r = fut.result()
            done[r["login"]] = r
            count += 1
            if count % 100 == 0:
                json.dump(list(done.values()), open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
                log(f"profiles fetched: {count}/{len(logins)}")

    ordered = [done[l] for l in logins if l in done]
    json.dump(ordered, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"DONE: {len(ordered)} users saved")

if __name__ == "__main__":
    main()
