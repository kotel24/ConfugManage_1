import tkinter as tk
from tkinter import scrolledtext
import os
import platform
import getpass
import argparse
import shutil


class VFSNode:
    def __init__(self, name, is_dir):
        self.name = name
        self.is_dir = is_dir
        self.children = {} if is_dir else None
        self.content = "" if not is_dir else None


class ShellEmulator(tk.Tk):
    def __init__(self, vfs_path=None, startup_script=None):
        super().__init__()

        self.vfs_path = vfs_path
        self.startup_script = startup_script
        self.history = []
        self.history_index = -1

        # VFS
        self.vfs_root = None
        self.cwd = None

        self._setup_ui()
        self._display_welcome()

        if vfs_path:
            self._load_vfs(vfs_path)

        if startup_script:
            self.after(100, self._run_startup_script)
        else:
            self._display_prompt()

    # ---------------- UI ----------------

    def _setup_ui(self):
        self.title(self._get_window_title())
        self.geometry("800x600")

        # Output
        self.output_area = scrolledtext.ScrolledText(
            self, state='disabled', wrap='word',
            bg='black', fg='white', font=('Consolas', 12)
        )
        self.output_area.pack(expand=True, fill='both', padx=5, pady=5)

        # Input
        input_frame = tk.Frame(self, bg='black')
        input_frame.pack(fill='x', padx=5, pady=5)

        tk.Label(input_frame, text=">", fg='white', bg='black', font=('Consolas', 12)).pack(side='left')

        self.input_entry = tk.Entry(
            input_frame, bg='black', fg='white',
            insertbackground='white', font=('Consolas', 12)
        )
        self.input_entry.pack(side='left', expand=True, fill='x', padx=(0, 5))
        self.input_entry.focus_set()
        self.input_entry.bind("<Return>", self._on_enter)
        self.input_entry.bind("<Up>", self._history_up)
        self.input_entry.bind("<Down>", self._history_down)

    def _get_window_title(self):
        username = getpass.getuser()
        hostname = platform.node()
        return f"Эмулятор - [{username}@{hostname}]"

    def _display_welcome(self):
        self._display_output("Welcome to the Shell Emulator!")
        self._display_output(f"VFS path: {self.vfs_path}")
        self._display_output(f"Startup script: {self.startup_script}")

    def _display_output(self, text):
        self.output_area.config(state='normal')
        self.output_area.insert(tk.END, text + "\n")
        self.output_area.config(state='disabled')
        self.output_area.see(tk.END)

    def _display_prompt(self):
        self.input_entry.delete(0, tk.END)
        self.output_area.config(state='normal')
        self.output_area.insert(tk.END, "> ")
        self.output_area.config(state='disabled')
        self.output_area.see(tk.END)

    # ---------------- Command handling ----------------

    def _on_enter(self, event=None):
        command = self.input_entry.get().strip()
        if not command:
            return

        self.history.append(command)
        self.history_index = len(self.history)

        self._display_output(f"> {command}")
        self._execute_command(command)
        self._display_prompt()

    def _history_up(self, event=None):
        if self.history and self.history_index > 0:
            self.history_index -= 1
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, self.history[self.history_index])
        return "break"

    def _history_down(self, event=None):
        if self.history and self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, self.history[self.history_index])
        return "break"

    def _execute_command(self, command_line):
        parts = command_line.split()
        if not parts:
            return

        parts = [os.path.expandvars(part) for part in parts]
        command, args = parts[0], parts[1:]

        if command == "ls":
            self._command_ls(args)
        elif command == "cd":
            self._command_cd(args)
        elif command == "pwd":
            self._command_pwd()
        elif command == "vfs-save":
            self._command_vfs_save(args)
        elif command == "exit":
            self.quit()
        else:
            self._display_output(f"Command not found: {command}")

    # ---------------- VFS Commands ----------------

    def _command_ls(self, args):
        if not self.cwd:
            self._display_output("No VFS loaded.")
            return
        if not self.cwd.is_dir:
            self._display_output("Not a directory.")
            return
        if self.cwd.children:
            self._display_output(" ".join(sorted(self.cwd.children.keys())))
        else:
            self._display_output("(empty directory)")

    def _command_cd(self, args):
        if not args:
            self._display_output("cd: missing argument")
            return
        target = args[0]

        if target == "/":
            self.cwd = self.vfs_root
            return

        if target == "..":
            if self.cwd == self.vfs_root:
                return
            path_parts = self._get_cwd_path().strip("/").split("/")
            path_parts = path_parts[:-1]
            node = self.vfs_root
            for p in path_parts:
                node = node.children[p]
            self.cwd = node
            return

        if target in self.cwd.children and self.cwd.children[target].is_dir:
            self.cwd = self.cwd.children[target]
        else:
            self._display_output(f"cd: {target}: No such directory")

    def _command_pwd(self):
        self._display_output(self._get_cwd_path())

    def _command_vfs_save(self, args):
        if not args:
            self._display_output("vfs-save: missing path")
            return
        save_path = args[0]
        if os.path.exists(save_path):
            self._display_output(f"Error: Path already exists on disk: {save_path}")
            return
        try:
            self._save_vfs_to_disk(self.vfs_root, save_path)
            self._display_output(f"VFS saved to {save_path}")
        except Exception as e:
            self._display_output(f"Error saving VFS: {e}")

    # ---------------- VFS Implementation ----------------

    def _load_vfs(self, root_path):
        if not os.path.isdir(root_path):
            self._display_output(f"Error: VFS path not found or not a directory: {root_path}")
            return

        def build_tree(path):
            node = VFSNode(os.path.basename(path) or "/", os.path.isdir(path))
            if node.is_dir:
                for name in os.listdir(path):
                    child_path = os.path.join(path, name)
                    node.children[name] = build_tree(child_path)
            else:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        node.content = f.read()
                except:
                    node.content = ""
            return node

        self.vfs_root = build_tree(root_path)
        self.cwd = self.vfs_root
        self._display_output(f"VFS loaded from {root_path}")

    def _save_vfs_to_disk(self, node, path):
        if node.is_dir:
            os.makedirs(path, exist_ok=True)
            for child_name, child_node in node.children.items():
                self._save_vfs_to_disk(child_node, os.path.join(path, child_name))
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(node.content or "")

    def _get_cwd_path(self):
        path = []
        node = self.cwd
        while node and node != self.vfs_root:
            path.append(node.name)
            # find parent
            node = self._find_parent(self.vfs_root, node)
        return "/" + "/".join(reversed(path))

    def _find_parent(self, current, target):
        if not current.is_dir:
            return None
        for child in current.children.values():
            if child == target:
                return current
            res = self._find_parent(child, target)
            if res:
                return res
        return None

    # ---------------- Startup script ----------------

    def _run_startup_script(self):
        try:
            with open(self.startup_script, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self._display_output(f"> {line}")
                        self._execute_command(line)
        except Exception as e:
            self._display_output(f"Error executing script: {e}")

        self._display_prompt()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Shell Emulator')
    parser.add_argument('--vfs-path', help='Path to VFS')
    parser.add_argument('--startup-script', help='Path to startup script')

    args = parser.parse_args()
    app = ShellEmulator(args.vfs_path, args.startup_script)
    app.mainloop()