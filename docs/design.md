---
layout: default
title: Design
nav_order: 9
has_children: true
has_toc: false
description: "The design record: e2e plan, egress and fingerprinting, provider rework."
---

# Design documents

The plans below describe how the tool is built and why. They were written before the code
and are kept as the design record. Each one records decisions, the evidence that produced
them, and what remains open.

- [End-to-end plan]({{ site.baseurl }}{% link plan-e2e.md %}): the test rings, the seams, the acceptance
  criteria, and what cannot be tested offline.
- [Egress and fingerprint]({{ site.baseurl }}{% link plan-egress-fingerprint.md %}): the egress check, the
  browser persona, the budgets and the challenge policy.
- [Provider rework]({{ site.baseurl }}{% link plan-provider-rework.md %}): every step of both sign-up paths,
  the selectors, the blockers and the order of work.

The recon evidence behind those decisions, with DOM snapshots and screenshots, is in the
repository under `docs/recon/`. It is used by the contract tests and is not part of this
site.
