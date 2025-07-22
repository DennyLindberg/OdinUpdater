import sublime
import sublime_plugin
import os
import subprocess
import threading
import re

class OdinUpdaterCommand(sublime_plugin.ApplicationCommand):
    def __init__(self):        
        self.build_info = {
            'odin_tag': "unknown-tag",
            'odin_commit': "unknown-commit",
            'odin_author': "unknown-author",
            'odin_date': "unknown-date",
            'odin_verify_msg': None,
            'odin_build_version': "unknown-version",
            'ols_commit': "unknown-commit",
            'ols_author': "unknown-author",
            'ols_date': "unknown-date",
            'update_error': "",
        }
        
        self.git_odin_repo = None
        self.git_odin_folder = None
        self.git_ols_repo = None
        self.git_ols_folder = None
        self.update_ols = True
    
    def get_setting(self, key, default=None):
        settings = sublime.load_settings('OdinUpdater.sublime-settings')
        os_specific_settings = {}
        if sublime.platform() == 'windows':
            os_specific_settings = sublime.load_settings('OdinUpdater (Windows).sublime-settings')
        elif sublime.platform() == 'osx':
            os_specific_settings = sublime.load_settings('OdinUpdater (OSX).sublime-settings')
        else:
            os_specific_settings = sublime.load_settings('OdinUpdater (Linux).sublime-settings')
        return os_specific_settings.get(key, settings.get(key, default))
        
    def run(self, odin_repo_url=None, odin_folder=None, ols_repo_url=None, ols_folder=None, update_ols=None):
        user_settings_path = os.path.join(sublime.packages_path(), 'User', 'OdinUpdater.sublime-settings')
        if not os.path.exists(user_settings_path):            
            settings_content = '''{
    // Official source code for Odin
    "odin_repo_url": "https://github.com/odin-lang/Odin.git",

    // Source code for Odin Language Server  
    "ols_repo_url": "https://github.com/DanielGavin/ols.git",

    // Where Odin will be installed on your system
    "odin_folder": "C:\\\\odin",
    
    // Where Odin Language Server will be installed on your system
    "ols_folder": "C:\\\\ols",

    // Whether Odin Language Server should be installed or updated
    "update_ols": true
}'''

            with open(user_settings_path, 'w') as f:
                f.write(settings_content)
            
            sublime.active_window().open_file(user_settings_path)
            sublime.message_dialog("Initial Setup\n\nUser settings created for Odin Updater. Please check that all folders in the settings are correct for your system and then run Odin Updater again.")
            return
        
        self._log("Updating/Installing Odin compiler and Odin Language Server...")
        
        window = sublime.active_window()
        if window:
            window.run_command("show_panel", {"panel": "console", "toggle": False})
        
        self.git_odin_repo = odin_repo_url or self.get_setting('odin_repo_url', '')
        self.git_odin_folder = odin_folder or self.get_setting('odin_folder', '')
        self.git_ols_repo = ols_repo_url or self.get_setting('ols_repo_url', '')
        self.git_ols_folder = ols_folder or self.get_setting('ols_folder', '')
        self.update_ols = update_ols or self.get_setting('update_ols', True)
                
        threading.Thread(target=self._run_async).start()

    def _run_async(self):
        try:
            self._log(f"Odin: {self.git_odin_folder} {self.git_odin_repo}")
            if self.update_ols:
                self._log(f"OLS: {self.git_ols_folder} {self.git_ols_repo}")
            else:
                self._log(f"OLS: Skipped (update_ols = False)")
            
            if self.update_ols:
                if not self._check_package_installed("LSP"):
                    return sublime.message_dialog("The 'LSP' package for Sublime Text is not installed. Install it using 'Package Control: Install Package'. Run Odin Updater after that.")
            
            if not self._check_package_installed("Odin"):
                return sublime.message_dialog("The 'Odin' package for Sublime Text is not installed. Install it using 'Package Control: Install Package'. Run Odin Updater after that.")
            
            if not self._check_git_available():
                return sublime.error_message(f"Odin Update failed: could not find Git, make sure Git is installed and available in system paths and try again.")
            
            if self.update_ols:
                self._log("Disabling LSP globally...")
                sublime.run_command("lsp_disable_language_server_globally")
            
            if not self._checkout_git_repo(self.git_odin_folder, self.git_odin_repo):
                return sublime.error_message(f"Failed to checkout git repo for Odin:\n\n{self.build_info['update_error']}")
            
            if self.update_ols:
                if not self._checkout_git_repo(self.git_ols_folder, self.git_ols_repo):
                    return sublime.error_message(f"Failed to checkout git repo for Odin Language Server:\n\n{self.build_info['update_error']}")
            
            self._log(f"Updating {self.git_odin_folder}...")
            if not self._pull_and_build_odin(self.git_odin_folder):
                return sublime.error_message(f"Failed to pull latest and build the Odin compiler, see the log for details.\n\nMake sure you have the MSVC compiler installed, it's required to build Odin from source.\n\nFull Visual Studio installer\nhttps://visualstudio.microsoft.com/\n\nMSVC only (PortableBuildTools)\nhttps://github.com/Data-Oriented-House/PortableBuildTools\n\nMSVC only (python script)\nhttps://gist.github.com/mmozeiko/7f3162ec2988e81e56d5c4e22cde9977")

            if self.update_ols:
                self._log(f"Updating {self.git_ols_folder}...")
                if not self._pull_and_build_ols(self.git_ols_folder):
                    return sublime.error_message(f"Failed to pull latest and build the Odin Language Server, see the log for details")
                
                self._log("Enabling LSP globally...")
                sublime.run_command("lsp_enable_language_server_globally")
            
            if not self._verify_odin_build(self.git_odin_folder):
                return sublime.error_message(f"Odin build failed validation\n\n{self.build_info['update_error']}")
                
            if self.build_info['odin_verify_msg']:
                sublime.message_dialog(self.build_info['odin_verify_msg'])
                
            if not self._check_package_installed("Odin"):
                sublime.message_dialog("The Odin package for Sublime Text is not installed. Install it using the Package Control: Install Package.")
            
            message = f"Update complete."
            message += f"\n\n-Odin {self.build_info['odin_tag']}\n{self.git_odin_folder} {self.git_odin_repo}\n{self.build_info['odin_author']}\n{self.build_info['odin_date']}\nCommit: {self.build_info['odin_commit']}"
            if self.update_ols:
                message += f"\n\n-Odin Language Server\n{self.git_ols_folder} {self.git_ols_repo}\n{self.build_info['ols_author']}\n{self.build_info['ols_date']}\nCommit: {self.build_info['ols_commit']}"
            else:
                message += f"\n\n-Odin Language Server\nSkipped (update_ols = False)"
            
            self._log(message)
            sublime.message_dialog(message)

        except Exception as e:
            self._log(f"ERROR: update failed: {str(e)}")
            sublime.error_message(f"Update failed: {str(e)}")

    def _log(self, message):
        print(f"[Odin Update] {message}")

    def _check_git_available(self):
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                shell=True,
                timeout=10
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                self._log(f"Git found: {version}")
                return True
            else:
                self._log("Git command failed")
                return False

        except FileNotFoundError:
            self._log("ERROR: Git not found in PATH")
            return False
        except subprocess.TimeoutExpired:
            self._log("ERROR: Git command timed out")
            return False
        except Exception as e:
            self._log(f"ERROR: Git check failed: {str(e)}")
            return False

    def _run_command_with_output(self, cmd, cwd, description=None, check_return_code=True):
        """
        Run a command with real-time output display

        Args:
            cmd: List of command arguments (e.g., ["git", "pull"])
            cwd: Working directory path
            description: Optional description for logging (defaults to command)
            check_return_code: Whether to raise exception on non-zero return code
        """
        try:
            if not os.path.exists(cwd):
                #raise Exception(f"Folder {cwd} does not exist")
                self._log(f"Folder {cwd} does not exist")
                return False

            # Generate description if not provided
            if description is None:
                description = " ".join(cmd)

            self._log(f"Running {description} in {cwd}...")

            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True,
                bufsize=1
            )

            # Read and display output line by line
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    self._log(f"  {line.strip()}")

            return_code = process.wait()

            if check_return_code and return_code != 0:
                self._log(f"{description} failed in {cwd} (return code: {return_code})")
                return False
            
            self._log(f"{description} completed in {cwd}")
            return True
            
        except Exception as e:
            self._log(f"ERROR: could not _run_command_with_output: {str(e)}")
            return False

    def _pull_and_build_ols(self, folder):
        """Updated function using the generalized command runner"""
        pull_result = self._run_command_with_output(
            ["git", "pull"], 
            folder, 
            "Git pull", 
            check_return_code=True
        )
        
        if not pull_result:
            return False
        
        build_path = os.path.join(folder, "build.bat")
        if not os.path.exists(build_path):
            self._log(f"build.bat not found in {folder}")
            return False

        return self._run_command_with_output(
            [build_path], 
            folder, 
            "`build.bat`", 
            check_return_code=False  # Ignore return code as requested
        )        
    
    def _pull_and_build_odin(self, folder):
        if not os.path.exists(folder):
            self._log(f"Folder {folder} does not exist")
            return False
        
        if not self._run_command_with_output(["git", "checkout", "master"], folder, "Checkout master branch"):
            # Fallback: create master branch
            if not self._run_command_with_output(["git", "checkout", "-b", "master", "origin/master"], folder, "Create master branch from origin/master"):
                self._log(f"Failed to checkout master branch")
                return False
        
        if not self._run_command_with_output(["git", "pull", "origin", "master"], folder, "Git pull from origin master"):
            self._log(f"Failed to Git Pull")
            return False
        
        if not self._run_command_with_output(["git", "fetch", "--tags"], folder, "Fetch tags"):
            self._log(f"Failed to Fetch Tags")
            return False
        
        latest_tag = self._find_latest_dev_tag(folder)
        if not latest_tag:
            self._log(f"No dev tags found matching format dev-YYYY-MM")
            return False
            
        self.build_info['odin_tag'] = latest_tag
        
        if not self._run_command_with_output(["git", "checkout", latest_tag], folder, f"Checkout latest dev tag: {latest_tag}"):
            self._log(f"Failed to checkout tag: {latest_tag}")
            return False
        
        build_path = os.path.join(folder, "build.bat")
        if not os.path.exists(build_path):
            self._log(f"build.bat not found in {folder}")
            return False

        if not self._run_command_with_output([build_path, "release"], folder, "`build.bat release`", check_return_code=False):
            self._log("Failed building Odin")
            return False
        else:
            self._log("Odin build completed")
            return True

    def _find_latest_dev_tag(self, folder):
        try:
            result = subprocess.run(
                ["git", "tag", "-l"], 
                cwd=folder, 
                capture_output=True, 
                text=True,
                shell=True
            )
            if result.returncode != 0:
                return None

            # Filter dev tags matching pattern dev-YYYY-MM
            dev_tags = []
            pattern = re.compile(r'^dev-(\d{4})-(\d{2})$')

            for tag in result.stdout.strip().split('\n'):
                tag = tag.strip()
                if not tag:  # Skip empty lines
                    continue
                match = pattern.match(tag)
                if match:
                    year, month = int(match.group(1)), int(match.group(2))
                    dev_tags.append((tag, year, month))

            if not dev_tags:
                return None

            # Sort by year, then month, and return the latest
            dev_tags.sort(key=lambda x: (x[1], x[2]), reverse=True)
            self._log(f"Found latest dev tag: {dev_tags[0][0]}")
            return dev_tags[0][0]
            
        except Exception as e:
            self._log(f"ERROR: could not retrieve tags: {str(e)}")
            return None
            
    def _show_repo_info(self, folder):
        """Display basic repository information"""
        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=folder,
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                self._log(f"Current branch: {branch}")

            # Get latest commit info
            result = subprocess.run(
                ["git", "log", "-1", '--pretty="%h|%an|%ad|%s"', "--date=iso"],
                cwd=folder,
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode == 0:
                commit_info = result.stdout.strip()
                if commit_info:
                    self._log(commit_info)
                    # Parse the formatted output: hash|author|date|subject
                    parts = commit_info.split('|', 3)
                    if len(parts) >= 4:
                        commit_hash, author, date, subject = parts

                        self._log(f"Latest commit: {commit_hash} - {subject}")
                        self._log(f"Author: {author}")
                        self._log(f"Date: {date}")

                        # Store commit info based on folder
                        if "odin" in folder.lower():
                            self.build_info['odin_commit'] = f"{commit_hash} - {subject}"
                            self.build_info['odin_author'] = author
                            self.build_info['odin_date'] = date
                        elif "ols" in folder.lower():
                            self.build_info['ols_commit'] = f"{commit_hash} - {subject}"
                            self.build_info['ols_author'] = author
                            self.build_info['ols_date'] = date

        except Exception as e:
            self._log(f"ERROR: could not retrieve repository info: {str(e)}")
         
    def _checkout_git_repo(self, folder, repo_url):
        try:
            if os.path.exists(os.path.join(folder, ".git")):
                self._log(f"Git repo already exists {folder} [{repo_url}]...")
                self._show_repo_info(folder)
                return True
            
            if os.path.exists(folder):
                self.build_info['update_error'] = f"ERROR: {folder} already exists and does not contain a valid .git repository. If this is an existing OLS or Odin installation it has to be a source build with a .git repository for this update script to work.\n\nRemove the folder and try again. The script will do a checkout from the official repository."
                
                return False
            
            self._log(f"Cloning {repo_url} to {folder}...")
            os.makedirs(folder, exist_ok=True)
            
            if not self._run_command_with_output(["git", "clone", repo_url, "."], folder, "Git Clone", check_return_code=True):
                self._log(f"Failed to clone {folder} {repo_url}")
                return False
            
            if os.path.exists(os.path.join(folder, ".git")):
                self._log(f"Repository cloned successfully {folder}")
                self._show_repo_info(folder)
                return True
            else:
                self._log("Clone appeared to succeed but .git folder is missing")
                return False

        except Exception as e:
            self._log(f"ERROR: checkout_git_repo failed: {str(e)}")
            return False
            
    def _check_odin_available(self):
        """Check if odin executable is available and show detailed information"""
        try:
            # Try to get odin version
            result = subprocess.run(
                ["odin", "version"],
                capture_output=True,
                text=True,
                shell=True,
                timeout=10
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                self._log(f"✓ Odin found: {version}")

                # Also try to get odin path for debugging
                try:
                    path_result = subprocess.run(
                        ["where", "odin"] if os.name == 'nt' else ["which", "odin"],
                        capture_output=True,
                        text=True,
                        shell=True,
                        timeout=5
                    )
                    if path_result.returncode == 0:
                        odin_path = path_result.stdout.strip()
                        self._log(f"  Odin location: {odin_path}")
                except:
                    pass  # Path detection is optional

                return True
            else:
                self._log("✗ Odin command failed")
                return False

        except FileNotFoundError:
            self._log("✗ ERROR: Odin executable not found in PATH")
            return False
        except subprocess.TimeoutExpired:
            self._log("✗ ERROR: Odin command timed out")
            return False
        except Exception as e:
            self._log(f"✗ ERROR: Odin check failed: {str(e)}")
            return False
        
    def _verify_odin_build(self, odin_folder):
        """Verify that Odin was built successfully"""
        odin_exe = os.path.join(odin_folder, "odin.exe")

        if not os.path.exists(odin_exe):
            self.build_info['update_error'] = f"✗ ERROR: odin.exe not found at {odin_exe}"
            self._log(self.build_info['update_error'])
            return False
        
        try:
            # Test the built executable directly
            result = subprocess.run(
                [odin_exe, "version"],
                capture_output=True,
                text=True,
                shell=True,
                timeout=10
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                self._log(f"✓ Built Odin executable works: {version}")
                self.build_info['odin_build_version'] = version
                
                # Check if it's in PATH
                if self._check_odin_available():
                    self._log("✓ Odin is also available in system PATH")
                else:
                    self._log("⚠ Odin built successfully but not in system PATH")
                    self._log(f"  Consider adding {odin_folder} to your PATH environment variable")
                    self.build_info['odin_verify_msg'] = f"Odin built successfully but not in system PATH.\nConsider adding {odin_folder} to your PATH environment variable."

                return True
            else:
                self.build_info['update_error'] = "✗ Built Odin executable failed to run"
                self._log(self.build_info['update_error'])
                return False

        except Exception as e:
            self.build_info['update_error'] = f"✗ Error testing built Odin: {str(e)}"
            self._log(self.build_info['update_error'])
            return False         
    
    def _check_package_installed(self, package_name):
        """Check if a package is installed via Package Control"""
        try:
            import sublime

            # Get Package Control settings
            pc_settings = sublime.load_settings("Package Control.sublime-settings")
            installed_packages = pc_settings.get("installed_packages", [])

            if package_name in installed_packages:
                self._log(f"✓ Package '{package_name}' is installed")
                return True
            else:
                self._log(f"✗ Package '{package_name}' is not installed")
                return False

        except Exception as e:
            self._log(f"Error checking package installation: {str(e)}")
            return False         

class AddOdinBuildSystemCommand(sublime_plugin.WindowCommand):
    def run(self):
        project_data = self.window.project_data()
        if not project_data:
            sublime.error_message("No project file found. Please save your project first.")
            return

        # modified version of Karl Zylinski's tutorial build system
        build_system_name = "sublime_odin_template"
        build_system = {
            "selector": "source.odin",
            "name": build_system_name,
            "working_dir": "$project_path",
            "file_regex": "^(.+)\\(([0-9]+):([0-9]+)\\) (.+)$",
            "shell": True,
            "variants": [
                {
                    "name": "Build and Run (temporary exe)", 
                    "cmd": ["odin", "run", ".", "-out:${project_base_name}.exe", "-vet-semicolon"]
                },
                {
                    "name": "Build and Run",
                    "cmd": ["odin", "build", ".", "-out:${project_base_name}.exe", "-vet-semicolon", "&&", "${project_base_name}.exe"]
                },
                {
                    "name": "Build Only",
                    "cmd": ["odin", "build", ".", "-out:${project_base_name}.exe", "-vet-semicolon"]
                }
            ]
        }
        
        if "build_systems" not in project_data:
            project_data["build_systems"] = []
        
        existing_index = None
        for i, bs in enumerate(project_data["build_systems"]):
            if bs.get("name") == build_system_name:
                existing_index = i
                break

        if existing_index is not None:
            sublime.message_dialog("Odin build system already exists in project")
        else:
            sublime.message_dialog("Odin build system added to project")
            project_data["build_systems"].append(build_system)
            self.window.set_project_data(project_data)
        
        project_file = self.window.project_file_name()
        if project_file:
            self.window.open_file(project_file)

class AddOdinFoldersToProjectCommand(sublime_plugin.WindowCommand):
    def get_setting(self, key, default=None):
        settings = sublime.load_settings('OdinUpdater.sublime-settings')
        os_specific_settings = {}
        if sublime.platform() == 'windows':
            os_specific_settings = sublime.load_settings('OdinUpdater (Windows).sublime-settings')
        elif sublime.platform() == 'osx':
            os_specific_settings = sublime.load_settings('OdinUpdater (OSX).sublime-settings')
        else:
            os_specific_settings = sublime.load_settings('OdinUpdater (Linux).sublime-settings')
        return os_specific_settings.get(key, settings.get(key, default))
        
    def run(self):
        odin_root = self.get_setting('odin_folder', '')
        folder_paths = [
            odin_root + "\\base",
            odin_root + "\\core",
            odin_root + "\\examples",
            odin_root + "\\vendor",
        ]

        project_data = self.window.project_data()
        if not project_data:
            project_data = {}
        
        if "folders" not in project_data:
            project_data["folders"] = []
        
        existing_paths = [os.path.abspath(f["path"]) for f in project_data["folders"]]
        added_count = 0
        
        for folder_path in folder_paths:
            if os.path.exists(folder_path):
                abs_path = os.path.abspath(folder_path)
                if abs_path not in existing_paths:
                    project_data["folders"].append({"path": folder_path})
                    added_count += 1
                    existing_paths.append(abs_path)  # Prevent duplicates in same operation
        
        if added_count > 0:
            self.window.set_project_data(project_data)
            sublime.status_message(f"Added {added_count} folders to project")
        else:
            sublime.status_message("No new folders to add (already exist or paths not found)")
