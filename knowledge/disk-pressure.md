---
id: disk-pressure
title: Node disk pressure
system: kubernetes
summary: Diagnose and relieve a node whose filesystem is filling up.
tags: [disk, storage, kubelet, eviction]
---

## Step 1 - Confirm which filesystem is full

Check usage per mount before touching anything; the root volume and the containerd
volume are usually different filesystems.

```bash
kubectl get nodes -o wide
```

## Step 2 - Inspect usage on the affected node

List the largest consumers under /var/log and the container runtime directory.

```bash
du -xh --max-depth=1 /var/log | sort -h | tail -n 20
```

## Step 3 - Check kubelet eviction signals

Look for eviction messages before deleting files; they tell you whether the pressure
is on disk space, inodes, or memory.

```bash
kubectl describe node NODE_NAME | grep -A5 Conditions
```

## Step 4 - Rotate container logs

Compressed rotation is safe to run and usually recovers the most space per minute.

```bash
journalctl --vacuum-time=3d
```

## Step 5 - Remove stale images from the runtime cache

Only run this after confirming no critical image pull is in progress.

```bash
kubectl drain NODE_NAME --ignore-daemonsets --delete-emptydir-data
```
