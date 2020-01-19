.section .text
.global _start
_start:

li a1,10 
li a2,5
test:
add a3,a1,a2 // a3 == 15 (0xf)
slli a4,a3,4 // a4==0xf0
ori a4,a4,5 // a4==0xf5
neg a2,a2   //  a2 = -5
sltz a5,a2  // a5 == 1
sltiu a5,a2,0 // a5 == 0
lui a5, 0x80000 // a5==0x80000000
srai a5,a5,24 // a5==0xffffff80
mv s1,a5 // a1==0xffffff80

// a1 == 10 and a2== -5 here 
beq a1,a2, test // no
//bne a1,a2, test // yes
//blt a2,a1, test // yes 
//bltu a2,a1,test // no 

// Load store unit 
li s1, 0
li s2, 0xdeadbeef
sw s2,4(s1)
lbu a1,5(s1) # should load 0xbe  
jal a6, test
