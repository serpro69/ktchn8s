---
icon: material/format-list-checks
---

# :material-format-list-checks: ToDo

<div class="banner-image-wrapper">
  <img class="banner-image" src="https://images.unsplash.com/photo-1598791318878-10e76d178023?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" style="object-position: 50% 60%; height: 200px;">
</div>

- [ ] Update [architecture/overview](./architecture/overview.md) components
    - Basic diagram of code components and their relations
    - Description of components and their purpose
- [ ] Update [concepts/pxe-boot](../concepts/pxe-boot.md) with a visual "in-action" showcase of how it works, once it's in place

- [ ] Add up-to-date config files of C1111 and C3560 for reference
    - Can be placed in a separate note (probably don't even need to make it visible in nav menu) and referenced from [installation/network](../installation/network.md)

- [ ] Check that devices on Guest WiFi network (when Eero is in AP/Bridge mode!) are still isolated and cannot see or communicate with each other or the main network.
    - Eero in Bridge mode looses a lot of security related functionality (it becomes "greyed out" in the app also.) However, it seems that the guest network can still be enabled from the app. Hopefully that guest network is still isolated, but needs double-checking.
    - Some related links: 
        - <https://www.reddit.com/r/eero/comments/g0mjqi/guest_network_and_general_routing_questions/>
