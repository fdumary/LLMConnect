import os
import pathspec
import subprocess

class RepoIndexer:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.default_ignores = [
            '.git/', 'node_modules/', '__pycache__/', '.venv/', 'venv/', 
            'env/', '.env', 'dist/', 'build/', '.llmconnect_data/'
        ]
        self.ignore_spec = self._load_gitignore()

    def _load_gitignore(self) -> pathspec.PathSpec:
        gitignore_path = os.path.join(self.root_dir, '.gitignore')
        lines = self.default_ignores.copy()
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                lines.extend(f.readlines())
        return pathspec.PathSpec.from_lines('gitwildmatch', lines)

    def _get_git_files(self) -> list:
        try:
            # Try to get only git-tracked files for a much cleaner tree
            result = subprocess.run(
                ['git', 'ls-files'], 
                cwd=self.root_dir, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return [f for f in result.stdout.splitlines() if f]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def generate_tree(self) -> str:
        # First try to use git ls-files for a clean map of only tracked files
        git_files = self._get_git_files()
        
        if git_files:
            # Build tree from git files
            tree = {}
            for file_path in git_files:
                parts = file_path.split('/')
                current = tree
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = None
            
            return self._format_tree_dict(tree)
        else:
            # Fallback to os.walk with robust ignores
            return self._fallback_os_walk_tree()

    def _format_tree_dict(self, tree: dict, indent: int = 0) -> str:
        lines = []
        prefix = ' ' * 4 * indent
        for name, subtree in sorted(tree.items()):
            if subtree is None:
                lines.append(f"{prefix}{name}")
            else:
                lines.append(f"{prefix}{name}/")
                lines.append(self._format_tree_dict(subtree, indent + 1))
        return "\n".join(lines)

    def _fallback_os_walk_tree(self) -> str:
        tree_lines = []
        for root, dirs, files in os.walk(self.root_dir):
            rel_root = os.path.relpath(root, self.root_dir)
            if rel_root == '.':
                rel_root = ''
            
            # Filter dirs in place
            dirs[:] = [d for d in dirs if not self.ignore_spec.match_file(os.path.join(rel_root, d) + '/')]
            
            level = rel_root.count(os.sep) if rel_root else 0
            indent = ' ' * 4 * level
            if rel_root:
                tree_lines.append(f"{indent}{os.path.basename(root)}/")
                sub_indent = ' ' * 4 * (level + 1)
            else:
                tree_lines.append(f"{os.path.basename(os.path.abspath(self.root_dir))}/")
                sub_indent = ' ' * 4
                
            # If the tree gets too deep, truncate it to prevent massive context
            if level > 4:
                tree_lines.append(f"{sub_indent}...")
                dirs[:] = [] # Stop descending
                continue

            for f in sorted(files):
                rel_file = os.path.join(rel_root, f) if rel_root else f
                if not self.ignore_spec.match_file(rel_file):
                    tree_lines.append(f"{sub_indent}{f}")

        return "\n".join(tree_lines)

    def get_repo_map(self) -> str:
        tree = self.generate_tree()
        # Hard limit the string length to prevent crashing the browser tab injection
        if len(tree) > 15000:
            tree = tree[:15000] + "\n... [Tree truncated due to size limit]"
        return f"Repository Map:\n{tree}\n"
