from subprocess import run
from pathlib import Path
import os, stat
import shutil
import xml.etree.ElementTree as ET

def handle_remove_readonly(func, path, exc_info):
    # Change the file to be writable
    os.chmod(path, stat.S_IWRITE)
    # Retry the removal
    func(path)
    
def remove_directory(folder):
    # If running on Windows, use the 'rd' command
    if os.name == 'nt':
        # Use the /s switch to remove all subdirectories and files,
        # and /q for quiet mode
        subprocess.run(f'rd /s /q "{folder}"', shell=True)
    else:
        shutil.rmtree(folder, onerror=handle_remove_readonly)

# This will take the directory containing this script (scripts) and then go up one level.
config_path = Path(__file__).resolve().parent.parent / "config.properties"
print(f"Looking for config.properties at {config_path}")


# Clean up the previous run: remove logs and external_projects folders if they exist
for folder in ["./logs", "./external_projects"]:
    p = Path(folder)
    if p.exists():
        remove_directory(str(p))
# (They will be re-created later by mkdir)

# List of repositories (update with the ones you want to test)
repos = [
    "https://github.com/junit-team/junit4.git",
    "https://github.com/togglz/togglz.git",
    "https://github.com/julianhyde/sqlline.git",
    "https://github.com/okta/okta-spring-boot.git"
    # ... add more repos as desired
]

# Number of times to run each test for averaging energy measurements
num_runs = 3

if __name__ == "__main__":
    # Create directories if they don't exist
    Path("./external_projects").mkdir(exist_ok=True)
    Path("./logs").mkdir(exist_ok=True)
    Path("./joularjx").mkdir(exist_ok=True)

    # Build JoularJX
    joularjx_dir = Path(os.getcwd(), "joularjx")
    run(["git", "clone", "https://github.com/joular/joularjx.git", str(joularjx_dir)])
    os.chdir(joularjx_dir)
    build_result = run("mvn clean install -DskipTests", shell=True)
    if build_result.returncode != 0:
        raise RuntimeError("JoularJX build failed!")
    
    target_dir = Path(joularjx_dir, "target")
    # Look for the jar file in the target directory
    jar_files = list(filter(lambda x: x.endswith(".jar") and "joularjx" in x, os.listdir(target_dir)))
    if jar_files:
        joularjx_path = target_dir / jar_files[0]
        if joularjx_path.exists():
            print(f"JoularJX jar found: {joularjx_path}")
        else:
            raise FileNotFoundError("JoularJX jar file was listed but not found on disk.")
    else:
        raise FileNotFoundError("No JoularJX jar found in the target directory.")
    
    os.chdir(joularjx_dir.parent)

    # Now iterate over each repo:
    for repo in repos:
        project = Path(repo).stem  # the repo name
        project_dir = Path(os.getcwd(), "external_projects", project)
        print(f"Cloning {project}...")
        run(["git", "clone", repo, str(project_dir)])
        
        os.chdir(project_dir)
        print(f"Building and testing {project}...")
        
        # Remove previous joularjx-result directory if it exists in this project
        shutil.rmtree(f"{project_dir}/joularjx-result", ignore_errors=True)
        # Copy our config.properties into the project folder
        shutil.copy(str(config_path), f"{project_dir}/config.properties")

        
        log_path = Path("../../logs", project + "_build.log")

        if Path("pom.xml").exists():
            print("Detected Maven project")
            # Parse the pom.xml and update the surefire plugin configuration to add the -javaagent parameter.
            tree = ET.parse(Path(project_dir, "pom.xml"))
            # Determine the namespace prefix (if any)
            root_tag = tree.getroot().tag  # might be like "{http://maven.apache.org/POM/4.0.0}project"
            ns = ""
            if root_tag.startswith("{"):
                ns = root_tag.split("}")[0] + "}"
            # Iterate through plugins to find maven-surefire-plugin and update its argLine
            for plugin in tree.iter(f"{ns}plugin"):
                artifactId = plugin.find(f"{ns}artifactId")
                if artifactId is not None and "maven-surefire-plugin" in artifactId.text:
                    # Ensure a <configuration> exists
                    configuration = plugin.find(f"{ns}configuration")
                    if configuration is None:
                        configuration = ET.SubElement(plugin, f"{ns}configuration")
                    # Ensure an <argLine> exists
                    argLine = configuration.find(f"{ns}argLine")
                    if argLine is None:
                        argLine = ET.SubElement(configuration, f"{ns}argLine")
                        argLine.text = ""
                    # Append the javaagent option along with the property to ignore the platform check
                    joularjx_arg = f"-javaagent:\"{joularjx_path}\" -Djoularjx.ignorePlatformCheck=true"
                    if argLine.text is None or argLine.text.strip() == "":
                        argLine.text = joularjx_arg
                    elif "joularjx" not in argLine.text.lower():
                        argLine.text = f"{joularjx_arg} {argLine.text}"
            tree.write("pom.xml")

            # Run Maven test and save the output to a log file.
            with open(log_path, "w") as outfile:
                run(["mvn", "clean", "test"], stdout=outfile, stderr=outfile)
        elif Path("build.gradle").exists() or Path("build.gradle.kts").exists():
            print("Detected Gradle project")
            # Set GRADLE_OPTS to include the javaagent option
            os.environ["GRADLE_OPTS"] = f"-javaagent:{str(joularjx_path)} -Djoularjx.ignorePlatformCheck=true"
            with open(log_path, "w") as outfile:
                run(["gradle", "clean", "test"], stdout=outfile, stderr=outfile)
        else:
            print(f"No recognized build file found for {project}")
        
        os.chdir(project_dir.parents[1])

    print("Automation complete.")
