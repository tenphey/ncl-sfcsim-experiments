#!/usr/bin/env python3
"""
Diagnostic: rerun suspicious seeds individually to understand why they produce anomalies.
Suspicious seeds: 8258, 7486, 8308 (produce very small DHEFT/HEFT but large NHEFT)
"""
import subprocess
import os
import tempfile
import time

def read_props(path):
    props = {}
    if os.path.exists(path):
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    k, v = line.split('=', 1)
                    props[k.strip()] = v.strip()
    return props

def write_props(props, path):
    with open(path, 'w') as f:
        for k, v in props.items():
            f.write(f'{k}={v}\n')

def extract_makespans(output):
    heft = dheft = nheft = None
    for line in output.split('\n'):
        if '[HEFT]makespan' in line and ':' in line:
            try:
                heft = float(line.split(':')[-1].strip())
            except:
                pass
        elif '[DHEFT]makespan' in line and ':' in line:
            try:
                dheft = float(line.split(':')[-1].strip())
            except:
                pass
        elif '[NHEFT]makespan' in line and ':' in line:
            try:
                nheft = float(line.split(':')[-1].strip())
            except:
                pass
    return heft, dheft, nheft

# Configuration
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
base_props_path = os.path.join(os.path.dirname(__file__), 'run_20260526_222616', 'base_properties_snapshot.properties')
diag_dir = os.path.join(os.path.dirname(__file__), 'diagnostic_logs')
os.makedirs(diag_dir, exist_ok=True)

java_cmd_base = [
    'java',
    '-Xmx1000m',
    '-cp', f'{repo_root}/classes:{repo_root}/lib/*',
    'net.gripps.cloud.nfv.main.NFVSchedulingTest'
]

suspicious_seeds = [8258, 7486, 8308]
repo_bws = [60, 120, 240, 480]
timeout = 120

print("=== E11 Diagnostic: Rerunning Suspicious Seeds ===\n")

base = read_props(base_props_path)
base.update({
    'vnf_type_max': '20',
    'sfc_vnf_num': '200',
    'multiple_sfc_num': '1',
    'vnf_image_size_min': '2400',
    'vnf_image_size_max': '6200',
})

diag_results = []

for seed in suspicious_seeds:
    print(f"\nSeed={seed}:")
    for rb in repo_bws:
        props = base.copy()
        props['repository_bw'] = str(rb)
        props['random_seed'] = str(seed)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.properties', mode='w')
        write_props(props, tmp.name)
        tmp.close()

        cmd = java_cmd_base + [tmp.name]

        try:
            start = time.time()
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  universal_newlines=True, timeout=timeout)
            elapsed = time.time() - start
            output = result.stdout

            # Save stdout
            log_file = os.path.join(diag_dir, f'seed_{seed}_rb_{rb}.log')
            with open(log_file, 'w') as lf:
                lf.write(output)

            heft, dheft, nheft = extract_makespans(output)
            if heft and dheft and nheft:
                gain_pct = (dheft - nheft) / dheft * 100 if dheft > 0 else 0
                print(f"  rb={rb}: HEFT={heft:.2f}, DHEFT={dheft:.2f}, NHEFT={nheft:.2f}, gain={gain_pct:.2f}% ({elapsed:.1f}s)")
                diag_results.append({
                    'seed': seed,
                    'repo_bw': rb,
                    'HEFT': heft,
                    'DHEFT': dheft,
                    'NHEFT': nheft,
                    'gain_pct': gain_pct,
                    'status': 'OK'
                })
            else:
                print(f"  rb={rb}: PARSE ERROR (see {log_file})")
                diag_results.append({
                    'seed': seed,
                    'repo_bw': rb,
                    'HEFT': None,
                    'DHEFT': None,
                    'NHEFT': None,
                    'gain_pct': None,
                    'status': 'PARSE_ERROR'
                })
        except subprocess.TimeoutExpired:
            print(f"  rb={rb}: TIMEOUT")
            diag_results.append({
                'seed': seed,
                'repo_bw': rb,
                'HEFT': None,
                'DHEFT': None,
                'NHEFT': None,
                'gain_pct': None,
                'status': 'TIMEOUT'
            })
        except Exception as e:
            print(f"  rb={rb}: ERROR - {e}")
            diag_results.append({
                'seed': seed,
                'repo_bw': rb,
                'HEFT': None,
                'DHEFT': None,
                'NHEFT': None,
                'gain_pct': None,
                'status': f'ERROR:{e}'
            })
        finally:
            try:
                os.remove(tmp.name)
            except:
                pass

print(f"\n✓ Diagnostic logs saved to: {diag_dir}")
print("\nSummary of diagnostic runs:")
for d in diag_results:
    if d['status'] == 'OK':
        print(f"  seed={d['seed']}, rb={d['repo_bw']}: DHEFT={d['DHEFT']:.2f}, NHEFT={d['NHEFT']:.2f}")

print("\n→ Logs for each run are in:", diag_dir)
print("→ Check if seed, SFC generation, or parsing is the cause of anomalies.")

