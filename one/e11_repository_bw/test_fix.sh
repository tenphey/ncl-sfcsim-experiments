#!/bin/bash
# Quick test to verify the fix: Run E11 with very limited parameters
# This should generate 200 VNFs consistently

echo "=== Testing E11 parameter fix ==="
echo "Running 1 single test with seed 8258 (previously anomalous) at repo_bw=60"

cd /Users/tengfeisun/Developer/2026/with-downloadscheduling2022-t

# Create a test properties file
TEST_PROPS="/tmp/test_e11.properties"
cat > "$TEST_PROPS" << 'EOF'
cloud_constrained_mode=1
cloud_container_dl_mode=1
core_max_usage=75
vnf_usage_min=20
vnf_usage_max=80
dist_vnf_usage=1
dist_vnf_usage_mu=0.5
vnf_type_max=20
vnf_weight_min=60
vnf_weight_max=240
dist_vnf_weight=1
dist_vnf_weight_mu=0.5
vnf_datasize_min=100
vnf_datasize_max=400
dist_vnf_datasize=1
dist_vnf_datasize_mu=0.5
sfc_vnf_num=200
sfc_vnf_outdegree_min=1
sfc_vnf_outdegree_max=3
sfc_vnf_startnumrate=0.10
sfc_vnf_deapthalpha=1
multiple_sfc_num=1
multiple_sfc_vnf_num_min=200
multiple_sfc_vnf_num_max=200
dist_multiple_sfc_vnf_num=1
dist_multiple_sfc_vnf_num_mu=0.5
datacenter_num=6
datacenter_externalbw_min=100
datacenter_externalbw_max=500
host_num_foreachdc_min=3
host_num_foreachdc_max=5
vm_num_foreachdc_min=3
vm_num_foreachdc_max=5
dist_host_cpu_num=1
dist_host_cpu_num_mu=0.5
host_cpu_num_min=1
host_cpu_num_max=2
host_core_num_foreachcpu_min=2
host_core_num_foreachcpu_max=18
host_thread_num_foreeachcore=2
offload_program_datasize=2
vm_mem_min=1024
vm_mem_max=8192
dist_host_mips=1
dist_host_mips_mu=0.5
host_mips_min=1000
host_mips_max=4000
core_mips_rate_min=1.0
core_mips_rate_max=1.0
dist_host_bw=1
dist_host_bw_mu=0.35
host_bw_min=150
host_bw_max=900
vm_cpi=1
dist_vm_vcpu_num=1
dist_vm_vcpu_num_mu=0.5
vm_vcpu_num_min=1
vm_vcpu_num_max=3
calcmode_level=0
nfv_fairness_weight_overlap=0.5
cmwsl_sched_area=3
mobile_device_num=10
mobile_device_core_num_min=2
mobile_device_core_num_max=4
mobile_device_cpu_mips_min=10
mobile_device_cpu_mips_max=25
mobile_device_bw_min=10
mobile_device_bw_max=50
mobile_device_power_min=60.0
mobile_device_power_max=100.0
dist_mobile_device_power=1
dist_mobile_device_power_mu=0.5
mobile_device_gain_min=0.3
mobile_device_gain_max=0.9
dist_mobile_device_gain=1
dist_mobile_device_gain_mu=0.5
mobile_device_back_noise=100
mec_channel_num=14
mobile_device_tau_min=0.7
mobile_device_tau_max=0.9
dist_mobile_device_tau=1
dist_mobile_device_tau_mu=0.5
vnf_image_size_min=2400
vnf_image_size_max=6200
repository_bw=60
random_seed=8258
EOF

# Run the test
echo ""
echo "Running: java -Xmx1000m -cp classes:lib/* net.gripps.cloud.nfv.main.NFVSchedulingTest $TEST_PROPS"
echo ""
java -Xmx1000m -cp classes:lib/* net.gripps.cloud.nfv.main.NFVSchedulingTest "$TEST_PROPS" 2>&1 | grep -E "^(ConfigFile|HostNum|VNF ID=|===== All VNFs)" | tail -20

# Count VNFs
echo ""
echo "Counting VNFs in output:"
java -Xmx1000m -cp classes:lib/* net.gripps.cloud.nfv.main.NFVSchedulingTest "$TEST_PROPS" 2>&1 | grep "^VNF ID=" | wc -l

rm -f "$TEST_PROPS"

