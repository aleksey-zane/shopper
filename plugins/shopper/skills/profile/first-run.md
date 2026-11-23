# First run

A new user has no shopper project folder yet: the working directory has no `data/README.md`. Do these steps once, before the job that was asked for, then go on with that job. Ask nothing else.

1. **Python.** Run `python3 -c "import sys; print(sys.version_info >= (3, 9))"`. The plugin's calculations are Python scripts that need Python 3.9 or newer; they are tested on 3.9.6, the version Apple's command line tools put on a Mac.
   - It prints `True`: go on to step 2.
   - Otherwise, on a Mac (`uname` prints `Darwin`): send one plain message: one line saying that the plugin needs Python for its calculations and that on a Mac it comes with Apple's command line tools, then the question in bold, **Install them now?**, followed by `Reply yes or no.`
     - **yes:** run `xcode-select --install`. It opens Apple's installer window. Say in one line that the user clicks Install in that window and tells you when it has finished. When they do, run the check of this step again.
     - **no:** say in one line that the plugin cannot calculate without Python, and stop.
   - Otherwise, on any other system: say in one line that the plugin needs Python 3.9 or newer from https://www.python.org/downloads/ and that you go on once it is installed. Stop until the user says it is.
2. **The data folder.** Run `python3 <this skill's folder>/scripts/setup_project.py --project <the working directory>`. It creates `data/` there with its `README.md` and changes nothing that already exists. The working directory is now the shopper project folder.
3. Say in one line, in the user's language: `Your data is kept in <the data folder it printed>. Next time, open Claude in <the working directory>.`
