---
id: vpn-tunnel-down
title: VPN tunnel is down
system: network
summary: Confirm the tunnel state, isolate which side failed, and restart safely.
tags: [vpn, ipsec, tunnel, network, connectivity]
---

## Step 1 - Check tunnel status on both gateways

Phase 1 and phase 2 status tell you whether IKE or the child SA failed.

```bash
ipsec status
```

## Step 2 - Test reachability to the peer address

A failed ping points at routing or firewall rather than at the negotiation itself.

```bash
ping -c 4 PEER_GATEWAY_IP
```

## Step 3 - Confirm the public address has not changed

Dynamic peers break when the public address changes without a matching local-id.

```bash
dig +short VPN_HOSTNAME
```

## Step 4 - Restart the tunnel service

Restarting drops current sessions; warn users first and prefer a maintenance window.

```bash
systemctl restart strongswan
```

## Step 5 - Verify traffic flows after the restart

Confirm the child SA is established and a host behind the tunnel answers.

```bash
ipsec status
```
