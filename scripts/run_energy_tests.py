from subprocess import Popen, run
from pathlib import Path
import os
import xml.etree.ElementTree as ET

repos = [
	# "https://github.com/allure-framework/allure-java.git"
	# "https://github.com/apache/cassandra.git",
	# "https://github.com/apache/camel.git",
	# "https://github.com/apache/accumulo.git",
	"https://github.com/1c-syntax/bsl-language-server.git",
	"https://github.com/hub4j/github-api.git"
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

		log_path = Path("../../logs", project + "_build.log")
		succeeded = False

		if Path("pom.xml").exists():
			print("Maven project")

			# https://stackoverflow.com/questions/46302636/maven-test-and-javaagent-argument
			# -javaagent:/home/roelof/Repositories/CS4575_project_2/joularjx/target/joularjx-3.0.1.jar
			# tree = ET.parse('pom.xml')
			# plugins = tree.findall("plugin")
			# for p in plugins:
			# 	print(p)

			# exit(0)

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

