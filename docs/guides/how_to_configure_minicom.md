---
icon: material/crosshairs-question
---

# :material-crosshairs-question: Configure `minicom`

- Run `sudo minicom -s`, the following screen will appear:

```
+-----[configuration]------+
| Filenames and paths      |
| File transfer protocols  |
| Serial port setup        |
| Modem and dialing        |
| Screen and keyboard      |
| Save setup as dfl        |
| Save setup as..          |
| Exit                     |
| Exit from Minicom        |
+--------------------------+
```

- Select **Serial port setup** and update your configuration settings to the following:

```
+-----------------------------------------------------------------------+
| A -    Serial Device      : /dev/ttyUSB0                              |
| B - Lockfile Location     : /var/lock                                 |
| C -   Callin Program      :                                           |
| D -  Callout Program      :                                           |
| E -    Bps/Par/Bits       : 9600 8N1                                  |
| F - Hardware Flow Control : No                                        |
| G - Software Flow Control : No                                        |
| H -     RS485 Enable      : No                                        |
| I -   RS485 Rts On Send   : No                                        |
| J -  RS485 Rts After Send : No                                        |
| K -  RS485 Rx During Tx   : No                                        |
| L -  RS485 Terminate Bus  : No                                        |
| M - RS485 Delay Rts Before: 0                                         |
| N - RS485 Delay Rts After : 0                                         |
|                                                                       |
|    Change which setting?                                              |
+-----------------------------------------------------------------------+
```

!!! note
    You may need to adjust the serial device path (`/dev/ttyUSB0`) based on your system and the type of cable you use. You can find the correct path by running `dmesg | grep -i tty` after connecting the serial cable to your PC and router/switch.

- Save configuration and exit.

!!! warning
    `minicom` uses <key>Ctrl</key>+`<key>` shortcuts for navigation. Make sure they don't conflict with some of your other terminal shortcuts.
    E.g. my [`tmux` configuration](https://github.com/serpro69/notfiles/blob/master/tmux.conf.local) uses `C-a` as prefix key, and that conflicts with `minicom`, so I usually have to use `minicom` outside of `tmux`.

