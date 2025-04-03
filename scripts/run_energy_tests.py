from subprocess import Popen, run
from pathlib import Path
import os
import xml.etree.ElementTree as ET
import shutil
import csv
import sys
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import shapiro
from decimal import Decimal

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
	"https://github.com/12joaquin/TestProject.git",
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
	test_methods = set()
	for java_tests in Path(project_dir).rglob("*.java"):
		relative_path = str(java_tests).replace(str(Path()), "")
		if "test" in relative_path.lower():
			with open(java_tests, "r") as tests_file:
				looking_for_method = False
				package_name = None
				for line in tests_file.readlines():
					if line.startswith("package"):
						package_name = line.split(" ")[1][:-2]
						test_packages.add(f"{package_name}.{Path(java_tests).stem}")
					if (line.strip().startswith("@ParameterizedTest") or line.strip().startswith("@Test")) and not looking_for_method:
						looking_for_method = True
					elif looking_for_method:
						if "(" in line and ")" in line and line.strip().endswith("{"):
							method_name = line.split("(")[0].split(" ")[-1].strip()
							if package_name is not None:
								test_methods.add(f"{package_name}.{java_tests.stem}.{method_name}")
							else:
								test_methods.add(f"{java_tests.stem}.{method_name}")
							looking_for_method = False
	print(f"Found {len(test_methods)} tests in {project_dir.stem}")
	with open(Path("config.properties"), "r") as joular_config:
		data = joular_config.read()
	data = data.replace("REPLACE-WITH-JOULAR-TEST-PACKAGES", ",".join(test_methods))
	with open(Path("config.properties"), "w") as joular_config:
		joular_config.write(data)
	
	# Copy this config file to any place where there is a pom.xml file
	config_path = Path("config.properties")
	for pom_xml in Path().rglob("pom.xml"):
		new_path = Path(pom_xml.parent, "config.properties")
		if not new_path.exists():
			shutil.copy(config_path, new_path)

def mvn_add_joularjx(project_dir, joularjx_path):
	# Add JoularJX config file to project
	shutil.copy(Path("config.properties"), Path(project_dir, "config.properties"))

	old_path = os.getcwd()
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

	add_test_packages_to_joularjx(project_dir)
	os.chdir(old_path)

def reject_outliers(data, m=2.):
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d / (mdev if mdev else 1.)
    return data[s < m]

def extract_joularjx_csv_files(project_dir, prefix=0):
	prefix = str(prefix)
	# Move joularjx files to results folder
	for csv_file in Path(project_dir).rglob("*.csv"):
		if "joularJX" in csv_file.name:
			csv_name = "-".join([prefix, project_dir.stem] + csv_file.name.split("-")[2:])
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

# Run tests multiple times (experiment phase)
def run_experiment(total_runs = 5):
	total_runs = 5
	total_repos = len(repos)
	for i in range(total_runs):
		print(f"Performing experiment run {i+1} of {total_runs}")
		for j, repo in enumerate(repos):
			project = Path(repo).stem
			project_dir = Path(os.getcwd(), "external_projects", project)
			log_path = Path(os.getcwd(), "logs", f"{i}_{project}_run.log")
			print(f"Running {project} ({j+1}/{total_repos})")
			run_command_in_external_project("mvn test", project_dir, log_path)
			extract_joularjx_csv_files(project_dir, i)

def get_project_runs_data():
	projects = {}
	for repo in repos:
		projects[Path(repo).stem] = []
	for csv_file in Path("./results").glob("*.csv"):
		for project in projects.keys():
			if project in csv_file.name and "filtered-methods-energy" in csv_file.name and not csv_file.name.startswith("build"):
				projects[project].append(csv_file)

	projects_energy_consumption = {}
	for project, csv_files in projects.items():
		if len(csv_files) > 0:
			print(f"Parsing CSVs for {project}")
		else:
			print(f"No CSV files found for {project}, skipping...")
			continue
		tests_energy_consumption = {}
		for csv_file in csv_files:
			with open(csv_file, "r") as file:
				csv_data = csv.reader(file)
				for line in csv_data:
					test_name = ".".join(line[0].split(".")[-2:]).split("$")[0]
					energy_consumption = float(line[1])
					if "test" not in line[0].lower() or "lambda" in test_name:
						continue
					if test_name not in tests_energy_consumption:
						tests_energy_consumption[test_name] = []
					tests_energy_consumption[test_name].append(energy_consumption)
		if len(tests_energy_consumption.keys()) == 0:
			print(f"No tests found for {project}, skipping...")
			continue
		else:
			for test_name, energy_consumptions in tests_energy_consumption.items():
				no_outliers = reject_outliers(np.array(energy_consumptions))
				if len(no_outliers) >= 3:
					if project not in projects_energy_consumption:
						projects_energy_consumption[project] = {}
					projects_energy_consumption[project][test_name] = no_outliers

	return projects_energy_consumption

# Generate plots from csv files
# max_tests specifies the top X energy consuming tests to plot
# data can be used to pass the data for generating plots (so it doesn't have to be re-read from disk)
def generate_plots(max_tests=15, data=None, numbers_instead_of_names=False):
	print("Generating plots")
	if data is None:
		data = get_project_runs_data()

	for project, tests_energy_consumption in data.items():
		print(f"Generating plot for {project}")
		means = []
		for test, energy_consumptions in tests_energy_consumption.items():
			means.append((test, np.mean(energy_consumptions)))
		means = sorted(means, key=lambda x: x[1], reverse=True)
		if max_tests is not None and max_tests > 0:
			means = means[:max_tests]
		boxes = [tests_energy_consumption[tup[0]] for tup in means]
		if numbers_instead_of_names:
			labels = list(range(1, len(boxes) + 1))
		else:
			labels = [tup[0].split(".")[-1] for tup in means]

		fix, ax = plt.subplots()
		bplot = plt.boxplot(boxes, labels=labels)
		plt.title(f"Test energy consumption of {project}")
		plt.xlabel("Test name")
		plt.ylabel("Energy consumption (J)")
		if not numbers_instead_of_names:
			plt.xticks(rotation=90, fontsize=6)
		plt.tight_layout()
		plt.savefig(Path("./plots", f"{project}.png"), dpi=300)
		plt.close()

# Generate the latex appendix file with all plots and tables in it
def generate_latex_appendix(max_tests=15, data=None):
	print("Generating LaTeX appendix...")
	if data is None:
		data = get_project_runs_data()
	
	appendix = """\\subsection{Results from test runs}\\label{app:A}
In this appendix we provide the boxplots showing the energy consumption across multiple test runs for all projects. We also provide the $p$-value for the Shapiro-Wilk test for normality.\n\n"""

	for project, energy_data in data.items():
		stats = []
		for test, energy_consumptions in energy_data.items():
			if len(energy_consumptions) < 3:
				continue
			d = {
				"name": test,
				"mean": np.mean(energy_consumptions),
				"stddev": round(np.std(energy_consumptions), 3),
				"shapwilks": shapiro(energy_consumptions)
			}
			stats.append(d)
		stats = sorted(stats, key=lambda x: x["mean"], reverse=True)
		appendix += f"\\begin{{figure*}}[h!]\n\\centering\n\\includegraphics[width=0.5\\linewidth]{{plots/{project}.png}}\n\\caption{{Energy consumption for {project} test suite. Corresponding tests can be found in table \\ref{{tab:{project}}}}}\n\\label{{fig:{project}}}\n\end{{figure*}}\n\n"
		appendix += f"\\begin{{table*}}[h!]\n\\centering\n\\begin{{tabular}}{{|c|l|c|c|c|}}\n\\hline\nIndex & Test name & Mean J & Std. dev. & $p$-value \\\\\n\hline\n"
		for i, test in enumerate(stats[:max_tests]):
			if test["shapwilks"].pvalue > 0.05:
				pvalue =  "{\\color{red}%.2e}" % Decimal(test["shapwilks"].pvalue)
			else:
				pvalue =  "%.2e" % Decimal(test["shapwilks"].pvalue)
			appendix += "{0} & {1} & ${2}$ & ${3}$ & ${4}$ \\\\\n\hline\n".format(i + 1, test["name"], round(test["mean"], 4), test["stddev"], pvalue)
		# appendix = appendix[:-10]
		appendix += f"\\end{{tabular}}\n\\caption{{Detailed energy usage for {project}\\label{{tab:{project}}}}}\n\\end{{table*}}\n\n"
	
	with open("appendix-runs.tex", "w") as f:
		f.write(appendix.replace("_", "\\_"))

if __name__ == "__main__":
	# Create directories if they don't exist
	os.chdir(Path(__file__).parents[1].resolve())
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

			if "--skip-tests" in sys.argv or "--skip-build" in sys.argv:
				print(f"Skipping build for {project}...")
			else:
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
	
	if "--skip-tests" in sys.argv or "--skip-experiment" in sys.argv:
		print("Skipping experiment...")
	else:
		# Defaults to 5 runs
		run_experiment()

	# Generate plots
	if "--skip-plots" not in sys.argv:
		energy_data = get_project_runs_data()
		generate_plots(data=energy_data, letters_instead_of_names=True)
		generate_latex_appendix(data=energy_data)

	print("done")
