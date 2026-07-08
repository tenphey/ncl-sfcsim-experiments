#!/usr/bin/env python3
"""
Test the E11 parameter fix by running a single test with the previously anomalous seed.
Verify that we now get 200 VNFs instead of 116.
"""
import subprocess
import os
import tempfile
import sys

REPO_ROOT = "/Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t"
JAVA_CMD = [
    "java",
    "-Xmx1000m",
    "-cp", f"{REPO_ROOT}/classes:{REPO_ROOT}/lib/*",
    "net.gripps.cloud.nfv.main.NFVSchedulingTest"
]

# Create test props with corrected parameters
test_props = {
    'cloud_constrained_mode': '1',
    'cloud_container_dl_mode': '1',
    'vnf_type_max': '20',
    'vnf_weight_min': '60',
    'vnf_weight_max': '240',
    'dist_vnf_weight': '1',
    'dist_vnf_weight_mu': '0.5',
    'vnf_datasize_min': '100',
    'vnf_datasize_max': '400',
    'dist_vnf_datasize': '1',
    'dist_vnf_datasize_mu': '0.5',
    'sfc_vnf_num': '200',
    'sfc_vnf_outdegree_min': '1',
    'sfc_vnf_outdegree_max': '3',
    'sfc_vnf_startnumrate': '0.10',
    'sfc_vnf_deapthalpha': '1',
    'multiple_sfc_num': '1',
    'multiple_sfc_vnf_num_min': '200',  # FIX: Was missing before
    'multiple_sfc_vnf_num_max': '200',  # FIX: Was missing before
    'dist_multiple_sfc_vnf_num': '1',
    'dist_multiple_sfc_vnf_num_mu': '0.5',
    'datacenter_num': '6',
    'host_num_foreachdc_min': '3',
    'host_num_foreachdc_max': '5',
    'vm_num_foreachdc_min': '3',
    'vm_num_foreachdc_max': '5',
    'host_core_num_foreachcpu_min': '2',
    'host_core_num_foreachcpu_max': '18',
    'host_thread_num_foreeachcore': '2',
    'vm_mem_min': '1024',
    'vm_mem_max': '8192',
    'dist_host_mips': '1',
    'dist_host_mips_mu': '0.5',
    'host_mips_min': '1000',
    'host_mips_max': '4000',
    'core_mips_rate_min': '1.0',
    'core_mips_rate_max': '1.0',
    'dist_host_bw': '1',
    'dist_host_bw_mu': '0.35',
    'host_bw_min': '150',
    'host_bw_max': '900',
    'vm_cpi': '1',
    'dist_vm_vcpu_num': '1',
    'dist_vm_vcpu_num_mu': '0.5',
    'vm_vcpu_num_min': '1',
    'vm_vcpu_num_max': '3',
    'vnf_image_size_min': '2400',
    'vnf_image_size_max': '6200',
    'repository_bw': '60',
    'random_seed': '8258',  # Previously anomalous seed
}

# Write properties to temp file
with tempfile.NamedTemporaryFile(mode='w', suffix='.properties', delete=False) as f:
    for k, v in test_props.items():
        f.write(f"{k}={v}\n")
    props_file = f.name

try:
    print("=" * 70)
    print("Testing E11 parameter fix with previously anomalous seed 8258")
    print("=" * 70)
    print(f"\nProperties file: {props_file}")
    print(f"Expected: 200 VNFs (with fixes applied)")
    print(f"Previous (buggy): 116 VNFs (without fixes)")
    print("\nRunning Java simulator...")
    print(f"Command: {' '.join(JAVA_CMD + [props_file])}\n")

    result = subprocess.run(
        JAVA_CMD + [props_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        timeout=120
    )

    output = result.stdout

    # Print first 500 chars for debugging
    if not output.strip():
        print("ERROR: No output from Java. Checking setup...")
        print(f"Return code: {result.returncode}")
        sys.exit(1)

    # Count VNF entries
    vnf_count = output.count("VNF ID=")

    # Extract config info
    for line in output.split('\n'):
        if 'ConfigFile:' in line:
            print(f"\n{line}")
        if 'HostNum:' in line:
            print(f"{line}")
        if '===== All VNFs' in line:
            break

    print(f"\n" + "=" * 70)
    print(f"RESULT: {vnf_count} VNFs generated")
    print("=" * 70)

    if vnf_count == 200:
        print("✓ SUCCESS! Fix is working correctly - 200 VNFs generated")
        sys.exit(0)
    elif vnf_count == 116:
        print("✗ FAILURE! Bug still present - 116 VNFs generated (should be 200)")
        sys.exit(1)
    else:
        print(f"⚠ UNEXPECTED: {vnf_count} VNFs (expected 200)")
        sys.exit(2)

finally:
    try:
        os.remove(props_file)
    except:
        pass

