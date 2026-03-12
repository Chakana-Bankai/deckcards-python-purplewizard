modules = [
    ("PIL", "Pillow"),
    ("numpy", "numpy"),
    ("cv2", "opencv-python"),
    ("noise", "noise"),
    ("pytweening", "pytweening"),
    ("soundfile", "soundfile"),
    ("librosa", "librosa"),
    ("pydantic", "pydantic"),
    ("dotenv", "python-dotenv"),
    ("rich", "rich"),
    ("networkx", "networkx"),
]

ok = True

for mod, pkg in modules:
    try:
        __import__(mod)
        print(f"[OK] {pkg}")
    except Exception as e:
        ok = False
        print(f"[FAIL] {pkg}: {e}")

print("\nSTACK READY" if ok else "\nSTACK INCOMPLETE")