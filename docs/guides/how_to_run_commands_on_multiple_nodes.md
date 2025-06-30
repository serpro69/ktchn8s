# Run commands on multiple nodes

## Ansible Console

Use [ansible-console](https://docs.ansible.com/ansible/latest/cli/ansible-console.html):

```bash
make console
```

Then enter the command(s) you want to run.

!!! example
    `root@all (4)[f:5]$ uptime`
    <br>
    ```console
    metal0 | CHANGED | rc=0 >>
     10:52:02 up 2 min,  1 user,  load average: 0.17, 0.15, 0.06
    metal1 | CHANGED | rc=0 >>
     10:52:02 up 2 min,  1 user,  load average: 0.14, 0.11, 0.04
    metal3 | CHANGED | rc=0 >>
     10:52:02 up 2 min,  1 user,  load average: 0.03, 0.02, 0.00
    metal2 | CHANGED | rc=0 >>
     10:52:02 up 2 min,  1 user,  load average: 0.06, 0.06, 0.02
    ```

## SSH

You can run commands on nodes using `ssh`. To execute a command on all hosts, use `run` make target with `CMD` input:

!!! example
    ```bash
    make run CMD='hostname'

    draupnir
    done hostname on draupnir
    freyja
    done hostname on freyja
    heimdall
    done hostname on heimdall
    megingjord
    done hostname on megingjord
    odin
    done hostname on odin
    ```
