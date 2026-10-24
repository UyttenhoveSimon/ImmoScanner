# Security policy

## Reporting a vulnerability

Please do not open a public issue. Report it privately through
[GitHub's private vulnerability reporting](https://github.com/UyttenhoveSimon/ImmoScanner/security/advisories/new),
with what you found, how to reproduce it, and what it exposes.

You should hear back within a week. Fixes go to the latest version on
`master`; there are no maintained older releases.

## Scope

ImmoScanner runs on your own machine: it reads public listing pages, keeps a
local SQLite archive, and its web explorer listens on `127.0.0.1` by default.
Worth reporting, for instance: a way for a portal's page to run code or write
files through the scanner, or for the explorer to be reached or abused from
elsewhere. A portal's own anti-bot protection is out of scope: ImmoScanner
reports it and stops.
