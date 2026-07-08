#!/usr/bin/env python3
"""
排查 E11 参数是否正确应用
"""
import os

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
EXPERIMENTS_DIR = os.path.dirname(THIS_DIR)
BASE_PROPS = os.path.join(EXPERIMENTS_DIR, 'base.properties')

# 读取 base.properties
props = {}
with open(BASE_PROPS) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            props[k.strip()] = v.strip()

print("=" * 80)
print("BASE.PROPERTIES CURRENT VALUES")
print("=" * 80)
print(f"sfc_vnf_num = {props.get('sfc_vnf_num', 'NOT FOUND')}")
print(f"multiple_sfc_num = {props.get('multiple_sfc_num', 'NOT FOUND')}")
print(f"multiple_sfc_vnf_num_min = {props.get('multiple_sfc_vnf_num_min', 'NOT FOUND')}")
print(f"multiple_sfc_vnf_num_max = {props.get('multiple_sfc_vnf_num_max', 'NOT FOUND')}")

print("\n" + "=" * 80)
print("EXPECTED VALUES FOR E11")
print("=" * 80)
print("sfc_vnf_num = 200")
print("multiple_sfc_num = 1")
print("multiple_sfc_vnf_num_min = 200")
print("multiple_sfc_vnf_num_max = 200")

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

if props.get('sfc_vnf_num') == '80':
    print("❌ sfc_vnf_num=80 (WRONG! Should be 200 for E11)")
    print("   This creates TOO SMALL SFCs with 80 VNFs instead of 200")
else:
    print("✓ sfc_vnf_num is correct")

if props.get('multiple_sfc_num') == '4':
    print("❌ multiple_sfc_num=4 (WRONG! Should be 1 for E11 with single SFC)")
    print("   This creates 4 separate SFCs instead of 1 unified SFC")
else:
    print("✓ multiple_sfc_num is correct")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("""
The base.properties file has NPPHEFT-optimized parameters that conflict
with E11's requirements. The run_experiment.py TRIES to override them,
but there might be an issue with the override mechanism.

Solution: Modify base.properties to have correct defaults,
or ensure the override is working correctly.
""")

