# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- France and Germany: bienici.com, kleinanzeigen.de and immowelt.de, verified
  on captured pages; leboncoin.fr, seloger.com, pap.fr and
  immobilienscout24.de, kept unverified behind their anti-bot walls.
- `brrrr` command: ranks fixer-uppers against their postal code, with rent,
  gross yield and equity after `--works-per-m2`.
- Condition reading: listings needing work are spotted from their description
  (French, Dutch, German) and their energy certificate, with `--condition`.
- `yield`, `scan` and `serve` commands; several postal codes at once.
- Portal capture and area scan workflows, run from GitHub.
- AGENTS.md, llms.txt and the community files.

### Changed

- The command line moved from plac to cyclopts, one subcommand per question:
  `immoscanner scan ...` replaces `immoscanner Belgium ...`, `brrrr`, `yield`
  and `serve` replace the `--brrrr`, `--yield` and `--serve` flags.
- Ruff, with every rule, replaces black and isort; ty type-checks the tree;
  prek runs the hooks.

### Fixed

- `--yield` crashed on the region argument the command line passed it.
- Prices "on request" no longer break the statistics.

## 0.2.0

- Archive of every scan, with what changed since the previous one.
- Web explorer: places, listings, rental yields and a price map.
- Region searches, rental yields, source filters.

[Unreleased]: https://github.com/UyttenhoveSimon/ImmoScanner/commits/master
