from subprocess import Popen, run
from pathlib import Path
import os
import xml.etree.ElementTree as ET
import shutil
import csv
import sys
import matplotlib.pyplot as plt
import numpy as np

repos = [
	# "https://github.com/allure-framework/allure-java.git"
	# "https://github.com/apache/cassandra.git",
	# "https://github.com/apache/camel.git",
	# "https://github.com/apache/accumulo.git",
	# "https://github.com/1c-syntax/bsl-language-server.git",
	"https://github.com/hub4j/github-api.git",
	# "https://github.com/zendesk/maxwell.git",
	"https://github.com/zebrunner/carina.git", # No tests
	"https://github.com/yegor256/cactoos.git",
	# "https://github.com/xnio/xnio.git",
	"https://github.com/wmixvideo/nfe.git",
	# "https://github.com/twilio/twilio-java.git",
	"https://github.com/ta4j/ta4j.git",
	# "https://github.com/sqlancer/sqlancer.git",
	# "https://github.com/soot-oss/soot.git" # this does some sort of concurrency, is it a good one?
	"https://github.com/junit-team/junit4.git", # This one is private?
	# "https://github.com/okta/okta-spring-boot.git", # No tests
	"https://github.com/julianhyde/sqlline.git",
	# "https://github.com/togglz/togglz.git", # No tests
	# "https://github.com/eclipse-ee4j/jaxrs-api.git", # No tests
	"https://github.com/damianszczepanik/cucumber-reporting.git",
	"https://github.com/decorators-squad/eo-yaml.git",
	"https://github.com/dlsc-software-consulting-gmbh/preferencesfx.git",
	"https://github.com/forcedotcom/dataloader.git",
	# "https://github.com/forge/roaster.git" # No tests
]

def build_joularjx(joularjx_dir):
	if "--skip-joularjx-build" in sys.argv:
		print("Skipping JoularJX build")
	else:
		run(["git", "clone", "https://github.com/joular/joularjx.git", joularjx_dir])
		shutil.copy(Path("config.properties"), Path(joularjx_dir, "config.properties"))
		os.chdir(joularjx_dir)
		r = run("mvn clean install -DskipTests", shell=True)
		os.chdir(joularjx_dir.parents[0])
	joularjx_path = Path(joularjx_dir, "target", list(filter(lambda x: x.endswith(".jar") and "joularjx" in x, os.listdir(Path(joularjx_dir, "target"))))[0])
	return joularjx_path

def add_test_packages_to_joularjx(project_dir=None):
	if project_dir is None:
		project_dir = os.getcwd()
	
	# Find packages containing tests in external project
	test_packages = set()
	for java_tests in Path(project_dir).rglob("*.java"):
		if "test" in java_tests.name.lower():
			with open(java_tests, "r") as tests_file:
				for line in tests_file.readlines():
					if line.startswith("package"):
						package_name = line.split(" ")[1][:-2]
						test_packages.add(package_name)
	with open(Path("config.properties"), "r") as joular_config:
		data = joular_config.read()
	data = data.replace("REPLACE-WITH-JOULAR-TEST-PACKAGES", ",".join(test_packages))
	with open(Path("config.properties"), "w") as joular_config:
		joular_config.write(data)

def mvn_add_joularjx(project_dir, joularjx_path):
	# Add JoularJX config file to project
	shutil.copy(Path("config.properties"), Path(project_dir, "config.properties"))

	old_path = os.getcwd()
	os.chdir(project_dir)

	tree = ET.parse(Path(project_dir, "pom.xml"))
	prefix = tree.getroot().tag.replace("project", "")
	ET.register_namespace("", prefix[1:-1])
	tree = ET.parse(Path(project_dir, "pom.xml"))

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
	tree.write("pom.xml")

	add_test_packages_to_joularjx(project_dir)
	os.chdir(old_path)

def extract_joularjx_csv_files(project_dir, prefix=0):
	prefix = str(prefix)
	# Move joularjx files to results folder
	for csv_file in Path(project_dir).rglob("*.csv"):
		if "joularJX" in csv_file.name:
			csv_name = "-".join([prefix, project] + csv_file.name.split("-")[2:])
			shutil.move(csv_file.resolve(), Path("results", csv_name))

def run_command_in_external_project(command, project_dir, log_path=None):
	old_dir = os.getcwd()
	os.chdir(project_dir)
	if log_path is None:
		r = run(command, shell=True)
	else:
		with open(log_path, "w") as outfile:
			r = run(command, shell=True, stdout=outfile, stderr=outfile)
	os.chdir(old_dir)

if __name__ == "__main__":
	# Create directories if they don't exist
	Path("./external_projects").mkdir(exist_ok=True)
	Path("./logs").mkdir(exist_ok=True)
	Path("./logs").mkdir(exist_ok=True)
	Path("./joularjx").mkdir(exist_ok=True)
	Path("./results").mkdir(exist_ok=-True)
	Path("./plots").mkdir(exist_ok=True)

	# Build joularjx
	joularjx_dir = Path(os.getcwd(), "joularjx")
	joularjx_path = build_joularjx(joularjx_dir)
	print(f"JoularJX path: {joularjx_path}")

	# Clone repos and run tests (setup phase)
	for repo in repos:
		project = Path(repo).stem
		project_dir = Path(os.getcwd(), "external_projects", project)
		print(f"Cloning {project}...")
		run(["git", "clone", repo, project_dir])

		print(f"Building and testing {project}...")
		
		log_path = Path(os.getcwd(), "logs", project + "_build.log")

		if Path(project_dir, "pom.xml").exists():
			print("Maven project")

			# Add JoularJX to project
			mvn_add_joularjx(project_dir, joularjx_path)

			# Run tests with joularjx
			run_command_in_external_project("mvn clean test", project_dir, log_path)
			
			extract_joularjx_csv_files(project_dir, "build")
			
		elif Path("build.gradle").exists() or Path("build.gradle.kts").exists():
			print("Gradle project, skipping...")
			continue
			with open(log_path, "w") as outfile:
				run("gradle clean test", shell=True, stdout=outfile, stderr=outfile)
		else:
			print(f"No recognized build file found for {project}")
			
		os.chdir(project_dir.parents[1])
	
	# Run tests multiple times (experiment phase)
	total_runs = 5
	for i in range(total_runs):
		print(f"Performing experiment run {i+1} of {total_runs}")
		for repo in repos:
			project = Path(repo).stem
			project_dir = Path(os.getcwd(), "external_projects", project)
			log_path = Path(os.getcwd(), "logs", f"{i}_{project}_run.log")
			print(f"Running {project} ({i+1}/{total_runs})")
			run_command_in_external_project("mvn test", project_dir, log_path)
			extract_joularjx_csv_files(project_dir, i)


	# Generate plots
	print("Generating plots")
	projects = {}
	for repo in repos:
		projects[Path(repo).stem] = []
	for csv_file in Path("./results").glob("*.csv"):
		# print(csv_file.name)
		for project in projects.keys():
			if project in csv_file.name and "filtered-methods-energy" in csv_file.name and not csv_file.name.startswith("build"):
				projects[project].append(csv_file)

	for project, csv_files in projects.items():
		if len(csv_files) > 0:
			print(f"Generating plot for {project}")
		else:
			print(f"No CSV files found for {project}, skipping...")
			continue
		tests_energy_consumption = {}
		for csv_file in csv_files:
			with open(csv_file, "r") as file:
				csv_data = csv.reader(file)
				for line in csv_data:
					test_name = line[0].split(".")[-1].split("$")[0]
					energy_consumption = float(line[1])
					if "test" not in line[0].lower():
						continue
					if test_name not in tests_energy_consumption:
						tests_energy_consumption[test_name] = []
					tests_energy_consumption[test_name].append(energy_consumption)
		if len(tests_energy_consumption.keys()) == 0:
			print(f"No tests found for {project}, skipping...")
			continue
		means = []
		for test, energy_consumptions in tests_energy_consumption.items():
			means.append((test, np.mean(energy_consumptions)))
		means = sorted(means, key=lambda x: x[1], reverse=True)
		boxes = [tests_energy_consumption[tup[0]] for tup in means[:10]]
		labels = [tup[0] for tup in means[:10]]
		bplot = plt.boxplot(boxes, labels=labels)
		plt.title(f"Test energy consumption of {project}")
		plt.xlabel("Test name")
		plt.ylabel("Energy consumption (J)")
		plt.xticks(rotation=90)
		plt.tight_layout()
		plt.savefig(Path("./plots", f"{project}.png"), dpi=300)
		plt.close()

	# for csv_file in Path("./results").glob("*.csv"):
	# 	if "filtered-methods-energy" in csv_file.name:
	# 		project_name = csv_file.stem.split("-")[1]
	# 		print(f"Generating plot for {project_name}")
	# 		tests_energy_consumption = {}
	# 		with open(csv_file, "r") as file:
	# 			csv_data = csv.reader(file)
	# 			for line in csv_data:
	# 				test_name = line[0].split(".")[-2].split("$")[0]
	# 				energy_consumption = float(line[1])
	# 				if "test" not in test_name.lower():
	# 					continue
	# 				if test_name not in tests_energy_consumption:
	# 					tests_energy_consumption[test_name] = 0.
	# 				tests_energy_consumption[test_name] += energy_consumption
	# 		plt.bar(tests_energy_consumption.keys(), tests_energy_consumption.values())
	# 		plt.title(f"Test energy consumption of {project_name}")
	# 		plt.xlabel("Test name")
	# 		plt.ylabel("Energy consumption (J)")
	# 		plt.xticks(rotation=90)
	# 		plt.tight_layout()
	# 		plt.savefig(Path("./plots", f"{project_name}.png"), dpi=300)
	# 		plt.close()

	print("done")
