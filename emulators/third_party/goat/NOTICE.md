# acl-evaluate.py

`acl-evaluate.py` is copied unchanged from the goat project:

- Repository: usareur-af/goatcore
- Path: `ops/ansible/roles/goat-zenoh/files/acl-evaluate.py`
- Commit: `cbf2cb7f`
- Licence: public domain in the United States, Apache-2.0 elsewhere.

`goatgen.py` loads it to check the access lists it generates, and the tests use it to decide what each list allows. It reads the router file with regular expressions, not a JSON5 parser, so the text form of the generated files is fixed by it (see the Global Constraints of the plan).
