# Raspberry Pi Zero W Benchmark Runbook

1. **Provision Testbed**: Clone the repository onto the Raspberry Pi Zero W and install dependencies: `bash scripts/setup_pi.sh`.
2. **Execute Hardware Benchmarks**: Run `bash scripts/pi_run.sh` directly on the Pi. This configures the performance CPU governor, records SoC temperature and hardware provenance, executes 100 benchmark iterations, and records genuine hardware records (`is_pi=True`) into `results/raw/`.
3. **Transfer Raw Data**: Copy the resulting raw CSV files from the Pi to your workstation: `scp pi@<ip>:~/ASCONplus/results/raw/*_pi*.csv results/raw/`.
4. **Process & Analyze Benchmarks**: Run `python benchmarks/project_pi.py && python benchmarks/analyze.py`. Physical hardware data is automatically detected and prioritized directly without applying slowdown factors.
5. **Run Scalability Simulation**: Execute the discrete-event queueing model using the hardware service times: `bash scripts/run_sim.sh`.
6. **Rebuild Evaluation Report**: Compile the final results into `docs/RESULTS.md`: `python scripts/build_report.py`.
