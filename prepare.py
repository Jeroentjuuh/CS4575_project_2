import os
import shutil
import csv
import xml.etree.ElementTree as ET

from pathlib import Path
from subprocess import run

from utils import run_command_in_external_project


def clone_and_build_joularjx(joularjx_dir):
    run(["git", "clone", "https://github.com/joular/joularjx.git", joularjx_dir])
    # shutil.copy(Path("config.properties"), Path(joularjx_dir, "config.properties"))
    os.chdir(joularjx_dir)
    run("mvn clean install -DskipTests", shell=True)
    os.chdir(joularjx_dir.parents[0])
    joularjx_path = Path(joularjx_dir, "target", list(filter(lambda x: x.endswith(".jar") and "joularjx" in x, os.listdir(Path(joularjx_dir, "target"))))[0])
    return joularjx_path


def clone_testing_repositories(project, project_git, testing_repositories_dir):
    repo_url = f"https://github.com/{project_git}.git"
    repo_dir = Path(testing_repositories_dir, project)
    print(f"Cloning {project_git} into {repo_dir}")
    if not repo_dir.exists():
        run(["git", "clone", repo_url, repo_dir])
    else:
        print(f"Repository {project} already exists. Skipping clone.")


def add_joularjx_to_project(project_dir, joularjx_path):
	# Add JoularJX config file to project
	shutil.copy(Path("config.properties"), Path(project_dir, "config.properties"))

	old_path = os.getcwd()
	print(f"Changing directory to {project_dir}")
	os.chdir(project_dir)

	for xml_file in Path(project_dir).rglob("pom.xml"):
		tree = ET.parse(xml_file)
		prefix = tree.getroot().tag.replace("project", "")
		ET.register_namespace("", prefix[1:-1])
		tree = ET.parse(xml_file)

		# Add joularjx to existing surefire config in pom.xml
		found_surefire = 0
		for plugin in tree.iter(f"{prefix}plugin"):
			artifactId = plugin.find(f"{prefix}artifactId").text
			if "maven-surefire-plugin" in artifactId:
				found_surefire += 1
				if plugin.find(f"{prefix}configuration") is None:
					plugin.append(ET.Element(f"{prefix}configuration"))
				configuration = plugin.find(f"{prefix}configuration")
				if configuration.find(f"{prefix}argLine") is None:
					configuration.append(ET.Element(f"{prefix}argLine"))
				argLine = plugin.find(f"{prefix}configuration/{prefix}argLine")
				if argLine.text is None:
					argLine.text = f"-javaagent:\"{joularjx_path}\""
				elif "joularjx" not in argLine.text.lower():
					argLine.text = f"-javaagent:\"{joularjx_path}\" {argLine.text}"
		
		# If no surefire config was found, insert one into pom.xml
		if found_surefire > 0:
			print(f"Found surefire plugin in {project_dir.stem}")
		else:
			print(f"No surefire in {project_dir.stem}")
			surefire_element = ET.fromstring(f"""<plugin>
		<artifactId>maven-surefire-plugin</artifactId>
		<version>3.5.2</version>
		<configuration>

		<trimStackTrace>false</trimStackTrace>
		<argLine>-javaagent:"{joularjx_path}"</argLine>
		</configuration>
	</plugin>""")
			for plugins_list in tree.iter(f"{prefix}plugins"):
				plugins_list.append(surefire_element)
		tree.write(xml_file)

	print(f"Switching back to {old_path}")
	os.chdir(old_path)
	
def add_test_packages_to_joularjx(project_dir=None):
    if project_dir is None:
        project_dir = os.getcwd()

    old_path = os.getcwd()
    print(f"Chaning directory to {project_dir}")
    os.chdir(project_dir)

	# Find packages containing tests in external project
    test_packages = set()
    for java_tests in Path().rglob("*/test/**/*.java"):
        print(f"Java test file found: {java_tests}")
        print(f"Java test file parent: {java_tests.parent.name}")
        with open(java_tests, "r") as tests_file:
            for line in tests_file.readlines():
                if line.startswith("package"):
                    package_name = line.split(" ")[1][:-2]
                    test_packages.add(f"{package_name}.{Path(java_tests).stem}")
    with open(Path("config.properties"), "r") as joular_config:
        data = joular_config.read()
    data = data.replace("REPLACE-WITH-JOULAR-TEST-PACKAGES", ",".join(test_packages))
    with open(Path("config.properties"), "w") as joular_config:
        joular_config.write(data)
	
	# Copy this config file to any place where there is a pom.xml file
    config_path = Path("config.properties")
    for pom_xml in Path().rglob("pom.xml"):
        new_path = Path(pom_xml.parent, "config.properties")
        if not new_path.exists():
            shutil.copy(config_path, new_path)

    print(f"Switching back to {old_path}")
    os.chdir(old_path)
    

def build_testing_repositories(project_dir, log_path):
    run_command_in_external_project("mvn clean test", project_dir, log_path)

def prepare():
    # Create directories if they don't exist
    print("Creating directories...")

    Path("./external_projects").mkdir(exist_ok=True)
    Path("./logs").mkdir(exist_ok=True)
    Path("./logs").mkdir(exist_ok=True)
    Path("./joularjx").mkdir(exist_ok=True)
    Path("./results").mkdir(exist_ok=-True)
    Path("./plots").mkdir(exist_ok=True)

    joularjx_dir = Path(os.getcwd(), "joularjx")
    joularjx_path = clone_and_build_joularjx(joularjx_dir)
    print(f"JoularJX path: {joularjx_path}")


    testing_repositories_dir = Path(os.getcwd(), "external_projects")
    repositories_csv = Path(os.getcwd(), "testing_projects.csv")

    with open(repositories_csv, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        for line in reader:
            project = Path(line["project_name"]).stem
            log_path = Path(os.getcwd(), "logs", project + "_build.log")
            if line['enabled'] == "false":
                print(f"Skipping {line['project_name']}")
                continue

            project_path = Path(testing_repositories_dir, project)
            clone_testing_repositories(project, line["project_name"], testing_repositories_dir)
            add_joularjx_to_project(project_path, joularjx_path)
            add_test_packages_to_joularjx(project_path)
            build_testing_repositories(project_path, log_path)

    print("Repositories cloned and built successfully.")


if __name__ == "__main__":
    prepare()
