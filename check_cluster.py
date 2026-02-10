import ray

ray.init(address='auto')
nodes = ray.nodes()
alive = [n for n in nodes if n.get('Alive')]

print(f'Nodos activos: {len(alive)}/{len(nodes)}')

total_cpus = sum(n.get('Resources', {}).get('CPU', 0) for n in alive)
print(f'Total CPUs: {int(total_cpus)}')

for i, n in enumerate(alive):
    ip = n.get('NodeManagerAddress')
    cpus = int(n.get('Resources', {}).get('CPU', 0))
    print(f'  Nodo {i+1}: {ip} - {cpus} CPUs')

ray.shutdown()
