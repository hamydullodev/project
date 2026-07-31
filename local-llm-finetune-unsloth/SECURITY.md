# Security Policy

## Supported versions

This is an actively developed educational/portfolio project — only the latest commit on `main` is supported.

## Reporting a vulnerability

Please do **not** open a public issue for security vulnerabilities. Instead, email **abduroshyd@gmail.com** with:

- A description of the vulnerability and its impact
- Steps to reproduce
- Any relevant logs or PoC code

You should receive a response within a few days. Once confirmed, a fix will be prioritized and credited to you (unless you prefer to stay anonymous) once released.

## Scope notes

- This project loads model weights from Hugging Face and runs local inference — treat any dataset or config file from an untrusted source with the same caution you'd apply to any code you `pip install` or `git clone`.
- The Streamlit app is intended for local/single-user use, not as a public-facing multi-tenant service, unless you add your own authentication layer.
