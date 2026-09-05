# Q4 Install-from-wheel CI Contract

Extend the main-branch CI workflow with an `install-from-wheel` job. The job
builds a wheel, installs it into a temporary isolated environment, sets
`COMMONS_HOME` under `$RUNNER_TEMP/commons-ci`, and runs
`python -m aafp_commons world`. It must use no secrets, publishing, or
simulation homes.
