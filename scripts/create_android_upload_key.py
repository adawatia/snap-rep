#!/usr/bin/env python3
"""Create a private Android upload key, its password, and a public certificate."""

import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
SECRETS = ROOT / ".secrets"
STORE = SECRETS / "android-upload.jks"
PASSWORD_FILE = SECRETS / "android-signing.env"
CERTIFICATE = SECRETS / "android-upload-cert.pem"


def main() -> int:
    keytool = shutil.which("keytool")
    if not keytool and os.environ.get("JAVA_HOME"):
        candidate = Path(os.environ["JAVA_HOME"]) / "bin" / "keytool"
        if candidate.is_file():
            keytool = str(candidate)
    if not keytool:
        print("Install a JDK or set JAVA_HOME so keytool is available.", file=sys.stderr)
        return 1
    if any(path.exists() for path in (STORE, PASSWORD_FILE, CERTIFICATE)):
        print("Upload key files already exist. Refusing to overwrite them.", file=sys.stderr)
        return 1

    old_umask = os.umask(0o077)
    try:
        SECRETS.mkdir(mode=0o700, exist_ok=True)
        password = secrets.token_hex(32)
        env = os.environ.copy()
        env["SNAPREP_NEW_KEY_PASSWORD"] = password
        common = ["-keystore", str(STORE), "-storepass:env", "SNAPREP_NEW_KEY_PASSWORD"]
        try:
            subprocess.run(
                [
                    keytool, "-genkeypair", *common,
                    "-alias", "snaprep", "-keyalg", "RSA", "-keysize", "4096",
                    "-sigalg", "SHA256withRSA", "-validity", "10000",
                    "-dname", "CN=SnapRep Upload Key, O=Datlabs, C=IN",
                    "-storetype", "JKS", "-keypass:env", "SNAPREP_NEW_KEY_PASSWORD",
                ],
                env=env, check=True, capture_output=True, text=True,
            )
            subprocess.run(
                [keytool, "-exportcert", "-rfc", *common, "-alias", "snaprep", "-file", str(CERTIFICATE)],
                env=env, check=True, capture_output=True, text=True,
            )
            result = subprocess.run(
                [keytool, "-list", "-v", *common, "-alias", "snaprep"],
                env=env, check=True, capture_output=True, text=True,
            )
            match = re.search(r"SHA256:\s*([0-9A-F:]+)", result.stdout)
            if not match:
                raise RuntimeError("Could not read the upload certificate fingerprint")
            PASSWORD_FILE.write_text(
                f"export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD={password}\n",
                encoding="ascii",
            )
            PASSWORD_FILE.chmod(0o600)
            STORE.chmod(0o600)
            CERTIFICATE.chmod(0o600)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            for path in (STORE, PASSWORD_FILE, CERTIFICATE):
                path.unlink(missing_ok=True)
            print(f"Key creation failed: {exc}", file=sys.stderr)
            return 1
        print(f"Created {STORE.relative_to(ROOT)} and {CERTIFICATE.relative_to(ROOT)}")
        print(f"Credentials saved to {PASSWORD_FILE.relative_to(ROOT)} (mode 600)")
        print(f"Upload certificate SHA-256: {match.group(1)}")
        return 0
    finally:
        os.umask(old_umask)


if __name__ == "__main__":
    raise SystemExit(main())
