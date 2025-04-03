import os
import subprocess

from subprocess import run

def run_command_in_external_project(command, project_dir, log_path=None):
	old_dir = os.getcwd()
	os.chdir(project_dir)
	if log_path is None:
		r = run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
	else:
		with open(log_path, "w") as outfile:
			r = run(command, shell=True, stdout=outfile, stderr=outfile)
	os.chdir(old_dir)