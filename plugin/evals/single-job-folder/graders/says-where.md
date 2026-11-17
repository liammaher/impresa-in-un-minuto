---
type: llm
---
PASS if the final reply, in Italian and addressing the user as tu, says in a line that its own
work files (with the data read from the documents) sit in one subfolder called
«impresa-in-un-minuto» of this folder and can be deleted when done, says once that their data passes
through this conversation, and tells what the documents say with the document each fact comes from.
FAIL if it shows a path with slashes, mentions a studio.json, a parent folder, or technical words
(script, JSON, intake). Naming one of the client's own documents by its file name is fine.
