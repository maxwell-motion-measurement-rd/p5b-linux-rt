"""Run a saved bash script on the verified P5B build VM over SSH."""
import pathlib
import subprocess
import sys

workspace = pathlib.Path(__file__).resolve().parents[2]
config = workspace / "work" / "ssh" / "config"
script = pathlib.Path(sys.argv[1]).resolve()
payload = script.read_bytes().replace(b"\r\n", b"\n")
result = subprocess.run(
    ["ssh", "-F", str(config), "p5b-vm", "bash", "-se"],
    input=payload,
)
raise SystemExit(result.returncode)
