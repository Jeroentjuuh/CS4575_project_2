# CS4575_project_2

Run the experiment with `python3 scripts/run_energy_tests.py`

Commandline options:

`--skip-joularjx-build`: skips building of JoularJX

`--skip-tests`: skips building of projects and the experiment

`--skip-build`: skips building of projects, but not the experiment

`--skip-experiment`: skips the experiment, but not building of projects

`--skip-plots`: skips generation of plots

For example: if you have already run the script once, you could run `python3 scripts/run_energy_tests.py --skip-joularjx-build --skip-build` to run only the experiment again and not rebuild joularjx or the external projects if they have not changed to speed up the process.
