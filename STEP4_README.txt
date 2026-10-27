REQUIEM — Step 4 Additions

This update adds four NEW files. It does not overwrite your existing archaeology
engine, tests, README, or Git history.

In a VS Code terminal (from the project root):

  cd ~/Documents/requiem-starter
  unzip -o ~/Downloads/requiem-step4.zip -d .
  python3 -m unittest discover -s tests -v
  python3 -m scripts.demo_afterlife

You should see 9 tests pass (3 existing + 6 new). The demo shows a possible
afterlife and a function with no new structural successor.

Finally commit the working milestone:

  git add backend/afterlife.py tests/test_afterlife.py scripts STEP4_README.txt
  git commit -m "Detect possible afterlives of deleted Python functions"

No dependencies to install. All analysis remains on your Mac.
