import shutil
import csv
import os
import sys

from pathlib import Path
from time import sleep
from pyEnergiBridge.api import EnergiBridgeRunner

from utils import run_command_in_external_project

def extract_joularjx_csv_files(project_dir, prefix=0):
	prefix = str(prefix)
	# Move joularjx files to results folder
	for csv_file in Path(project_dir).rglob("*.csv"):
		if "joularJX" in csv_file.name:
			csv_name = "-".join([prefix, project_dir.stem] + csv_file.name.split("-")[2:])
			shutil.move(csv_file.resolve(), Path("results", csv_name))


def run_experiments_joularjx(project, project_path, amount_of_tests=30):
		for i in range(amount_of_tests):
			# print("Sleeping for 30 seconds to allow the system to stabilize...")
			# sleep(30)
			print(f"{project} experiment run {i+1}/{amount_of_tests}")
			log_path = Path(os.getcwd(), "logs", f"{i}_{project}_run.log")
			run_command_in_external_project("mvn test", project_path, log_path)
			extract_joularjx_csv_files(project_path, i)


def run_experiments_energibrdige(project, project_path, amount_of_tests=30):
	runner = EnergiBridgeRunner()
	methods = {}
	with open(Path(project_path, "config.properties"), "r") as joular_config:
		for line in joular_config:
			if line.startswith("filter-method-names="):
				for method in line.split("=")[1].strip().split(","):
					methods[method] = None
				break
	for i in range(amount_of_tests):
		# print("Sleeping for 30 seconds to allow the system to stabilize...")
		# sleep(30)
		print(f"{project} experiment run {i+1}/{amount_of_tests}")
		for method in methods.keys():
			runner.start()
			sleep(1)
			print(f"Running method {method}")
			run_command_in_external_project(f"mvn -Dtest={method.split('.')[-2]}#{method.split('.')[-1]} test", project_path)
			sleep(1)
			energy, duration = runner.stop()
			print(f"Energy: {energy}, Duration: {duration}")
			methods[method] = energy
		
		# Write the results to a CSV file
		with open(Path("results", f"{i}-{project}-filtered-methods-energy.csv"), "w") as csv_file:
			writer = csv.writer(csv_file)
			for method, energy in methods.items():
				writer.writerow([method, energy])

if __name__ == "__main__":
	joularjx_dir = Path(os.getcwd(), "joularjx")
	joularjx_path = Path(joularjx_dir, "target", list(filter(lambda x: x.endswith(".jar") and "joularjx" in x, os.listdir(Path(joularjx_dir, "target"))))[0])
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

			print(f"Running experiments for {project}")
			project_path = Path(testing_repositories_dir, project)
			if "--joularjx" in sys.argv:
				run_experiments_joularjx(project, project_path)
			elif "--energi-bridge" in sys.argv:
				run_experiments_energibrdige(project, project_path)
			else:
				print("Please specify --joularjx or --energi-bridge to run the experiments.")
