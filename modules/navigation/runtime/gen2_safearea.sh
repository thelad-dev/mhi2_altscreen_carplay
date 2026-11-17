#!/bin/ksh
set -u

MIBR_ROOT=${MIBR_ROOT:-/mnt/app/root/mibr}
ROOT=$MIBR_ROOT/config/cockpit
CONF=$ROOT/mibr-carplay111-safearea.conf
CARPLAY_CONF=$MIBR_ROOT/config/carplay/altscreen111.conf
# Canvas size of the Stream-111 display. 1010x376 is the MU1440 reference and
# stays the default; a profile with another size (for example 800x480) states it
# in altscreen111.conf, the same file the GEN2 launcher reads.
FULL_W=1010
FULL_H=376
FULL_SRC=default
RW=0

usage(){
  echo "usage:"
  echo "  gen2_safearea.sh status"
  echo "  gen2_safearea.sh full"
  echo "  gen2_safearea.sh set X Y W H"
  echo "  gen2_safearea.sh bottom PIXELS"
  echo "  gen2_safearea.sh inset LEFT TOP RIGHT BOTTOM"
  echo "  gen2_safearea.sh clear"
  exit 2
}

app_rw(){
  [ "$RW" -eq 1 ] && return 0
  mount -uw /mnt/app 2>/dev/null || {
    echo "GEN2_SAFEAREA=FAIL_MOUNT_APP_RW"
    exit 10
  }
  RW=1
}

app_ro(){
  if [ "$RW" -eq 1 ]; then
    sync 2>/dev/null || true
    mount -ur /mnt/app 2>/dev/null || true
    RW=0
  fi
}
trap app_ro 0 1 2 15

is_uint(){
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

# Take the canvas size from altscreen111.conf when it names one. Both values
# must be plain integers in range; anything else stops instead of guessing.
load_full_size(){
  [ -r "$CARPLAY_CONF" ] || return 0
  cw=
  ch=
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ALTSCREEN111_WIDTH=*) cw=${line#ALTSCREEN111_WIDTH=} ;;
      ALTSCREEN111_HEIGHT=*) ch=${line#ALTSCREEN111_HEIGHT=} ;;
    esac
  done < "$CARPLAY_CONF"
  [ -z "$cw" ] && [ -z "$ch" ] && return 0
  if is_uint "$cw" && is_uint "$ch" && [ "$cw" -ge 100 ] && [ "$cw" -le 4096 ] &&
     [ "$ch" -ge 60 ] && [ "$ch" -le 2160 ]; then
    FULL_W=$cw
    FULL_H=$ch
    FULL_SRC=altscreen111.conf
    return 0
  fi
  echo "GEN2_SAFEAREA=FAIL_CANVAS_SIZE conf=$CARPLAY_CONF width=$cw height=$ch"
  exit 14
}

validate_rect(){
  x=$1
  y=$2
  w=$3
  h=$4

  is_uint "$x" || return 1
  is_uint "$y" || return 1
  is_uint "$w" || return 1
  is_uint "$h" || return 1

  [ "$w" -gt 0 ] || return 1
  [ "$h" -gt 0 ] || return 1
  [ "$x" -lt "$FULL_W" ] || return 1
  [ "$y" -lt "$FULL_H" ] || return 1
  [ $((x+w)) -le "$FULL_W" ] || return 1
  [ $((y+h)) -le "$FULL_H" ] || return 1
  return 0
}

write_rect(){
  x=$1
  y=$2
  w=$3
  h=$4
  validate_rect "$x" "$y" "$w" "$h" || {
    echo "GEN2_SAFEAREA=FAIL_RANGE x=$x y=$y w=$w h=$h full=${FULL_W}x${FULL_H}"
    exit 11
  }

  app_rw
  tmp="$CONF.tmp.$$"
  {
    echo "x=$x"
    echo "y=$y"
    echo "w=$w"
    echo "h=$h"
  } > "$tmp" || {
    rm -f "$tmp" 2>/dev/null || true
    echo "GEN2_SAFEAREA=FAIL_WRITE path=$CONF"
    exit 12
  }
  mv "$tmp" "$CONF" || {
    rm -f "$tmp" 2>/dev/null || true
    echo "GEN2_SAFEAREA=FAIL_RENAME path=$CONF"
    exit 13
  }
  app_ro

  echo "GEN2_SAFEAREA=STORED"
  echo "config=$CONF"
  echo "x=$x"
  echo "y=$y"
  echo "w=$w"
  echo "h=$h"
  echo "apply=next_altScreen_info_handshake"
  echo "first_try=reconnect_carplay"
  echo "unit_reboot=not_required_first"
}

show_status(){
  echo "=== GEN2 SAFEAREA ==="
  echo "full_width=$FULL_W"
  echo "full_height=$FULL_H"
  echo "full_source=$FULL_SRC"
  echo "config=$CONF"
  if [ -r "$CONF" ]; then
    echo "configured=1"
    cat "$CONF"
    sx=
    sy=
    sw=
    sh=
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in
        x=*) sx=${line#x=} ;;
        y=*) sy=${line#y=} ;;
        w=*) sw=${line#w=} ;;
        h=*) sh=${line#h=} ;;
      esac
    done < "$CONF"
    if validate_rect "$sx" "$sy" "$sw" "$sh"; then
      echo "configured_in_range=1"
    else
      echo "configured_in_range=0"
    fi
  else
    echo "configured=0"
    echo "x=0"
    echo "y=0"
    echo "w=$FULL_W"
    echo "h=$FULL_H"
  fi
  echo "apply=next_altScreen_info_handshake"
}

load_full_size

cmd=${1:-status}
case "$cmd" in
  status)
    show_status
    ;;
  full)
    write_rect 0 0 "$FULL_W" "$FULL_H"
    ;;
  set)
    [ $# -eq 5 ] || usage
    write_rect "$2" "$3" "$4" "$5"
    ;;
  bottom)
    [ $# -eq 2 ] || usage
    is_uint "$2" || usage
    [ "$2" -lt "$FULL_H" ] || usage
    write_rect 0 0 "$FULL_W" $((FULL_H-$2))
    ;;
  inset)
    [ $# -eq 5 ] || usage
    l=$2
    t=$3
    r=$4
    b=$5
    is_uint "$l" || usage
    is_uint "$t" || usage
    is_uint "$r" || usage
    is_uint "$b" || usage
    w=$((FULL_W-l-r))
    h=$((FULL_H-t-b))
    write_rect "$l" "$t" "$w" "$h"
    ;;
  clear)
    app_rw
    rm -f "$CONF"
    app_ro
    echo "GEN2_SAFEAREA=CLEARED"
    echo "fallback=full_canvas_${FULL_W}x${FULL_H}"
    echo "apply=next_altScreen_info_handshake"
    ;;
  *)
    usage
    ;;
esac
