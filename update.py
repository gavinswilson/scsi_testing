from datetime import datetime

with open("README.md", "a") as f:
    f.write(f"\nUpdated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
