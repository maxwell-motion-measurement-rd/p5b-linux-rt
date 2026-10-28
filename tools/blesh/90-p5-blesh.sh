# Auto-start only for interactive PS UART logins. Sourced by /etc/profile.
case $- in
    *i*)
        if [ -t 0 ] && [ -t 1 ] &&
           [ -z "${P5_BLESH_LOGIN_ACTIVE:-}" ] &&
           [ ! -e /etc/p5-blesh.disabled ] &&
           [ -x /opt/p5-blesh/start.sh ]; then
            case "$(tty 2>/dev/null)" in
                /dev/ttyPS0)
                    if ! grep -qw 'p5_blesh=off' /proc/cmdline; then
                        P5_BLESH_LOGIN_ACTIVE=1 /opt/p5-blesh/start.sh ||
                            printf '\nP5 ble.sh startup failed; plain login shell remains available.\n' >&2
                    fi
                    ;;
            esac
        fi
        ;;
esac
