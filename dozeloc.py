import unittest
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tkfd
import tkinter.font as font
import tkinter.scrolledtext
from pathlib import Path
import sys
import subprocess
import os
import textwrap
import re
import webbrowser

# TODO enable automatic download of new exercises
# TODO allow to mix italic and bold
# TODO filter duplicate line breaks
# TODO allow images in markdown


class DozelocUI(ttk.Frame):
    def __init__(self, root=None, exdir=Path(".")):
        super().__init__(root)
        self.root = root
        self.root.title("Dozeloc")
        self.exdir = Path(exdir)
        self.create_widgets()
        self.grid(row=0, column=0, sticky="NESW", padx=10, pady=10)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    def exercises(self, exdir):
        # find folders which contain a folder called "test"
        exercises = [x for x in exdir.iterdir() if x.is_dir() and (x / "test").is_dir()]
        return sorted([x.name for x in exercises])

    def create_widgets(self):
        self.exercise_chooser = ttk.Combobox(self, values=self.exercises(self.exdir), state="readonly")
        self.exercise_chooser.bind("<<ComboboxSelected>>", self.select)
        self.exercise_chooser.current(0)
        self.exercise_label = ttk.Label(self, text="Exercise")
        self.solution_label = ttk.Label(self, text="Solution file")
        self.solution_chooser = FileChooser(self)
        self.check_button = ttk.Button(self, text="Check!", command=self.check)
        self.result = tkinter.scrolledtext.ScrolledText(self, state="disabled")
        self.result.config(padx=5, pady=5)
        self.exercise_text = MarkdownText(self)
        self.exercise_text.config(padx=5, pady=5)
        self.select(None)

        self.exercise_label.grid(row=0, column=0, sticky="W", padx=5)
        self.exercise_chooser.grid(row=0, column=1, sticky="EW", pady=5)
        self.solution_label.grid(row=1, column=0, sticky="W", padx=5)
        self.solution_chooser.grid(row=1, column=1, sticky="EW", pady=5)
        self.check_button.grid(row=2, column=0, columnspan=2, pady=5)
        self.result.grid(row=3, column=0, columnspan=2, sticky="NESW")
        self.exercise_text.grid(row=0, column=2, rowspan=4, sticky="NESW")
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(3, weight=1)
    
    def select(self, event):
        self.exercise_text.config(state="normal")
        ex = self.exdir / self.exercise_chooser.get()
        docs = [x for x in ex.iterdir() if x.suffix == ".md"]
        self.exercise_text.delete("1.0", "end")
        self.exercise_text.insert_markdown("1.0", docs[0].read_text(encoding="utf-8"))
        self.exercise_text.config(state="disabled")
        self.load_result(ex)

    def check(self):
        ex = self.exdir / self.exercise_chooser.get()
        test = [x for x in (ex / "test").iterdir() if x.suffix == ".py"]
        sol = Path(self.solution_chooser.textvar.get())
        res = ""
        correct = True
        for t in test:
            text, code = run_unittest(t, sol)
            correct = correct and code == 0
            res += text
            res += "\n"
        self.save_result(ex, res, correct)
        self.show_result(res, correct)

    def save_solution_path(self, ex, path):
        solfile = ex / "test" / "last_solution_path.txt"
        solfile.write_text(path, encoding="utf-8")

    def load_solution_path(self, ex):
        solfile = ex / "test" / "last_solution_path.txt"
        if not solfile.is_file():
            return
        path = Path(solfile.read_text(encoding="utf-8"))
        self.solution_chooser.set_file(path)

    def save_result(self, ex, res, correct):
        outfile = ex / "test" / "last_result.txt"
        prefix = "# correct = {}\n".format(correct)
        outfile.write_text(prefix + res, encoding="utf-8")

    def load_result(self, ex):
        infile = ex / "test" / "last_result.txt"
        if not infile.is_file():
            self.show_result("", None)
            return
        res = infile.read_text(encoding="utf-8")
        lines = res.splitlines()
        correct = None
        if lines[0] == "# correct = True":
            correct = True
        elif lines[0] == "# correct = False":
            correct = False
        if correct is not None:
            lines = lines[1:]
        res = "\n".join(lines)
        self.show_result(res, correct)

    def show_result(self, res, correct=None):
        self.result.config(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("1.0", res)
        self.result.config(state="disabled")
        if correct is None:
            self.result["background"] = "#DDD"
        elif correct:
            self.result["background"] = "#AFA"
        else:
            self.result["background"] = "#FAA"


class FileChooser(ttk.Frame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.create_widgets()
        self.initialdir = Path(".")

    def create_widgets(self):
        self.textvar = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.textvar)
        self.button = ttk.Button(self, text="Browse..", command=self.browse)
        self.entry.grid(column=0, row=0, sticky="EWNS")
        self.button.grid(column=1, row=0, sticky="NS")
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

    def browse(self):
        fn = tkfd.askopenfilename(title="Open file", filetypes=[("python code", "*.py")], initialdir=self.initialdir)
        if len(fn) > 0:
            self.textvar.set(fn)
            self.initialdir = Path(fn).parent

    def set_file(self, fpath):
        self.initialdir = fpath
        self.textvar.set(fpath)


class MarkdownText(tkinter.scrolledtext.ScrolledText):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config(wrap="word")
        self.fonts = {}
        for x in ['em', 'strong', 'code']:
            self.fonts[x] = font.nametofont("TkDefaultFont").copy()
        self.fonts['em'].config(slant="italic")
        self.fonts['strong'].config(weight="bold")
        self.fonts['code'].config(family=font.nametofont("TkFixedFont")["family"])
        for l in range(1, 5):
            f = font.nametofont(self["font"]).copy()
            # h4 = 1.33, h3 = 1.66, h2 = 1.99, h1 = 2.33
            f.config(size=int(round(f["size"] * (8-l)/3)))
            self.fonts["h{}".format(l)] = f
        for x in ['em', 'strong', 'code'] + ["h{}".format(l) for l in range(1,5)]:
            self.tag_config(x, font=self.fonts[x])
        self.tag_config("code", background="#DDD")
        for i in range(1, 10):
            self.tag_config("indent{}".format(i), lmargin1=20*i, lmargin2=20*i)

    def insert_markdown(self, index, md):
        current = index
        parser = MarkdownParser()
        for text, tags in parser.parse_markdown(md):
            print(tags, text)
            self.insert(current, text, tags)
            current = "insert"
        print("\n\n")
        for url in parser.hrefs:
            # NOTE: we need to bind the *current* value of url to the lambda
            # otherwise, the call will always use the value after the loop has ended
            self.tag_bind("href={}".format(url), "<1>", lambda ev, u=url: self.visit_url(u))
            self.tag_config("href={}".format(url), foreground="#33E", underline=True)

    def set_markdown_content(self, md):
        self.delete("1.0", "end")
        self.insert_markdown("1.0", md)

    def visit_url(self, url):
        print("visit", url)
        webbrowser.open(url)


class MarkdownParser(object):
    def __init__(self, indentation="    "):
        self.indentation = indentation
        self.incode = False
        self.hrefs = []

    def parse_markdown(self, md):
        result = []
        for line in md.splitlines():
            result.extend(self.parse_line(line))
        return result

    def parse_line(self, md, indentation="    "):
        rest = md
        # count indentation level
        indent = 0
        while rest.startswith(indentation):
            rest = rest[len(indentation):]
            indent += 1
        # handle multiline code
        if rest.startswith("```"):
            self.incode = not self.incode
            self.codeindent = indent
            return []
        if self.incode:
            indentoff = self.codeindent * len(indentation)
            return [(md[indentoff:] + "\n", ("code", "indent%d" % self.codeindent))]
        # handle headings
        if md.startswith("#"):
            level = 0
            self.persistent_tags = []
            while md[level] == "#":
                level += 1
            result = self.parse_inline(md[level+1:], tags=["h%d" % level])
            self.persistent_tags = []
            return result
        # handle paragraph break
        if len(rest.strip()) == 0:
            self.persistent_tags = []
            return [("\n\n", ())]
        result = []
        line_tags = []
        line_tags.extend(self.persistent_tags)
        line_tags.append("indent%d" % indent)
        # handle codes at start of line
        while re.search(r"^(\* |\- |\+ |\> |\d+\. )", rest) is not None:
            if rest[0] in ['*', '-', '+']:
                # handle unordered lists
                line_tags.append("ul")
                rest = rest[2:]
                # add newline and bullet point
                result.append(("\n\u2022 ", tuple(line_tags)))
            elif rest.startswith(">"):
                # handle blockquotes
                line_tags.append("blockquote")
                rest = rest[2:]
            else:
                # handle ordered lists
                number = re.find(r"^\d+").group(0)
                line_tags.append("ol")
                result.append(("{}. ".format(number), tuple(line_tags)))
                rest = rest[len(number)+2:]
        result.extend(self.parse_inline(rest, tags=line_tags))
        result.append((" ", tuple(line_tags)))
        return result

    def toggle(self, tag):
        if tag in self.persistent_tags:
            self.persistent_tags.remove(tag)
        else:
            self.persistent_tags.append(tag)

    def parse_inline(self, md, tags=[]):
        result = []
        # split at *, **, `, links, and images (only if not preceded by escape sign)
        tokens = re.split(r"\\?(\*{1,2}|`|!?\[.*?\]\(.*?\))", md)
        for t in tokens:
            if t == "*":
                self.toggle("em")
            elif t == "**":
                self.toggle("strong")
            elif t == "`":
                self.toggle("code")
            else:
                match = re.match(r"(!?)\[(.*?)\]\((.*?)\)", t)
                if match is not None:
                    if match.group(1) == "!":
                        # image
                        pass
                    else:
                        # hyperlink
                        hl = "href={}".format(match.group(3))
                        self.hrefs.append(match.group(3))
                        result.append((match.group(2), tuple(tags + self.persistent_tags + [hl])))
                else:
                    # add everything else as normal text
                    result.append((t, tuple(tags + self.persistent_tags)))
        return result


def run_unittest(test_file, solution_file):
    subenv = os.environ.copy()
    if "PYTHONPATH" not in subenv:
        subenv["PYTHONPATH"] = solution_file.parent
    else:
        subenv["PYTHONPATH"] += ":" + (solution_file.parent)
    res = subprocess.run(["python", test_file], env=subenv, timeout=60, capture_output=True)
    restxt = "" if len(res.stdout) == 0 else "{}\n\n".format(res.stdout.decode("utf-8"))
    restxt += str(res.stderr.decode("utf-8"))
    return (restxt, res.returncode)

if __name__ == "__main__":
    exdir = Path("../uebungen/dozentron")
    usage = textwrap.dedent("""\
    Usage: python dozeloc.py [exercise_definition_folder]
    """)
    if len(sys.argv) > 1:
        if Path(sys.argv[1]).is_dir():
            exdir = sys.argv[1]
        else:
            print(usage)
            print("{} does not exist or is not a folder".format(sys.argv[1]))
    root = tk.Tk()
    app = DozelocUI(root=root, exdir=exdir)
    app.mainloop()
