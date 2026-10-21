# CupCarbon Simulation Instructions & Results Entry

## Option 1: Automated Simulation Execution (Recommended)

Run the automated headless simulation runner to execute the CupCarbon simulation engine across all star topologies ($N \in \{5, 10, 25, 50\}$) and automatically populate `results/raw/cupcarbon_manual.csv`:

```bash
python simulation/cupcarbon/run_simulation.py --sim-time 300
```

To specify a custom CupCarbon directory:
```bash
python simulation/cupcarbon/run_simulation.py --cupcarbon-dir "C:\Users\thanu\OneDrive\Desktop\cupcarbon_windows" --sim-time 300
```

## Option 2: Interactive CupCarbon GUI Execution

1. Launch CupCarbon Klaines (`java -jar cupcarbon.jar`) and open a scenario from `simulation/cupcarbon/scenarios/star_<N>` (N = 5, 10, 25, 50).
2. Click the green "Play" (Simulation) button on the top toolbar to run the discrete-event network simulation for your desired duration.
3. When the simulation pauses or completes, inspect the live simulation telemetry panel and terminal log on screen.
4. Note the total message counters: sensor packets sent (`Sent`), packets delivered to gateway base station (`Received`), and compute `Lost = Sent - Received`.
5. Enter the observed values (`sim_time_s`, `sent`, `received`, `lost`, and `notes`) into the corresponding row in `results/raw/cupcarbon_manual.csv`.

## Rebuilding Evaluation Report

After updating telemetry, regenerate the final report:
```bash
python scripts/build_report.py
```
