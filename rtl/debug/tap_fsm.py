"""
Common JTAG TAP state machine used by debug transport frontends.
(c) 2026 The Bonfire Project
License: See LICENSE
"""
from myhdl import always, block, enum, instances


t_tap_state = enum(
    'test_logic_reset',
    'run_test_idle',
    'select_dr_scan',
    'capture_dr',
    'shift_dr',
    'exit1_dr',
    'pause_dr',
    'exit2_dr',
    'update_dr',
    'select_ir_scan',
    'capture_ir',
    'shift_ir',
    'exit1_ir',
    'pause_ir',
    'exit2_ir',
    'update_ir',
)


@block
def TapStateController(tck_i, reset, trstn_i, tms_i, tap_state):
    @always(tck_i.posedge)
    def state_transition():
        if reset or not trstn_i:
            tap_state.next = t_tap_state.test_logic_reset
        elif tap_state == t_tap_state.test_logic_reset:
            if tms_i:
                tap_state.next = t_tap_state.test_logic_reset
            else:
                tap_state.next = t_tap_state.run_test_idle
        elif tap_state == t_tap_state.run_test_idle:
            if tms_i:
                tap_state.next = t_tap_state.select_dr_scan
            else:
                tap_state.next = t_tap_state.run_test_idle
        elif tap_state == t_tap_state.select_dr_scan:
            if tms_i:
                tap_state.next = t_tap_state.select_ir_scan
            else:
                tap_state.next = t_tap_state.capture_dr
        elif tap_state == t_tap_state.capture_dr:
            if tms_i:
                tap_state.next = t_tap_state.exit1_dr
            else:
                tap_state.next = t_tap_state.shift_dr
        elif tap_state == t_tap_state.shift_dr:
            if tms_i:
                tap_state.next = t_tap_state.exit1_dr
            else:
                tap_state.next = t_tap_state.shift_dr
        elif tap_state == t_tap_state.exit1_dr:
            if tms_i:
                tap_state.next = t_tap_state.update_dr
            else:
                tap_state.next = t_tap_state.pause_dr
        elif tap_state == t_tap_state.pause_dr:
            if tms_i:
                tap_state.next = t_tap_state.exit2_dr
            else:
                tap_state.next = t_tap_state.pause_dr
        elif tap_state == t_tap_state.exit2_dr:
            if tms_i:
                tap_state.next = t_tap_state.update_dr
            else:
                tap_state.next = t_tap_state.shift_dr
        elif tap_state == t_tap_state.update_dr:
            if tms_i:
                tap_state.next = t_tap_state.select_dr_scan
            else:
                tap_state.next = t_tap_state.run_test_idle
        elif tap_state == t_tap_state.select_ir_scan:
            if tms_i:
                tap_state.next = t_tap_state.test_logic_reset
            else:
                tap_state.next = t_tap_state.capture_ir
        elif tap_state == t_tap_state.capture_ir:
            if tms_i:
                tap_state.next = t_tap_state.exit1_ir
            else:
                tap_state.next = t_tap_state.shift_ir
        elif tap_state == t_tap_state.shift_ir:
            if tms_i:
                tap_state.next = t_tap_state.exit1_ir
            else:
                tap_state.next = t_tap_state.shift_ir
        elif tap_state == t_tap_state.exit1_ir:
            if tms_i:
                tap_state.next = t_tap_state.update_ir
            else:
                tap_state.next = t_tap_state.pause_ir
        elif tap_state == t_tap_state.pause_ir:
            if tms_i:
                tap_state.next = t_tap_state.exit2_ir
            else:
                tap_state.next = t_tap_state.pause_ir
        elif tap_state == t_tap_state.exit2_ir:
            if tms_i:
                tap_state.next = t_tap_state.update_ir
            else:
                tap_state.next = t_tap_state.shift_ir
        else:
            if tms_i:
                tap_state.next = t_tap_state.select_dr_scan
            else:
                tap_state.next = t_tap_state.run_test_idle

    return instances()
