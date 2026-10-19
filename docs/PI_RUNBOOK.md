# Raspberry Pi Benchmark Runbook

1. **Provision Pi**: Clone repo onto the Raspberry Pi and run `bash scripts/setup_pi.sh` to configure system packages and virtual environment.
2. **Execute Benchmarks**: Run `bash scripts/pi_run.sh` on the Pi (sets CPU performance governor, logs temperature, executes 100 iterations).
3. **Collect Archive**: Copy the output tarball to your laptop: `scp pi@<pi-ip>:~/ASCONplus/pi_results_*.tar.gz .`.
4. **Extract Raw Data**: On your laptop, extract into the repo root via `tar -xzf pi_results_*.tar.gz` to populate `results/raw/`.
5. **Analyze Measurements**: Run `python benchmarks/analyze.py` to aggregate statistics and generate comparative figures.
6. **Execute Scalability Simulation**: Run `bash scripts/run_sim.sh` to run the SimPy queue model using the hardware Pi service times.
7. **Rebuild Comprehensive Report**: Run `python scripts/build_report.py` to update `docs/RESULTS.md` with final hardware outcomes.
