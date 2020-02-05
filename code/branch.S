// Test Branches
.section .text
.global _start
.extern monitor
_start:

la gp,monitor
li a1,1 // true
li a2,0 // false

//  eq
li t1, 5
li t2, 5
beq t1,t2, label1
sw a2,4(gp) // not ok...
label1:
sw a1,4(gp) // ok
bne t1,t2, label2
sw a1,8(gp) // ok
j label2b
label2:
sw a2,8(gp) // not ok
label2b:
addi t2,t2,1 // t2 now 6
blt t1,t2,label3
sw a2,12(gp) // not ok
label3:
sw a1,12(gp) // ok
bge t1,t2,label4
sw a1,16(gp) // ok
j label4b
label4:
sw a2,16(gp) // not ok
label4b:
bge t2,t1, label6
sw a2,20(gp) // not ok
label6:
sw a1,20(gp) // ok

li t1, -5
blt t1,t2,label7 // -5 < 6 should be true
sw a2,24(gp) // not ok
label7:
sw a1,24(gp) //  ok
bltu t1,t2, label8 // when t1,t2 considered unsigned t1 < t2 is false
sw a1,0(gp)
label8:
sw a2,0(gp) // not ok



endless:
j endless
