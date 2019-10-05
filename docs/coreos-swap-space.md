# Setting Up Swap Space on CoreOS

#### Credits to https://coreos.com/os/docs/latest/adding-swap.html

CoreOS doesn't have swap space by default. We use the following commands to set up 2gb of swap space in CoreOS:
```bash
curl http://raw.githubusercontent.com/nimashoghi/YouTube2PodBean/master/scripts/enable_swap.sh | sudo bash
```
