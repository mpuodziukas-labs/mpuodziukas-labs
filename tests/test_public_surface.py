import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def test_selftest_planted_cases():
    r = subprocess.run([sys.executable, os.path.join(HERE, "..", ".github", "public-surface.py"), "--selftest"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "FAIL" not in r.stdout
