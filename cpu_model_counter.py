#!/usr/bin/env python3
"""
Kubernetes CPU Model Counter with RAM and CPU Aggregation

This script connects to a Kubernetes cluster using the active context,
iterates over all nodes, and counts how many nodes support each CPU model
based on the cpu-model.node.kubevirt.io/* labels. It also aggregates
the total RAM capacity and CPU count for each CPU model, and displays them
with customizable columns and sorting.

Author: Dan Kenigsberg <danken@redhat.com>
Assisted-by: Cursor IDE and Claude Sonnet 4 (Anthropic)
Date: 2025-07-08
"""

import sys
import argparse
from collections import defaultdict
from datetime import datetime
from kubernetes import client, config
from kubernetes.client.rest import ApiException


# Static dictionary mapping CPU models to their release dates
CPU_MODEL_RELEASE_DATES = {
    # Intel CPU Models (approximate release dates)
    'Raptor Lake': '2022-10-20',
    'Alder Lake': '2021-11-04',
    'Rocket Lake': '2021-03-30',
    'Tiger Lake': '2020-09-02',
    'Ice Lake': '2019-05-28',
    'Comet Lake': '2019-08-21',
    'Cascade Lake': '2019-04-02',
    'Coffee Lake': '2017-10-05',
    'Kaby Lake': '2017-01-03',
    'Skylake': '2015-08-05',
    'Skylake-Client': '2015-08-05',
    'Skylake-Client-IBRS': '2015-08-05',
    'Skylake-Server': '2017-07-11',
    'Skylake-Server-IBRS': '2017-07-11',
    'Broadwell': '2014-10-27',
    'Broadwell-IBRS': '2014-10-27',
    'Broadwell-noTSX': '2014-10-27',
    'Broadwell-noTSX-IBRS': '2014-10-27',
    'Haswell': '2013-06-04',
    'Haswell-IBRS': '2013-06-04',
    'Haswell-noTSX': '2013-06-04',
    'Haswell-noTSX-IBRS': '2013-06-04',
    'IvyBridge': '2012-04-29',
    'IvyBridge-IBRS': '2012-04-29',
    'SandyBridge': '2011-01-09',
    'SandyBridge-IBRS': '2011-01-09',
    'Westmere': '2010-01-07',
    'Westmere-IBRS': '2010-01-07',
    'Nehalem': '2008-11-17',
    'Nehalem-IBRS': '2008-11-17',
    'Penryn': '2007-11-12',
    'Conroe': '2006-07-27',
    
    # AMD CPU Models (approximate release dates)
    'Zen 4': '2022-09-27',
    'Zen 3': '2020-11-05',
    'Zen 2': '2019-07-07',
    'Zen': '2017-03-02',
    'Zen+': '2018-04-19',
    'Piledriver': '2012-10-23',
    'Bulldozer': '2011-10-12',
    'K10': '2007-09-10',
    'K8': '2003-04-22',
    
    # Generic/Common Models
    'EPYC': '2017-06-20',
    'EPYC-IBPB': '2017-06-20',
    'EPYC-Rome': '2019-08-07',
    'EPYC-Milan': '2021-03-15',
    'EPYC-Genoa': '2022-11-10',
    'Opteron_G1': '2005-04-21',
    'Opteron_G2': '2006-08-15',
    'Opteron_G3': '2009-06-01',
    'Opteron_G4': '2011-10-12',
    'Opteron_G5': '2012-10-23',
}


# Static dictionary mapping CPU models to their PassMark CPU Mark scores
# Scores are representative values based on typical processors for each architecture
CPU_MODEL_PASSMARK_SCORES = {
    # Intel CPU Models (PassMark CPU Mark scores)
    'Raptor Lake': 58800,      # i9-14900K/i9-13900K class
    'Alder Lake': 34400,       # i7-12700K class
    'Rocket Lake': 24400,      # i7-11700K class
    'Tiger Lake': 15000,       # i7-1165G7 class
    'Ice Lake': 12000,         # i7-1065G7 class
    'Comet Lake': 18200,       # i9-10900K class
    'Cascade Lake': 22000,     # Xeon Cascade Lake class
    'Coffee Lake': 13600,      # i7-8700K class
    'Kaby Lake': 9600,         # i7-7700K class
    'Skylake': 8900,           # i7-6700K class
    'Skylake-Client': 8900,    # i7-6700K class
    'Skylake-Client-IBRS': 8900, # i7-6700K class
    'Skylake-Server': 15000,   # Xeon Skylake class
    'Skylake-Server-IBRS': 15000, # Xeon Skylake class
    'Broadwell': 7800,         # i7-5775C class
    'Broadwell-IBRS': 7800,    # i7-5775C class
    'Broadwell-noTSX': 7800,   # i7-5775C class
    'Broadwell-noTSX-IBRS': 7800, # i7-5775C class
    'Haswell': 7200,           # i7-4790K class
    'Haswell-IBRS': 7200,      # i7-4790K class
    'Haswell-noTSX': 7200,     # i7-4790K class
    'Haswell-noTSX-IBRS': 7200, # i7-4790K class
    'IvyBridge': 6400,         # i7-3770K class
    'IvyBridge-IBRS': 6400,    # i7-3770K class
    'SandyBridge': 5600,       # i7-2600K class
    'SandyBridge-IBRS': 5600,  # i7-2600K class
    'Westmere': 4200,          # i7-980X class
    'Westmere-IBRS': 4200,     # i7-980X class
    'Nehalem': 3800,           # i7-920 class
    'Nehalem-IBRS': 3800,      # i7-920 class
    'Penryn': 2400,            # Core 2 Quad Q9650 class
    'Conroe': 1800,            # Core 2 Duo E6700 class
    
    # AMD CPU Models (PassMark CPU Mark scores)
    'Zen 4': 62500,            # Ryzen 9 7950X class
    'Zen 3': 39000,            # Ryzen 9 5900X class
    'Zen 2': 32500,            # Ryzen 9 3900X class
    'Zen+': 18100,             # Ryzen 7 3700X class
    'Zen': 17500,              # Ryzen 7 2700X class
    'Piledriver': 8500,        # FX-8350 class
    'Bulldozer': 7200,         # FX-8150 class
    'K10': 3200,               # Phenom II X6 1100T class
    'K8': 1200,                # Athlon 64 X2 6000+ class
    
    # Generic/Common Models
    'EPYC': 25000,             # EPYC 7401P class
    'EPYC-IBPB': 25000,        # EPYC 7401P class
    'EPYC-Rome': 35000,        # EPYC 7542 class
    'EPYC-Milan': 45000,       # EPYC 7543 class
    'EPYC-Genoa': 55000,       # EPYC 9554 class
    'Opteron_G1': 800,         # Opteron 275 class
    'Opteron_G2': 1000,        # Opteron 2218 class
    'Opteron_G3': 1400,        # Opteron 2435 class
    'Opteron_G4': 4200,        # Opteron 6272 class
    'Opteron_G5': 6800,        # Opteron 6386 SE class
}


def get_cpu_model_release_date(cpu_model):
    """Get the release date for a CPU model."""
    # Try exact match first
    if cpu_model in CPU_MODEL_RELEASE_DATES:
        return datetime.strptime(CPU_MODEL_RELEASE_DATES[cpu_model], '%Y-%m-%d')
    
    # Try to find a partial match for models with suffixes
    for model_name, release_date in CPU_MODEL_RELEASE_DATES.items():
        if model_name in cpu_model or cpu_model.startswith(model_name):
            return datetime.strptime(release_date, '%Y-%m-%d')
    
    # Return a very old date for unknown models so they appear last
    return datetime.strptime('1990-01-01', '%Y-%m-%d')


def get_cpu_model_passmark_score(cpu_model):
    """Get the PassMark CPU Mark score for a CPU model."""
    # Try exact match first
    if cpu_model in CPU_MODEL_PASSMARK_SCORES:
        return CPU_MODEL_PASSMARK_SCORES[cpu_model]
    
    # Try to find a partial match for models with suffixes
    for model_name, score in CPU_MODEL_PASSMARK_SCORES.items():
        if model_name in cpu_model or cpu_model.startswith(model_name):
            return score
    
    # Return 0 for unknown models so they appear last when sorting by performance
    return 0


def format_release_date(date_obj):
    """Format release date for display."""
    return date_obj.strftime('%Y-%m-%d')


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Count CPU models in Kubernetes nodes and aggregate resources',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                                    # Default: show model, nodes, cpus, ram, sorted by PassMark
  %(prog)s --columns=model,passmark,nodes     # Show model, PassMark score, and node count
  %(prog)s --columns=model,date,nodes         # Show model, date, and node count
  %(prog)s --columns=model,modeldate,nodes    # Show model, release date, and node count
  %(prog)s --sortby=nodes                     # Sort by node count (descending)
  %(prog)s --sortby=model                     # Sort by model name (alphabetically)
  %(prog)s --columns=model,ram --sortby=ram   # Show model and RAM, sort by RAM
  %(prog)s --columns=model,availcpus,availram # Show available resources
  %(prog)s --sortby=passmark                  # Sort by PassMark performance score
  %(prog)s --recommend                        # Show recommendation for best CPU model

Available columns: model, date, modeldate, passmark, nodes, cpus, ram, availcpus, availram
Available sort options: passmark, modeldate, model, nodes, cpus, ram, availcpus, availram
        ''')
    
    parser.add_argument(
        '--columns',
        default='model,nodes,cpus,ram',
        help='Comma-separated list of columns to display (default: model,nodes,cpus,ram). '
             'Available: model, date, modeldate, passmark, nodes, cpus, ram, availcpus, availram'
    )
    
    parser.add_argument(
        '--sortby',
        default='passmark',
        choices=['passmark', 'modeldate', 'model', 'nodes', 'cpus', 'ram', 'availcpus', 'availram'],
        help='Sort results by specified field (default: passmark)'
    )
    
    parser.add_argument(
        '--recommend',
        action='store_true',
        help='Show recommendation for best CPU model for cluster default'
    )
    
    return parser.parse_args()


def get_sort_key(cpu_model, count, ram_bytes, cpu_cores, avail_ram_bytes, avail_cpu_cores, sort_by):
    """Get sort key based on sort_by option."""
    if sort_by == 'passmark':
        return get_cpu_model_passmark_score(cpu_model)
    elif sort_by == 'modeldate':
        return get_cpu_model_release_date(cpu_model)
    elif sort_by == 'model':
        return cpu_model
    elif sort_by == 'nodes':
        return count
    elif sort_by == 'cpus':
        return cpu_cores
    elif sort_by == 'ram':
        return ram_bytes
    elif sort_by == 'availcpus':
        return avail_cpu_cores
    elif sort_by == 'availram':
        return avail_ram_bytes
    else:
        return cpu_model


def get_sort_reverse(sort_by):
    """Determine if sort should be reversed based on sort_by option."""
    if sort_by in ['passmark', 'modeldate', 'nodes', 'cpus', 'ram', 'availcpus', 'availram']:
        return True  # Descending for these fields
    else:
        return False  # Ascending for model names


def load_kubernetes_config():
    """Load Kubernetes configuration from active context."""
    try:
        # Try to load from cluster config first (if running inside cluster)
        config.load_incluster_config()
        print("Using in-cluster configuration")
    except config.ConfigException:
        try:
            # Load from kubeconfig file
            config.load_kube_config()
            print("Using kubeconfig file")
        except config.ConfigException as e:
            print(f"Error loading Kubernetes configuration: {e}")
            sys.exit(1)


def get_all_nodes():
    """Retrieve all nodes from the cluster."""
    v1 = client.CoreV1Api()
    try:
        nodes = v1.list_node()
        return nodes.items
    except ApiException as e:
        print(f"Error retrieving nodes: {e}")
        sys.exit(1)


def extract_cpu_models(node_labels):
    """Extract CPU models from node labels."""
    cpu_models = []
    cpu_model_prefix = "cpu-model.node.kubevirt.io/"
    
    for label_key, label_value in node_labels.items():
        if label_key.startswith(cpu_model_prefix):
            # Extract the CPU model name from the label key
            cpu_model = label_key[len(cpu_model_prefix):]
            if cpu_model:  # Only add if there's actually a model name
                cpu_models.append(cpu_model)
    
    return cpu_models


def parse_memory_capacity(memory_str):
    """Parse memory capacity string (e.g., '32Gi', '1024Mi') to bytes."""
    if not memory_str:
        return 0
    
    # Remove any whitespace
    memory_str = memory_str.strip()
    
    # Handle different units
    if memory_str.endswith('Ki'):
        return int(memory_str[:-2]) * 1024
    elif memory_str.endswith('Mi'):
        return int(memory_str[:-2]) * 1024 * 1024
    elif memory_str.endswith('Gi'):
        return int(memory_str[:-2]) * 1024 * 1024 * 1024
    elif memory_str.endswith('Ti'):
        return int(memory_str[:-2]) * 1024 * 1024 * 1024 * 1024
    elif memory_str.endswith('Pi'):
        return int(memory_str[:-2]) * 1024 * 1024 * 1024 * 1024 * 1024
    elif memory_str.endswith('Ei'):
        return int(memory_str[:-2]) * 1024 * 1024 * 1024 * 1024 * 1024 * 1024
    else:
        # Assume bytes if no unit
        return int(memory_str)


def parse_cpu_capacity(cpu_str):
    """Parse CPU capacity string (e.g., '4', '8', '1000m') to number of cores."""
    if not cpu_str:
        return 0
    
    # Remove any whitespace
    cpu_str = cpu_str.strip()
    
    # Handle millicores (e.g., '1000m' = 1 core)
    if cpu_str.endswith('m'):
        return int(cpu_str[:-1]) / 1000
    else:
        # Assume whole cores
        return int(cpu_str)


def format_memory_size(bytes_value):
    """Format memory size in bytes to human-readable format."""
    if bytes_value < 1024:
        return f"{bytes_value} B"
    elif bytes_value < 1024 ** 2:
        return f"{bytes_value / 1024:.1f} Ki"
    elif bytes_value < 1024 ** 3:
        return f"{bytes_value / (1024 ** 2):.1f} Mi"
    elif bytes_value < 1024 ** 4:
        return f"{bytes_value / (1024 ** 3):.1f} Gi"
    elif bytes_value < 1024 ** 5:
        return f"{bytes_value / (1024 ** 4):.1f} Ti"
    else:
        return f"{bytes_value / (1024 ** 5):.1f} Pi"


def format_table_row(cpu_model, count, ram_bytes, cpu_cores, avail_ram_bytes, avail_cpu_cores, columns, column_widths):
    """Format a table row based on selected columns."""
    row_data = {
        'model': cpu_model,
        'date': format_release_date(get_cpu_model_release_date(cpu_model)),
        'modeldate': format_release_date(get_cpu_model_release_date(cpu_model)),
        'passmark': str(get_cpu_model_passmark_score(cpu_model)),
        'nodes': str(count),
        'cpus': f"{cpu_cores:.1f}" if cpu_cores != int(cpu_cores) else str(int(cpu_cores)),
        'ram': format_memory_size(ram_bytes),
        'availcpus': f"{avail_cpu_cores:.1f}" if avail_cpu_cores != int(avail_cpu_cores) else str(int(avail_cpu_cores)),
        'availram': format_memory_size(avail_ram_bytes)
    }
    
    row_parts = []
    for col in columns:
        if col in row_data:
            row_parts.append(f"{row_data[col]:<{column_widths[col]}}")
    
    return ' '.join(row_parts)


def get_column_headers_and_widths(columns):
    """Get column headers and their widths."""
    headers = {
        'model': 'CPU Model',
        'date': 'Release Date',
        'modeldate': 'Release Date',
        'passmark': 'PassMark',
        'nodes': 'Nodes',
        'cpus': 'Total CPUs',
        'ram': 'Total RAM',
        'availcpus': 'Avail CPUs',
        'availram': 'Avail RAM'
    }
    
    widths = {
        'model': 40,
        'date': 13,
        'modeldate': 13,
        'passmark': 10,
        'nodes': 8,
        'cpus': 12,
        'ram': 15,
        'availcpus': 12,
        'availram': 15
    }
    
    selected_headers = []
    selected_widths = {}
    
    for col in columns:
        if col in headers:
            selected_headers.append(headers[col])
            selected_widths[col] = widths[col]
    
    return selected_headers, selected_widths


def calculate_cpu_model_scores(cpu_model_counts, cpu_model_avail_ram, cpu_model_avail_cores):
    """Calculate scores for each CPU model to recommend the best default."""
    if not cpu_model_counts:
        return {}
    
    scores = {}
    
    # Get all values for normalization
    all_cpu_cores = list(cpu_model_avail_cores.values())
    all_ram_bytes = list(cpu_model_avail_ram.values())
    all_node_counts = list(cpu_model_counts.values())
    all_dates = [get_cpu_model_release_date(model) for model in cpu_model_counts.keys()]
    
    # Find min/max values for normalization
    max_cpu_cores = max(all_cpu_cores) if all_cpu_cores else 1
    max_ram_bytes = max(all_ram_bytes) if all_ram_bytes else 1
    max_node_count = max(all_node_counts) if all_node_counts else 1
    min_date = min(all_dates) if all_dates else datetime.strptime('1990-01-01', '%Y-%m-%d')
    max_date = max(all_dates) if all_dates else datetime.strptime('2024-01-01', '%Y-%m-%d')
    
    # Avoid division by zero
    date_range = (max_date - min_date).days
    if date_range == 0:
        date_range = 1
    
    # Calculate scores for each CPU model
    for cpu_model in cpu_model_counts:
        # Normalize metrics (0-1 scale)
        cpu_score = cpu_model_avail_cores[cpu_model] / max_cpu_cores
        ram_score = cpu_model_avail_ram[cpu_model] / max_ram_bytes
        node_score = cpu_model_counts[cpu_model] / max_node_count
        
        # CPU age score (newer is better)
        model_date = get_cpu_model_release_date(cpu_model)
        age_score = (model_date - min_date).days / date_range
        
        # Weighted composite score
        # Weights: Available CPUs (40%), Available RAM (30%), Node count (20%), CPU age (10%)
        composite_score = (
            cpu_score * 0.40 +
            ram_score * 0.30 +
            node_score * 0.20 +
            age_score * 0.10
        )
        
        scores[cpu_model] = {
            'composite': composite_score,
            'cpu_score': cpu_score,
            'ram_score': ram_score,
            'node_score': node_score,
            'age_score': age_score
        }
    
    return scores


def recommend_best_cpu_model(cpu_model_counts, cpu_model_avail_ram, cpu_model_avail_cores):
    """Recommend the best CPU model based on scoring."""
    scores = calculate_cpu_model_scores(cpu_model_counts, cpu_model_avail_ram, cpu_model_avail_cores)
    
    if not scores:
        return None
    
    # Find the highest scoring model
    best_model = max(scores.items(), key=lambda x: x[1]['composite'])
    model_name, model_scores = best_model
    
    print(f"\n{'='*80}")
    print("RECOMMENDATION: BEST CPU MODEL FOR CLUSTER DEFAULT")
    print(f"{'='*80}")
    print(f"Recommended CPU Model: {model_name}")
    print(f"Overall Score: {model_scores['composite']:.3f} (out of 1.000)")
    
    # Show breakdown
    print(f"\nScore Breakdown:")
    print(f"  Available CPUs:  {model_scores['cpu_score']:.3f} (40% weight) - {cpu_model_avail_cores[model_name]:.1f} cores")
    print(f"  Available RAM:   {model_scores['ram_score']:.3f} (30% weight) - {format_memory_size(cpu_model_avail_ram[model_name])}")
    print(f"  Node Count:      {model_scores['node_score']:.3f} (20% weight) - {cpu_model_counts[model_name]} nodes")
    print(f"  CPU Generation:  {model_scores['age_score']:.3f} (10% weight) - {format_release_date(get_cpu_model_release_date(model_name))}")
    
    print(f"\nReasoning:")
    print(f"This recommendation balances available resources with node distribution and CPU generation.")
    print(f"The scoring emphasizes available CPU cores (40%) and RAM (30%) as primary factors,")
    print(f"while considering node count for redundancy (20%) and CPU generation for performance (10%).")
    
    # Show top 3 if there are multiple models
    if len(scores) > 1:
        print(f"\nTop 3 CPU Models by Score:")
        sorted_scores = sorted(scores.items(), key=lambda x: x[1]['composite'], reverse=True)
        for i, (model, score_data) in enumerate(sorted_scores[:3]):
            print(f"  {i+1}. {model:<35} {score_data['composite']:.3f}")
    
    # Add OpenShift/KubeVirt configuration command
    print(f"\n{'='*80}")
    print("SETTING AS KUBEVIRT DEFAULT CPU MODEL")
    print(f"{'='*80}")
    print(f"To set '{model_name}' as the default CPU model for OpenShift Virtualization/KubeVirt,")
    print(f"run the following command:")
    print(f"")
    print(f"oc patch hyperconverged kubevirt-hyperconverged \\")
    print(f"  -n openshift-cnv \\")
    print(f"  --type=merge \\")
    print(f"  -p='{{\"spec\":{{\"defaultCPUModel\":\"{model_name}\"}}}}'")
    print(f"")
    print(f"This will configure OpenShift Virtualization to use '{model_name}' as the default")
    print(f"CPU model for new virtual machines when no specific CPU model is specified.")
    print(f"")
    print(f"Note: You may need to adjust the namespace (-n flag) if your OpenShift Virtualization")
    print(f"      operator is installed in a different namespace (e.g., 'kubevirt-hyperconverged').")
    
    return model_name


def count_cpu_models():
    """Count CPU models and aggregate RAM and CPU across all nodes."""
    try:
        args = parse_arguments()
    except SystemExit:
        # Handle cases where argparse exits (like --columns without value)
        print("\nValid columns: model, date, modeldate, passmark, nodes, cpus, ram, availcpus, availram")
        print("Valid sort options: passmark, modeldate, model, nodes, cpus, ram, availcpus, availram")
        sys.exit(1)
    
    # Parse columns
    if not args.columns or args.columns.strip() == '':
        print("Error: --columns cannot be empty.")
        print("Valid columns: model, date, modeldate, passmark, nodes, cpus, ram, availcpus, availram")
        print("Example: --columns=model,nodes,cpus,ram")
        sys.exit(1)
    
    columns = [col.strip() for col in args.columns.split(',')]
    valid_columns = ['model', 'date', 'modeldate', 'passmark', 'nodes', 'cpus', 'ram', 'availcpus', 'availram']
    
    # Validate columns
    invalid_columns = [col for col in columns if col not in valid_columns]
    if invalid_columns:
        print(f"Error: Invalid column(s): {', '.join(invalid_columns)}")
        print(f"Valid columns: {', '.join(valid_columns)}")
        print("Example: --columns=model,nodes,cpus,ram")
        sys.exit(1)
    
    # Remove empty columns (in case of trailing commas)
    columns = [col for col in columns if col]
    
    if not columns:
        print("Error: No valid columns specified.")
        print(f"Valid columns: {', '.join(valid_columns)}")
        print("Example: --columns=model,nodes,cpus,ram")
        sys.exit(1)
    
    print("Connecting to Kubernetes cluster...")
    load_kubernetes_config()
    
    print("Retrieving all nodes...")
    nodes = get_all_nodes()
    
    if not nodes:
        print("No nodes found in the cluster.")
        return
    
    print(f"Found {len(nodes)} nodes in the cluster.")
    
    # Dictionaries to track CPU models and their associated resources
    cpu_model_counts = defaultdict(int)
    cpu_model_ram = defaultdict(int)  # Track total RAM in bytes
    cpu_model_cores = defaultdict(float)  # Track total CPU cores
    cpu_model_avail_ram = defaultdict(int)  # Track available RAM in bytes
    cpu_model_avail_cores = defaultdict(float)  # Track available CPU cores
    nodes_with_cpu_labels = 0
    
    # Process each node
    for node in nodes:
        node_name = node.metadata.name
        node_labels = node.metadata.labels or {}
        
        # Get node resource capacity and allocatable
        node_memory_capacity = node.status.capacity.get('memory', '0')
        node_cpu_capacity = node.status.capacity.get('cpu', '0')
        node_memory_allocatable = node.status.allocatable.get('memory', '0')
        node_cpu_allocatable = node.status.allocatable.get('cpu', '0')
        
        node_memory_capacity_bytes = parse_memory_capacity(node_memory_capacity)
        node_cpu_capacity_cores = parse_cpu_capacity(node_cpu_capacity)
        node_memory_allocatable_bytes = parse_memory_capacity(node_memory_allocatable)
        node_cpu_allocatable_cores = parse_cpu_capacity(node_cpu_allocatable)
        
        print(f"\nProcessing node: {node_name}")
        
        # Extract CPU models from this node's labels
        cpu_models = extract_cpu_models(node_labels)
        
        if cpu_models:
            nodes_with_cpu_labels += 1
            print(f"  CPU models found: {', '.join(cpu_models)}")
            
            # Count each CPU model and add node's resources to each model
            for cpu_model in cpu_models:
                cpu_model_counts[cpu_model] += 1
                cpu_model_ram[cpu_model] += node_memory_capacity_bytes
                cpu_model_cores[cpu_model] += node_cpu_capacity_cores
                cpu_model_avail_ram[cpu_model] += node_memory_allocatable_bytes
                cpu_model_avail_cores[cpu_model] += node_cpu_allocatable_cores
        else:
            print("  No CPU model labels found")
    
    # Display results
    print(f"\n{'='*80}")
    print("CPU MODEL SUMMARY")
    print(f"{'='*80}")
    print(f"Total nodes: {len(nodes)}")
    print(f"Nodes with CPU model labels: {nodes_with_cpu_labels}")
    print(f"Unique CPU models found: {len(cpu_model_counts)}")
    
    if cpu_model_counts:
        # Get headers and widths for selected columns
        headers, column_widths = get_column_headers_and_widths(columns)
        
        # Sort models
        sorted_models = sorted(
            cpu_model_counts.items(),
            key=lambda x: get_sort_key(x[0], x[1], cpu_model_ram[x[0]], cpu_model_cores[x[0]], 
                                     cpu_model_avail_ram[x[0]], cpu_model_avail_cores[x[0]], args.sortby),
            reverse=get_sort_reverse(args.sortby)
        )
        
        # Display table
        sort_desc = {
            'passmark': 'sorted by PassMark score (highest first)',
            'modeldate': 'sorted by release date (newest first)',
            'model': 'sorted by model name',
            'nodes': 'sorted by node count (descending)',
            'cpus': 'sorted by CPU count (descending)',
            'ram': 'sorted by RAM (descending)',
            'availcpus': 'sorted by available CPU count (descending)',
            'availram': 'sorted by available RAM (descending)'
        }
        
        print(f"\nCPU Model Distribution ({sort_desc[args.sortby]}):")
        
        # Print header
        header_row = []
        for i, header in enumerate(headers):
            col_name = columns[i]
            header_row.append(f"{header:<{column_widths[col_name]}}")
        print(' '.join(header_row))
        
        # Print separator
        total_width = sum(column_widths[col] for col in columns) + len(columns) - 1
        print("-" * total_width)
        
        # Print data rows
        for cpu_model, count in sorted_models:
            ram_bytes = cpu_model_ram[cpu_model]
            cpu_cores = cpu_model_cores[cpu_model]
            avail_ram_bytes = cpu_model_avail_ram[cpu_model]
            avail_cpu_cores = cpu_model_avail_cores[cpu_model]
            print(format_table_row(cpu_model, count, ram_bytes, cpu_cores, avail_ram_bytes, avail_cpu_cores, columns, column_widths))
        
        # Add recommendation
        if args.recommend:
            recommend_best_cpu_model(cpu_model_counts, cpu_model_avail_ram, cpu_model_avail_cores)
    else:
        print("\nNo CPU model labels found in any nodes.")
        print("Make sure KubeVirt is installed and CPU models are being detected.")


if __name__ == "__main__":
    try:
        count_cpu_models()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1) 
