yosys -import
source edalize_yosys_procs.tcl

# Compute a path relative to 'base' (replacement for 'file relative')
proc relative_path {base path} {
    # Normalize both paths
    set base [file normalize $base]
    set path [file normalize $path]

    # Split into components
    set bl [file split $base]
    set pl [file split $path]

    # Find common prefix length
    set i 0
    set max [expr {[llength $bl] < [llength $pl] ? [llength $bl] : [llength $pl]}]
    while {$i < $max && [lindex $bl $i] eq [lindex $pl $i]} {
        incr i
    }

    # Number of ".." needed to go up from base
    set up [expr {[llength $bl] - $i}]
    set rel {}
    for {set j 0} {$j < $up} {incr j} {
        lappend rel ..
    }

    # Append remaining parts of 'path'
    set rel [concat $rel [lrange $pl $i end]]

    # If identical paths, return "."
    if {[llength $rel] == 0} {
        return "."
    }
    # Join list back to a path
    return [file join {*}$rel]
}

# Recursively collect VHDL files and return relative paths to 'base'
proc find_vhdl_files {base dir} {
    set result {}

    # Collect files in current directory (case-insensitive .vhd/.vhdl)
    foreach f [glob -nocomplain -types f -directory $dir *] {
        if {[regexp -nocase {\.vhd(l)?$} $f]} {
            lappend result [relative_path $base $f]
        }
    }

    # Recurse into subdirectories
    foreach subdir [glob -nocomplain -types d -directory $dir *] {
        # Skip . and ..
        if {[file tail $subdir] in {. ..}} continue
        set result [concat $result [find_vhdl_files $base $subdir]]
    }

    return $result
}


set srcdir [file join [pwd] src]
set srcfiles [find_vhdl_files [pwd] $srcdir]


plugin -i ghdl
echo on
yosys ghdl --std=08 --ieee=synopsys -frelaxed-rules  -Wno-specs {*}$srcfiles -e $top
echo off

synth_ecp5 -top $top -json $name.json

