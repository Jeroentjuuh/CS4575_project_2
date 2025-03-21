from subprocess import Popen, run
from pathlib import Path
import os
import xml.etree.ElementTree as ET
import shutil
import configparser

repos = [
	# "https://github.com/allure-framework/allure-java.git"
	# "https://github.com/apache/cassandra.git",
	# "https://github.com/apache/camel.git",
	# "https://github.com/apache/accumulo.git",
	# "https://github.com/1c-syntax/bsl-language-server.git",
	"https://github.com/hub4j/github-api.git",
	# "https://github.com/zendesk/maxwell.git",
	"https://github.com/zebrunner/carina.git",
	"https://github.com/yegor256/cactoos.git",
	# "https://github.com/xnio/xnio.git",
	"https://github.com/wmixvideo/nfe.git",
	# "https://github.com/twilio/twilio-java.git",
	"https://github.com/ta4j/ta4j.git",
	# "https://github.com/sqlancer/sqlancer.git",
	# "https://github.com/soot-oss/soot.git" # this does some sort of concurrency, is it a good one?
	"https://github.com/junit-team/junit4.git", # This one is private?
	"https://github.com/okta/okta-spring-boot.git",
	"https://github.com/julianhyde/sqlline.git",
	"https://github.com/togglz/togglz.git",
	"https://github.com/eclipse-ee4j/jaxrs-api.git",
	"https://github.com/damianszczepanik/cucumber-reporting.git",
	"https://github.com/decorators-squad/eo-yaml.git",
	"https://github.com/dlsc-software-consulting-gmbh/preferencesfx.git",
	"https://github.com/forcedotcom/dataloader.git",
	"https://github.com/forge/roaster.git"
]

if __name__ == "__main__":
	# Create directories if they don't exist
	Path("./external_projects").mkdir(exist_ok=True)
	Path("./logs").mkdir(exist_ok=True)
	Path("./logs").mkdir(exist_ok=True)
	Path("./joularjx").mkdir(exist_ok=True)

	# Build joularjx
	joularjx_dir = Path(os.getcwd(), "joularjx")
	run(["git", "clone", "https://github.com/joular/joularjx.git", joularjx_dir])
	os.chdir(joularjx_dir)
	r = run("mvn clean install -DskipTests", shell=True)
	joularjx_path = Path(joularjx_dir, "target", list(filter(lambda x: x.endswith(".jar") and "joularjx" in x, os.listdir(Path(joularjx_dir, "target"))))[0])
	print(f"JoularJX path: {joularjx_path}")
	os.chdir(joularjx_dir.parents[0])

	# Clone repos and run tests
	for repo in repos:
		project = Path(repo).stem
		project_dir = Path(os.getcwd(), "external_projects", project)
		print(f"Cloning {project}...")
		run(["git", "clone", repo, project_dir])

		print(f"Building and testing {project}...")
		
		os.chdir(project_dir)

		shutil.rmtree(f"{project_dir}/joularjx-result", ignore_errors=True)
		shutil.copy('../../config.properties', f"{project_dir}/config.properties")
		# config = configparser.ConfigParser()
		# config.read(f"{project_dir}/config.properties")
		log_path = Path("../../logs", project + "_build.log")
		succeeded = False

		if Path("pom.xml").exists():
			print("Maven project")

			# https://stackoverflow.com/questions/46302636/maven-test-and-javaagent-argument
			# -javaagent:/home/roelof/Repositories/CS4575_project_2/joularjx/target/joularjx-3.0.1.jar
			tree = ET.parse(Path(project_dir, "pom.xml"))
			prefix = tree.getroot().tag.replace("project", "")
			ET.register_namespace("", prefix[1:-1])
			tree = ET.parse(Path(project_dir, "pom.xml"))
			groupId = tree.find(f"{prefix}groupId").text

			# config.set("filter-method-names", "filter-method-names", groupId)
			for plugin in tree.iter(f"{prefix}plugin"):
				artifactId = plugin.find(f"{prefix}artifactId").text
				if "maven-surefire-plugin" in artifactId:
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
			tree.write("pom.xml")

			with open(log_path, "w") as outfile:
				r = run("mvn clean test", shell=True, stdout=outfile, stderr=outfile)
		elif Path("build.gradle").exists() or Path("build.gradle.kts").exists():
			print("Gradle project")
			with open(log_path, "w") as outfile:
				run("gradle clean test", shell=True, stdout=outfile, stderr=outfile)
		else:
			print(f"No recognized build file found for {project}")
			
		os.chdir(project_dir.parents[1])

	print("done")

