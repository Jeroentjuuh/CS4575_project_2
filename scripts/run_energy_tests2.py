from subprocess import run
from pathlib import Path
import os

# List of repositories (update with the ones you want to test)
repos = [
    "https://github.com/junit-team/junit4.git",
    "https://github.com/togglz/togglz.git",
    "https://github.com/julianhyde/sqlline.git",
    "https://github.com/okta/okta-spring-boot.git"
]

# Number of times to run each test for averaging energy measurements
num_runs = 5

if __name__ == "__main__":
    # Create directories if they don't exist
    Path("./external_projects").mkdir(exist_ok=True)
    Path("./logs").mkdir(exist_ok=True)

    for repo in repos:
        project = Path(repo).stem
        project_dir = Path(os.getcwd(), "external_projects", project)
        print(f"Cloning {project}...")
        run(["git", "clone", repo, str(project_dir)])
        
        os.chdir(project_dir)
        print(f"Building and testing {project}...")

        # Set up a log directory specific for this project
        project_log_dir = Path(os.getcwd()).parent.parent / "logs"
        # Ensure you capture both the build output and the energy measurements

        if Path("pom.xml").exists():
            print("Detected Maven project")
            # Instead of running "mvn clean test" directly, wrap it with JoularJX.
            # This assumes that running "joularjx mvn clean test" captures energy data.
            energy_command = ["joularjx", "mvn", "clean", "test"]
        elif Path("build.gradle").exists() or Path("build.gradle.kts").exists():
            print("Detected Gradle project")
            energy_command = ["joularjx", "gradle", "clean", "test"]
        else:
            print(f"No recognized build file found for {project}")
            os.chdir(project_dir.parents[1])
            continue

        # Run multiple iterations to gather sufficient data for analysis
        for run_number in range(1, num_runs + 1):
            log_path = project_log_dir / f"{project}_run{run_number}.log"
            print(f"Running test iteration {run_number} for {project}...")
            # Here, we run the energy measurement command and redirect output to a log file
            with open(log_path, "w") as outfile:
                run(energy_command, shell=False, stdout=outfile, stderr=outfile)
                
        # Return to the parent directory to process the next project
        os.chdir(project_dir.parents[1])

    print("Automation complete.")
