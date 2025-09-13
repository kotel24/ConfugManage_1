import tkinter as tk
from tkinter import scrolledtext
import shlex
import platform
import getpass
import argparse


# ----------------- VFS Node -----------------
class VFSNode:
    def __init__(self, name, is_dir, parent=None):
        self.name = name
        self.is_dir = is_dir
        self.parent = parent   # ссылка на родителя
        self.children = {} if is_dir else None
        self.content = "" if not is_dir else None


# ----------------- Shell Emulator -----------------
class ShellEmulator(tk.Tk):
    def __init__(self, vfs_path=None, startup_script=None):
        super().__init__()

        self.vfs_path = vfs_path
        self.startup_script = startup_script
        self.history = []
        self.history_index = -1

        # создаём VFS
        self.vfs_root = VFSNode("/", True, None)
        self.cwd = self.vfs_root

        # для примера сразу сделаем /home/user
        home = VFSNode("home", True, self.vfs_root)
        self.vfs_root.children["home"] = home
        user = VFSNode("user", True, home)
        home.children["user"] = user
        file1 = VFSNode("text.txt", False, user)
        file1.content = "Hellow World\n"
        user.children["text.txt"] = file1

        self._setup_ui()
        self._display_welcome()

        # запуск скрипта если указан
        if self.startup_script:
            self.after(100, self._run_startup_script)

        self._display_prompt()

    # ---------------- UI ----------------
    def _setup_ui(self):
        self.title(f"Shell Emulator - {self.vfs_path if self.vfs_path else 'no VFS'}")
        self.geometry("900x600")

        self.text = scrolledtext.ScrolledText(
            self, wrap="word",
            bg="black", fg="white",
            insertbackground="white", font=("Consolas", 12)
        )
        self.text.pack(expand=True, fill="both")

        self.text.bind("<Return>", self._on_enter)
        self.text.bind("<BackSpace>", self._on_backspace)
        self.text.bind("<Key>", self._on_key)

        self.prompt_mark = None

    def _display_welcome(self):
        self._append_text("Welcome to the Shell Emulator!\n")
        self._append_text(f"VFS path: {self.vfs_path}\n")
        self._append_text(f"Startup script: {self.startup_script}\n")

    def _append_text(self, text):
        self.text.insert(tk.END, text)
        self.text.see(tk.END)

    def _display_prompt(self):
        username = getpass.getuser()
        hostname = platform.node()
        cwd_path = self._get_cwd_path()
        prompt = f"{username}@{hostname}:{cwd_path}$ "
        self._append_text(prompt)
        self.prompt_mark = self.text.index(tk.INSERT)

    # ---------------- Input handling ----------------
    def _on_backspace(self, event):
        if self.text.compare(tk.INSERT, ">", self.prompt_mark):
            return None
        return "break"

    def _on_key(self, event):
        if self.text.compare(tk.INSERT, "<", self.prompt_mark):
            self.text.mark_set(tk.INSERT, self.prompt_mark)
        return None

    def _on_enter(self, event):
        command = self.text.get(self.prompt_mark, tk.END).strip()
        self._append_text("\n")
        if command:
            self.history.append(command)
            self.history_index = len(self.history)
            self._execute_command(command)
        self._display_prompt()
        return "break"

    # ---------------- Command execution ----------------
    def _execute_command(self, command_line):
        parts = shlex.split(command_line)
        if not parts:
            return

        command, args = parts[0], parts[1:]

        try:
            if command == "ls":
                self._command_ls(args)
            elif command == "cd":
                self._command_cd(args)
            elif command == "pwd":
                self._command_pwd()
            elif command == "head":
                self._command_head(args)
            elif command == "uniq":
                self._command_uniq(args)
            elif command == "cp":
                self._command_cp(args)
            elif command == "clear":
                self.text.delete("1.0", tk.END)
            elif command == "exit":
                self.quit()
            else:
                self._append_text(f"{command}: command not found\n")
        except Exception as e:
            self._append_text(f"Error: {e}\n")

    # ---------------- Commands ----------------
    def _command_ls(self, args):
        if not self.cwd.children:
            self._append_text("empty home screen\n")
        else:
            self._append_text(" ".join(self.cwd.children.keys()) + "\n")

    def _command_cd(self, args):
        if not args:
            self.cwd = self.vfs_root
            return
        target = args[0]
        if target == "/":
            self.cwd = self.vfs_root
            return
        if target == "..":
            if self.cwd.parent:
                self.cwd = self.cwd.parent
            return
        if target in self.cwd.children and self.cwd.children[target].is_dir:
            self.cwd = self.cwd.children[target]
        else:
            self._append_text(f"cd: {target}: No such directory\n")

    def _command_pwd(self):
        self._append_text(self._get_cwd_path() + "\n")

    def _command_head(self, args):
        if not args:
            self._append_text("head: missing file operand\n")
            return
        filename = args[0]
        n = 10
        if len(args) > 1 and args[1].startswith("-n"):
            try:
                n = int(args[1][2:])
            except:
                pass
        if filename not in self.cwd.children or self.cwd.children[filename].is_dir:
            self._append_text(f"head: {filename}: No such file\n")
            return
        lines = self.cwd.children[filename].content.splitlines()
        for line in lines[:n]:
            self._append_text(line + "\n")

    def _command_uniq(self, args):
        if not args:
            self._append_text("uniq: missing file operand\n")
            return
        filename = args[0]
        if filename not in self.cwd.children or self.cwd.children[filename].is_dir:
            self._append_text(f"uniq: {filename}: No such file\n")
            return
        lines = self.cwd.children[filename].content.splitlines()
        prev = None
        for line in lines:
            if line != prev:
                self._append_text(line + "\n")
            prev = line

    def _command_cp(self, args):
        if not args:
            self._append_text("cp: missing file operand\n")
            return
        if len(args) < 2:
            self._append_text("cp: missing destination file operand\n")
            return
        src, dst = args[0], args[1]
        if src not in self.cwd.children:
            self._append_text(f"cp: cannot stat '{src}': No such file or directory\n")
            return
        if dst in self.cwd.children:
            self._append_text(f"cp: cannot overwrite '{dst}': File exists\n")
            return
        node = self.cwd.children[src]
        if node.is_dir:
            self._append_text(f"cp: -r not specified; omitting directory '{src}'\n")
        else:
            new_node = VFSNode(dst, False, self.cwd)
            new_node.content = node.content
            self.cwd.children[dst] = new_node

    # ---------------- Helpers ----------------
    def _get_cwd_path(self):
        path_parts = []
        node = self.cwd
        while node and node.parent is not None:
            path_parts.append(node.name)
            node = node.parent
        return "/" + "/".join(reversed(path_parts)) if path_parts else "/"

    def _run_startup_script(self):
        try:
            with open(self.startup_script, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    self._append_text(f"> {line}\n")
                    self._execute_command(line)
        except Exception as e:
            self._append_text(f"Error executing startup script: {e}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shell Emulator")
    parser.add_argument("--vfs-path", help="Path to VFS")
    parser.add_argument("--startup-script", help="Path to startup script")
    args = parser.parse_args()

    app = ShellEmulator(args.vfs_path, args.startup_script)
    app.mainloop()