

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CupCarbon Scenario Generator
============================

Generates CupCarbon simulation scenarios with a star topology:
1 Gateway (base station) + N Sensors evenly distributed on a circle around it.

Conforms to CupCarbon Klaines 8.2 project structure and file format.

Usage:
    python simulation/cupcarbon/generate_scenarios.py --n-list 5 10 25 50
"""

import argparse
import math
import os
import shutil
import sys
import time
from typing import Dict, List, Optional, Tuple

# Earth radius in meters used by CupCarbon (utilities.MapCalc)
EARTH_RADIUS_M = 6378137.0

# Default CupCarbon project directory subfolders
CUPCARBON_SUBDIRS = [
    "agents",
    "config",
    os.path.join("config", "nodes"),
    os.path.join("config", "sensor_radios"),
    "gps",
    "logs",
    "natevents",
    "network",
    "results",
    "scripts",
    "tmp",
    "xbee",
]

# Default parameters when template files/directories are empty
DEFAULT_CENTER_LAT = 25.308037979296657
DEFAULT_CENTER_LON = 55.44253706932068
DEFAULT_RADIO_RANGE = 100.0  # meters (CupCarbon ZigBee standard default)
DEFAULT_PLACEMENT_RATIO = 0.5  # circle radius = 50% of radio range (50m)


def read_cup_file(cup_path: str) -> Dict[str, str]:
    """Parse a CupCarbon .cup project file into key-value pairs."""
    params = {}
    if not os.path.isfile(cup_path):
        return params

    with open(cup_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ":" in line:
                k, v = line.split(":", 1)
                params[k.strip()] = v.strip()
    return params


def inspect_template_radio_range(template_dir: str) -> Optional[float]:
    """
    Attempt to read radio range from any existing node radio files in the template.
    Returns None if no node radio files exist.
    """
    radios_dir = os.path.join(template_dir, "config", "sensor_radios")
    if os.path.isdir(radios_dir):
        for fname in os.listdir(radios_dir):
            fpath = os.path.join(radios_dir, fname)
            if os.path.isfile(fpath) and not fname.startswith("."):
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("radio_radius:"):
                            try:
                                return float(line.split(":", 1)[1].strip())
                            except ValueError:
                                pass
    return None


def inspect_template_gateway_pos(template_dir: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Attempt to read gateway position from template node files.
    Returns (lat, lon) or (None, None) if not defined in node files.
    """
    nodes_dir = os.path.join(template_dir, "config", "nodes")
    if os.path.isdir(nodes_dir):
        # Look for basestation or node 0
        candidates = ["basestation_0", "basestation_1", "sensor_0", "sensor_1"]
        for fname in os.listdir(nodes_dir):
            if fname.startswith("basestation") or fname in candidates:
                fpath = os.path.join(nodes_dir, fname)
                lat, lon = None, None
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("device_latitude:"):
                            lat = float(line.split(":", 1)[1].strip())
                        elif line.startswith("device_longitude:"):
                            lon = float(line.split(":", 1)[1].strip())
                if lat is not None and lon is not None:
                    return lat, lon
    return None, None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance in meters between two points.
    Matches utilities.MapCalc.distance in CupCarbon.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1) / 2.0
    dlambda = math.radians(lon2 - lon1) / 2.0

    a = (math.sin(dphi) ** 2) + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_M * c


def compute_star_sensor_coordinates(
    center_lat: float, center_lon: float, n_nodes: int, radius_m: float
) -> List[Tuple[float, float]]:
    """
    Computes coordinates for N sensors placed evenly on a circle around (center_lat, center_lon).
    """
    coords = []
    lat_rad = math.radians(center_lat)
    cos_lat = math.cos(lat_rad)

    for i in range(n_nodes):
        theta = (2.0 * math.pi * i) / n_nodes
        dx = radius_m * math.cos(theta)
        dy = radius_m * math.sin(theta)

        dlat = (dy / EARTH_RADIUS_M) * (180.0 / math.pi)
        dlon = (dx / (EARTH_RADIUS_M * cos_lat)) * (180.0 / math.pi)

        s_lat = center_lat + dlat
        s_lon = center_lon + dlon
        coords.append((s_lat, s_lon))

    return coords


def safe_rmtree(path: str, max_retries: int = 5, delay: float = 0.2) -> None:
    """Robustly remove a directory tree on Windows, handling file locks and read-only attributes."""
    if not os.path.exists(path):
        return

    def on_exc(func, fpath, exc_info):
        try:
            os.chmod(fpath, 0o777)
        except Exception:
            pass
        try:
            func(fpath)
        except Exception:
            pass

    for attempt in range(max_retries):
        try:
            if sys.version_info >= (3, 12):
                shutil.rmtree(path, onexc=on_exc)
            else:
                shutil.rmtree(path, onerror=on_exc)
            return
        except OSError:
            if attempt == max_retries - 1:
                # Fallback: traverse and attempt removing individual elements
                for root, dirs, files in os.walk(path, topdown=False):
                    for f in files:
                        try:
                            fp = os.path.join(root, f)
                            os.chmod(fp, 0o777)
                            os.remove(fp)
                        except Exception:
                            pass
                    for d in dirs:
                        try:
                            os.rmdir(os.path.join(root, d))
                        except Exception:
                            pass
                try:
                    os.rmdir(path)
                except Exception:
                    pass
                return
            time.sleep(delay)


def generate_scenario(
    template_dir: str,
    output_dir: str,
    n_nodes: int,
    gateway_lat: float,
    gateway_lon: float,
    radio_range: float,
) -> str:
    """
    Generates a complete CupCarbon scenario project folder: scenarios/star_<n>/
    """
    project_name = f"star_{n_nodes}"
    project_path = os.path.join(output_dir, project_name)

    # 1. Idempotent cleanup: overwrite project directory
    if os.path.exists(project_path):
        safe_rmtree(project_path)

    # 2. Create directory structure
    for subdir in CUPCARBON_SUBDIRS:
        os.makedirs(os.path.join(project_path, subdir), exist_ok=True)
    open(os.path.join(project_path, "logs", "log.txt"), "a", encoding="utf-8").close()
    open(os.path.join(project_path, "results", "wisen_simulation.csv"), "a", encoding="utf-8").close()

    # 3. Create project file <project_name>.cup
    template_cup_path = os.path.join(template_dir, "template.cup")
    cup_params = read_cup_file(template_cup_path)

    # Replicate template settings with updated project name
    cup_lines = [
        "CupCarbon v. Klaines 8.2",
        "----------------",
        f"name:{project_name}",
        f"zoom:{cup_params.get('zoom', '2')}",
        f"centerposition_la:{gateway_lat}",
        f"centerposition_lo:{gateway_lon}",
        f"map:{cup_params.get('map', '1')}",
        f"display_details:{cup_params.get('display_details', 'true')}",
        f"draw_radio_links:{cup_params.get('draw_radio_links', 'true')}",
        f"draw_sensor_arrows:{cup_params.get('draw_sensor_arrows', 'true')}",
        f"radio_links_color:{cup_params.get('radio_links_color', '2')}",
        f"draw_marker_arrows:{cup_params.get('draw_marker_arrows', 'false')}",
        f"display_rl_distance:{cup_params.get('display_rl_distance', 'false')}",
        f"propagation:{cup_params.get('propagation', 'false')}",
        f"display_marker_distance:{cup_params.get('display_marker_distance', 'false')}",
        f"display_radio_messages:{cup_params.get('display_radio_messages', 'true')}",
        f"draw_script_file_name:{cup_params.get('draw_script_file_name', 'true')}",
        f"display_print_messages:{cup_params.get('display_print_messages', 'true')}",
        f"display_all_routes:{cup_params.get('display_all_routes', 'false')}",
        "",
    ]
    with open(os.path.join(project_path, f"{project_name}.cup"), "w", encoding="utf-8") as f:
        f.write("\n".join(cup_lines))

    # 4. Copy or create config/session.cfg
    template_session = os.path.join(template_dir, "config", "session.cfg")
    session_content = "sessionecd0ccdab865\n"
    if os.path.isfile(template_session):
        with open(template_session, "r", encoding="utf-8") as f:
            session_content = f.read()
    with open(os.path.join(project_path, "config", "session.cfg"), "w", encoding="utf-8") as f:
        f.write(session_content)

    # 5. Create scripts (both SenScript .csc and Python .py to support all CupCarbon modes)
    sensor_csc = (
        "// CupCarbon SenScript for Sensor Node\n"
        "// Sends one message to the gateway every 1 simulated second\n"
        "loop\n"
        "send \"DATA\" 0 1\n"
        "delay 1000\n"
    )
    gateway_csc = (
        "// CupCarbon SenScript for Gateway\n"
        "atmy 1\n"
        "loop\n"
        "receive x\n"
        "print x\n"
        "delay 1000\n"
    )
    sensor_py = (
        "# CupCarbon IoT Python Script for Sensor Node\n"
        "from cup_functions import *\n\n"
        "while True:\n"
        "    cup_send(\"DATA\", \"0 1\")\n"
        "    cup_wait(1)\n"
    )
    gateway_py = (
        "# CupCarbon IoT Python Script for Gateway\n"
        "from cup_functions import *\n\n"
        "while True:\n"
        "    msg = cup_read()\n"
        "    cup_print(msg)\n"
    )

    scripts_dir = os.path.join(project_path, "scripts")
    with open(os.path.join(scripts_dir, "sensor.csc"), "w", encoding="utf-8") as f:
        f.write(sensor_csc)
    with open(os.path.join(scripts_dir, "gateway.csc"), "w", encoding="utf-8") as f:
        f.write(gateway_csc)
    with open(os.path.join(scripts_dir, "sensor.py"), "w", encoding="utf-8") as f:
        f.write(sensor_py)
    with open(os.path.join(scripts_dir, "gateway.py"), "w", encoding="utf-8") as f:
        f.write(gateway_py)

    # 6. Create Gateway Node (BaseStation id 0, name G/SINK_0)
    # File: config/nodes/basestation_0
    nodes_dir = os.path.join(project_path, "config", "nodes")
    radios_dir = os.path.join(project_path, "config", "sensor_radios")

    gw_node_content = (
        "List of parameters\n"
        "------------------------------------------\n"
        "device_type:4\n"
        "device_id:0\n"
        f"device_longitude:{gateway_lon}\n"
        f"device_latitude:{gateway_lat}\n"
        "device_elevation:0.0\n"
        "device_radius:0.0\n"
        "device_hide:0\n"
        "device_draw_battery:false\n"
        "device_sensor_unit_radius:0.0\n"
        "device_script_file_name:gateway.csc\n"
    )
    with open(os.path.join(nodes_dir, "basestation_0"), "w", encoding="utf-8") as f:
        f.write(gw_node_content)

    gw_radio_content = (
        "List of radio Modules for the Sensor0\n"
        "------------------------------------------\n"
        "current_radio_name:radio1\n"
        "radio_standard:ZigBee\n"
        "radio_my:1\n"
        "radio_channel:0\n"
        "radio_network_id:13108\n"
        f"radio_radius:{radio_range}\n"
        "radio_etx:5.92E-5\n"
        "radio_erx:2.86E-5\n"
        "radio_esleep:1.0E-7\n"
        "radio_elisten:1.0E-6\n"
        "radio_data_rate:250000\n"
        "conso_tx_model:Classical (Tx)\n"
        "conso_rx_model:Classical (Rx)\n"
    )
    with open(os.path.join(radios_dir, "basestation_0"), "w", encoding="utf-8") as f:
        f.write(gw_radio_content)

    # 7. Create Sensor Nodes S1..SN (IDs 1..N)
    circle_radius_m = radio_range * DEFAULT_PLACEMENT_RATIO
    sensor_positions = compute_star_sensor_coordinates(
        gateway_lat, gateway_lon, n_nodes, circle_radius_m
    )

    for i, (s_lat, s_lon) in enumerate(sensor_positions, start=1):
        s_id = i
        sensor_node_content = (
            "List of parameters\n"
            "------------------------------------------\n"
            "device_type:1\n"
            f"device_id:{s_id}\n"
            f"device_longitude:{s_lon}\n"
            f"device_latitude:{s_lat}\n"
            "device_elevation:0.0\n"
            "device_radius:10.0\n"
            "device_hide:0\n"
            "device_pic:0\n"
            "device_draw_battery:false\n"
            "device_sensor_unit_radius:10.0\n"
            "device_script_file_name:sensor.csc\n"
        )
        with open(os.path.join(nodes_dir, f"sensor_{s_id}"), "w", encoding="utf-8") as f:
            f.write(sensor_node_content)

        sensor_radio_content = (
            f"List of radio Modules for the Sensor{s_id}\n"
            "------------------------------------------\n"
            "current_radio_name:radio1\n"
            "radio_standard:ZigBee\n"
            "radio_my:0\n"
            "radio_channel:0\n"
            "radio_network_id:13108\n"
            f"radio_radius:{radio_range}\n"
            "radio_etx:5.92E-5\n"
            "radio_erx:2.86E-5\n"
            "radio_esleep:1.0E-7\n"
            "radio_elisten:1.0E-6\n"
            "radio_data_rate:250000\n"
            "conso_tx_model:Classical (Tx)\n"
            "conso_rx_model:Classical (Rx)\n"
        )
        with open(os.path.join(radios_dir, f"sensor_{s_id}"), "w", encoding="utf-8") as f:
            f.write(sensor_radio_content)

    return project_path


def validate_scenario(project_path: str, n_nodes: int, max_radio_range: float) -> Tuple[bool, List[str]]:
    """
    Validates the generated CupCarbon scenario:
    - Node count == N + 1
    - All IDs unique
    - All file references between nodes, radios, and scripts resolve
    - All sensors are within radio range of gateway
    """
    errors = []
    p_name = os.path.basename(project_path)

    # 1. Project file check
    cup_file = os.path.join(project_path, f"{p_name}.cup")
    if not os.path.isfile(cup_file):
        errors.append(f"Missing project file: {p_name}.cup")

    # 2. Subdirectories check
    for subdir in CUPCARBON_SUBDIRS:
        sd_path = os.path.join(project_path, subdir)
        if not os.path.isdir(sd_path):
            errors.append(f"Missing subdirectory: {subdir}")

    # 3. Node files check
    nodes_dir = os.path.join(project_path, "config", "nodes")
    radios_dir = os.path.join(project_path, "config", "sensor_radios")
    scripts_dir = os.path.join(project_path, "scripts")

    node_files = [f for f in os.listdir(nodes_dir) if not f.startswith(".")]
    expected_count = n_nodes + 1
    if len(node_files) != expected_count:
        errors.append(
            f"Node count mismatch: expected {expected_count} (1 gateway + {n_nodes} sensors), found {len(node_files)}"
        )

    # 4. Check IDs, positions, radio files, and script resolution
    node_ids = set()
    node_positions = {}
    gateway_id = None

    for nf in node_files:
        nf_path = os.path.join(nodes_dir, nf)
        node_id = None
        device_type = None
        script_name = None
        lat, lon = None, None

        with open(nf_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("device_id:"):
                    try:
                        node_id = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        errors.append(f"Invalid integer device_id in {nf}: {line}")
                elif line.startswith("device_type:"):
                    device_type = line.split(":", 1)[1].strip()
                elif line.startswith("device_script_file_name:"):
                    script_name = line.split(":", 1)[1].strip()
                elif line.startswith("device_latitude:"):
                    lat = float(line.split(":", 1)[1].strip())
                elif line.startswith("device_longitude:"):
                    lon = float(line.split(":", 1)[1].strip())

        if node_id is None:
            errors.append(f"No device_id found in {nf}")
        elif node_id in node_ids:
            errors.append(f"Duplicate node ID found: {node_id} in {nf}")
        else:
            node_ids.add(node_id)

        if device_type == "4" or nf.startswith("basestation"):
            gateway_id = node_id

        if lat is not None and lon is not None:
            node_positions[node_id] = (lat, lon)

        # Check corresponding radio file exists
        rf_path = os.path.join(radios_dir, nf)
        if not os.path.isfile(rf_path):
            errors.append(f"Missing radio file for node {nf}: {rf_path}")
        else:
            # Check radio file content
            with open(rf_path, "r", encoding="utf-8") as f:
                r_content = f.read()
                if "radio_radius:" not in r_content:
                    errors.append(f"Radio file {nf} missing radio_radius parameter")

        # Check script reference resolves
        if script_name:
            script_path = os.path.join(scripts_dir, script_name)
            if not os.path.isfile(script_path):
                errors.append(f"Script reference in {nf} ({script_name}) does not exist in {scripts_dir}")

    # 5. Validate Gateway existence
    if gateway_id is None:
        errors.append("No gateway node (base station) found")
    elif gateway_id not in node_positions:
        errors.append(f"Gateway {gateway_id} has no valid coordinates")
    else:
        gw_lat, gw_lon = node_positions[gateway_id]
        # Check all sensors are within radio range of gateway
        for s_id, (s_lat, s_lon) in node_positions.items():
            if s_id != gateway_id:
                dist = haversine_distance(gw_lat, gw_lon, s_lat, s_lon)
                if dist > max_radio_range:
                    errors.append(
                        f"Sensor node {s_id} is at distance {dist:.2f}m, outside gateway radio range ({max_radio_range:.2f}m)"
                    )

    passed = len(errors) == 0
    return passed, errors


def main():
    parser = argparse.ArgumentParser(
        description="Generate CupCarbon star topology scenarios cloning the template format."
    )
    parser.add_argument(
        "--n-list",
        nargs="+",
        type=int,
        default=[5, 10, 25, 50],
        help="List of sensor counts for scenarios (default: 5 10 25 50)",
    )
    parser.add_argument(
        "--template",
        type=str,
        default=os.path.join("simulation", "cupcarbon", "template"),
        help="Path to CupCarbon template project folder",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join("simulation", "cupcarbon", "scenarios"),
        help="Output base directory for generated scenarios",
    )
    args = parser.parse_args()

    # Workspace directory resolution
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    template_dir = os.path.abspath(os.path.join(base_dir, args.template))
    output_base_dir = os.path.abspath(os.path.join(base_dir, args.output_dir))

    if not os.path.isdir(template_dir):
        # Fallback to local path if running from root
        template_dir = os.path.abspath(args.template)
        output_base_dir = os.path.abspath(args.output_dir)

    print("=" * 70)
    print("CupCarbon Scenario Generator")
    print(f"Template directory : {template_dir}")
    print(f"Output directory   : {output_base_dir}")
    print(f"Scenarios (N-list) : {args.n_list}")
    print("=" * 70)

    # Inspect template
    template_cup = read_cup_file(os.path.join(template_dir, "template.cup"))
    gw_lat, gw_lon = inspect_template_gateway_pos(template_dir)
    if gw_lat is None or gw_lon is None:
        try:
            gw_lat = float(template_cup.get("centerposition_la", DEFAULT_CENTER_LAT))
            gw_lon = float(template_cup.get("centerposition_lo", DEFAULT_CENTER_LON))
        except (ValueError, TypeError):
            gw_lat = DEFAULT_CENTER_LAT
            gw_lon = DEFAULT_CENTER_LON

    radio_range = inspect_template_radio_range(template_dir)
    if radio_range is None:
        radio_range = DEFAULT_RADIO_RANGE

    circle_radius = radio_range * DEFAULT_PLACEMENT_RATIO
    print(f"Gateway Position   : ({gw_lat}, {gw_lon})")
    print(f"Gateway Radio Range: {radio_range:.1f} m")
    print(f"Sensor Circle Radius: {circle_radius:.1f} m (all nodes within radio range)")
    print("-" * 70)

    os.makedirs(output_base_dir, exist_ok=True)

    # Generate each scenario
    results = {}
    for n in args.n_list:
        print(f"\n[*] Generating scenario star_{n} (1 gateway + {n} sensors = {n + 1} nodes)...")
        proj_dir = generate_scenario(
            template_dir=template_dir,
            output_dir=output_base_dir,
            n_nodes=n,
            gateway_lat=gw_lat,
            gateway_lon=gw_lon,
            radio_range=radio_range,
        )
        passed, errors = validate_scenario(proj_dir, n, radio_range)
        results[n] = (passed, errors, proj_dir)

    # Validation Report
    print("\n" + "=" * 70)
    print("VALIDATION REPORT")
    print("=" * 70)
    all_passed = True
    for n, (passed, errors, ppath) in results.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"Scenario star_{n:<2}: [{status}] - {ppath}")
        print(f"  - Node Count     : {n + 1} (1 Gateway + {n} Sensors)")
        print(f"  - Unique IDs     : 0 (Gateway), 1..{n} (Sensors)")
        print(f"  - File References: All node radios & scripts verified")
        if not passed:
            for err in errors:
                print(f"    [!] Error: {err}")
    print("=" * 70)
    print(f"OVERALL STATUS: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("=" * 70)

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
