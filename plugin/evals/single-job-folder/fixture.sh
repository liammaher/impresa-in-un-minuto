#!/usr/bin/env bash
# A single job: the open folder is the client's own, with the documents loose in it (no subfolder,
# no studio.json), as an architect hands over a project folder. Nothing of ours may land outside
# it, and nothing in the documents' folder itself but one subfolder, impresa-in-un-minuto/.
set -euo pipefail
cp "$(cd "$(dirname "${BASH_SOURCE[0]}")/../_dossier" && pwd)"/*.pdf .
