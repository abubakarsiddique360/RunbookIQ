---
id: pod-crashloop
title: Pod stuck in CrashLoopBackOff
system: kubernetes
summary: Find why a container keeps restarting, without guessing at the application code.
tags: [kubernetes, pod, crashloop, restart, logs]
---

## Step 1 - List the unhealthy pods

Start from the workload rather than a single pod name, so you see every replica.

```bash
kubectl get pods -n NAMESPACE -o wide
```

## Step 2 - Read the termination reason

The exit code and reason separate an application crash from an OOM kill or a probe
failure.

```bash
kubectl describe pod POD_NAME -n NAMESPACE
```

## Step 3 - Read the previous container logs

CrashLoopBackOff means the current container is young, so ask for the previous run.

```bash
kubectl logs POD_NAME -n NAMESPACE --previous --tail=200
```

## Step 4 - Look at resource limits and probes

Compare the last state reason with the limits; a 137 exit code means the kernel
killed the container for memory.

```bash
kubectl get pod POD_NAME -n NAMESPACE -o jsonpath={.status.containerStatuses}
```

## Step 5 - Roll back the last deployment if the crash is new

Only after the logs show a regression introduced by the current revision.

```bash
kubectl rollout undo deployment/DEPLOYMENT_NAME -n NAMESPACE
```
