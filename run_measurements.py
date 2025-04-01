import shutil
import csv
import os

from pathlib import Path

from utils import run_command_in_external_project

def extract_joularjx_csv_files(project_dir, prefix=0):
	prefix = str(prefix)
	# Move joularjx files to results folder
	for csv_file in Path(project_dir).rglob("*.csv"):
		if "joularJX" in csv_file.name:
			csv_name = "-".join([prefix, project_dir.stem] + csv_file.name.split("-")[2:])
			shutil.move(csv_file.resolve(), Path("results", csv_name))


def run_experiments(project, project_path, amount_of_tests=30):
		for i in range(amount_of_tests):
			print(f"{project} experiment run {i+1}/{amount_of_tests}")
			log_path = Path(os.getcwd(), "logs", f"{i}_{project}_run.log")
			run_command_in_external_project("mvn test", project_path, log_path)
			extract_joularjx_csv_files(project_path, i)
            

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
			run_experiments(project, project_path)