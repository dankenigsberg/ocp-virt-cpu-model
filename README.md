# Default CPU Model recommendation for OpenShift Virtualization
If you are running a heterogenous cluster, with multiple vendor and cpu models,
it is not always easy to choose the best CPU model for your virtual machines.
If you use a new model, only a small subset of the cluster would be able to run it.
If you use an old model, your guests may be impacted.

This script is intended to help you find a reasonable sweet point.
It takes into account the number of nodes that can run a specific CPU model,
the number of physical CPUs on these nodes as well as the available memory there.

## Example
```
$ python cpu_model_counter.py --recommend
================================================================================
CPU MODEL SUMMARY
================================================================================
Total nodes: 25
Nodes with CPU model labels: 23
Unique CPU models found: 66

CPU Model Distribution (sorted by PassMark score (highest first)):
CPU Model                                Nodes    Total CPUs   Total RAM      
------------------------------------------------------------------------------
EPYC-Rome                                3        768          754.3 Gi       
EPYC                                     3        768          754.3 Gi       
EPYC-IBPB                                3        768          754.3 Gi       
EPYC-Rome-v1                             3        768          754.3 Gi       
EPYC-Rome-v2                             3        768          754.3 Gi       
EPYC-Rome-v3                             3        768          754.3 Gi       
EPYC-Rome-v4                             3        768          754.3 Gi       
EPYC-v1                                  3        768          754.3 Gi       
EPYC-v2                                  3        768          754.3 Gi       
EPYC-v3                                  3        768          754.3 Gi       
EPYC-v4                                  3        768          754.3 Gi       
Skylake-Client-noTSX-IBRS                14       1352         9.6 Ti         
Skylake-Client-v3                        10       992          8.6 Ti         
Skylake-Client-v4                        10       992          8.6 Ti         
Skylake-Server-noTSX-IBRS                14       1352         9.6 Ti         
Skylake-Server-v3                        10       992          8.6 Ti         
Skylake-Server-v4                        10       992          8.6 Ti         
Skylake-Server-v5                        10       992          8.6 Ti         
Broadwell-noTSX                          18       1576         12.4 Ti        
Broadwell-noTSX-IBRS                     18       1576         12.4 Ti        
Broadwell-v2                             14       1216         11.5 Ti        
Broadwell-v4                             14       1216         11.5 Ti        
Broadwell                                4        224          2.9 Ti         
Broadwell-IBRS                           4        224          2.9 Ti         
Broadwell-v1                             4        224          2.9 Ti         
Broadwell-v3                             4        224          2.9 Ti         
Haswell-noTSX                            20       1696         14.4 Ti        
Haswell-noTSX-IBRS                       20       1696         14.4 Ti        
Haswell-v2                               16       1336         13.4 Ti        
Haswell-v4                               16       1336         13.4 Ti        
Haswell                                  4        224          2.9 Ti         
Haswell-IBRS                             4        224          2.9 Ti         
Haswell-v1                               4        224          2.9 Ti         
Haswell-v3                               4        224          2.9 Ti         
IvyBridge                                20       1696         14.4 Ti        
IvyBridge-IBRS                           20       1696         14.4 Ti        
IvyBridge-v1                             16       1336         13.4 Ti        
IvyBridge-v2                             16       1336         13.4 Ti        
SandyBridge                              23       2464         15.1 Ti        
SandyBridge-IBRS                         23       2464         15.1 Ti        
SandyBridge-v1                           19       2104         14.2 Ti        
SandyBridge-v2                           19       2104         14.2 Ti        
Westmere                                 23       2464         15.1 Ti        
Westmere-IBRS                            23       2464         15.1 Ti        
Westmere-v1                              19       2104         14.2 Ti        
Westmere-v2                              19       2104         14.2 Ti        
Nehalem                                  23       2464         15.1 Ti        
Nehalem-IBRS                             23       2464         15.1 Ti        
Nehalem-v1                               19       2104         14.2 Ti        
Nehalem-v2                               19       2104         14.2 Ti        
Penryn                                   23       2464         15.1 Ti        
Penryn-v1                                19       2104         14.2 Ti        
Opteron_G3                               3        768          754.3 Gi       
Opteron_G3-v1                            3        768          754.3 Gi       
Opteron_G1                               4        360          1005.6 Gi      
Cascadelake-Server-noTSX                 14       1352         9.6 Ti         
Cascadelake-Server-v3                    10       992          8.6 Ti         
Cascadelake-Server-v4                    10       992          8.6 Ti         
Cascadelake-Server-v5                    10       992          8.6 Ti         
Denverton-v2                             4        640          5.9 Ti         
Denverton-v3                             4        640          5.9 Ti         
Icelake-Server-noTSX                     4        640          5.9 Ti         
Icelake-Server-v2                        4        640          5.9 Ti         
Dhyana                                   3        768          754.3 Gi       
Dhyana-v1                                3        768          754.3 Gi       
Dhyana-v2                                3        768          754.3 Gi       

================================================================================
RECOMMENDATION: BEST CPU MODEL FOR CLUSTER DEFAULT
================================================================================
Recommended CPU Model: SandyBridge
Overall Score: 0.971 (out of 1.000)

Score Breakdown:
  Available CPUs:  1.000 (40% weight) - 2451.0 cores
  Available RAM:   1.000 (30% weight) - 15.0 Ti
  Node Count:      1.000 (20% weight) - 23 nodes
  CPU Generation:  0.710 (10% weight) - 2011-01-09

Reasoning:
This recommendation balances available resources with node distribution and CPU generation.
The scoring emphasizes available CPU cores (40%) and RAM (30%) as primary factors,
while considering node count for redundancy (20%) and CPU generation for performance (10%).

Top 3 CPU Models by Score:
  1. SandyBridge                         0.971
  2. SandyBridge-IBRS                    0.971
  3. Westmere                            0.968

================================================================================
SETTING AS KUBEVIRT DEFAULT CPU MODEL
================================================================================
To set 'SandyBridge' as the default CPU model for OpenShift Virtualization/KubeVirt,
run the following command:

oc patch hyperconverged kubevirt-hyperconverged \
  -n openshift-cnv \
  --type=merge \
  -p='{"spec":{"defaultCPUModel":"SandyBridge"}}'

This will configure OpenShift Virtualization to use 'SandyBridge' as the default
```

## Author
Dan Kenigsberg <danken@redhat.com>

## Testing
Next to none. The script provides nothing but a seemingly reasonable heuristics.
Please use with great care! Your mileage may vary much.
