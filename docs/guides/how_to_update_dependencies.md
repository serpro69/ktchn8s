---
icon: material/crosshairs-question
title: Update Dependencies
---

# :material-crosshairs-question: HowTo update dependencies

## Metal

!!! tip
    When updating dependencies - for example ansible version, ansible collections versions, and so on - first apply the changes to a single node with: `make -C metal main ANSIBLE_TARGETS=localhost,draupnir`. 
    This reduces the risk of messing everything up (worst case you will mess up one node and can re-provision it) and makes it easier to test version updates in isolation.
    <br>
    When you're happy with the changes and have verified that everything works as expected on the targeted node, you can apply changes to all nodes with: `make metal`.

## System

tbd

<!-- TODO: figure it out and document -->

## External

tbd

<!-- TODO: figure it out and document -->

## Apps/Platform

tbd

<!-- TODO: figure it out and document -->
