#!/usr/bin/env python3
import os
import argparse
import jwt

def main():
    parser = argparse.ArgumentParser(description="Generate non-expiring local dev JWT for DapMeet.")
    parser.add_argument("--user-id", required=True, help="User ID (must exist in DB for API auth).")
    parser.add_argument("--email", default="dev@example.com", help="User email.")
    parser.add_argument("--name", default="Dev User", help="User name.")
    parser.add_argument("--secret", default=None, help="Override NEXTAUTH_SECRET (falls back to env).")
    args = parser.parse_args()

    secret = args.secret or os.getenv("NEXTAUTH_SECRET")
    if not secret:
        raise SystemExit("Error: NEXTAUTH_SECRET not set. Pass --secret or export NEXTAUTH_SECRET.")

    payload = {
        "sub": args.user_id,
        "email": args.email,
        "name": args.name,
        # Note: no 'exp' for non-expiring local token
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    print(token)

if __name__ == "__main__":
    main()
