import hashlib
import pathlib
import urllib.request

url = "https://raw.githubusercontent.com/fred-framework/meta-retis/02995952c2df1819657f2998e6e3a63c0e2aaa63/recipes-kernel/linux/files/patch-5.4.3-rt1.patch"
expected = "684ad81ec7d25bd4b268ae5ced3c24bc53b3595aea5c528518cdeeb2e8bee26a"
target = pathlib.Path(__file__).resolve().parents[1] / "inputs" / "patch-5.4.3-rt1.patch"
with urllib.request.urlopen(url, timeout=60) as response:
    data = response.read()
digest = hashlib.sha256(data).hexdigest()
if len(data) != 822792 or digest != expected:
    raise RuntimeError(f"Patch integrity mismatch: {len(data)} bytes, sha256={digest}")
target.write_bytes(data)
print(f"PATCH_OK bytes={len(data)} sha256={digest}")
