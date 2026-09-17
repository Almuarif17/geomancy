# notes/ - worked analyses, published as method rather than as a personal record

These are the documents where a real chart was read end to end, so the rule set can be checked
against a case instead of only against prose. The convention is strict:

* the **chart, the arithmetic, each rule's output and the verdict** are published;
* the **question asked, and anything identifying the querent, are not** - the file is scrubbed on
  entry by `library/tools/check_public_leaks.py`, which fails the build on a city name, an email, a
  phone number, an absolute home path, a screenshot filename or a line that reads as the asked
  question itself;
* personal castings live in `readings/` and screenshots in `uploads/`, both permanently gitignored.

If a note here ever needs the question to make sense, the fix is a synthetic question of the same
type (`kb/question_inventory.json` has 35 from the printed casebooks), not the real one.
