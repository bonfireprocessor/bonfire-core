.section .text
.global _start
.extern monitor
//.extern mtime

#define check(_result) \
  li s2,_result; \
  jal store \


_start:
//la s0,trap_handler
//csrw mtvec,s0

la s0, monitor
add gp,s0,0x200 // test result area
//la s1,mtime

la a1,data_area // store area

li a2,0x0FA55AA55

//lw a3,0(s1) // get timer
//sw a3,4(s0)



sw a2, 0(a1)  // Test word r/w
lw t4, 0(a1)   // => FA55AA55
check(0xfa55aa55)
sb a2, 8(a1) // store two bytes
sb a2, 9(a1)
lw t4,8(a1)  // => 00005555
check(0x5555)

lbu t4, 1(a1) // 1(a1) contains AA (see above) => 000000AA
check(0xaa)
lb t4,1(a1)   // same signed => FFFFFFAA
check(0xffffffaa)
lbu t4,0(a1) // => 00000055
check(0x55)
lb  t4,0(a1) // => 00000055
check(0x55)
sh a2,12(a1) // Store 16 Bit Word
srli t1,a2,16
sh t1,14(a1) // Store Upper half of a2

lw t4,12(a1) // should be FA55AA55
check(0xfa55aa55)

lhu t4,14(a1) // => 0000FA55
check(0xfa55)
lh  t4,14(a1) // => FFFFFA55
check(0xfffffa55)
lhu t4,12(a1) // => 0000AA55
check(0xaa55)
lh  t4,12(a1) // => FFFFAA55
check(0xffffaa55)

// misalign tests
/*
sh t1,17(a1) // test store of "middle" half word
check(6)
sw t1,17(a1)
check(6)
lw t1,18(a1)
check(4)
lh t1,17(a1)
check(4)

lw t0,0(s1) // load timer
sw t0,4(s0) // store timer to monitor
sltu t4,a3,t0 // check if old timer (a3) < new timer (t0)
check(1)
*/

li t0,1
sw t0,0(s0) // write 1 to monitor result register



store: // store t4 to mem and increment
sw t4,0(gp) // save result
add gp,gp,4 // increment pointer
beq t4,s2,ok // check if t4 contains desired result

sw s2,4(s0) // check value
li s2,-1
sw s2,(s0)  // write -1 to monitor result address

ok:
ret

/*
trap_handler:
la a4, (monitor+0x1000) // Trap output area
csrr t4, mcause // will also return mcause in t4

sw t4,0(a4)
csrr x31, mepc
sw x31,4(a4)
addi x31,x31,4
csrw mepc,x31
csrr t1,mbadaddr
sw x31,8(a4)
csrr x31,mstatus
sw x31,12(a4)
mret
*/

.align 4
data_area:
