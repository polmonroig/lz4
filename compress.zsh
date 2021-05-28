#!/bin/zsh 

program=$1
files=(
    "la_regenta_utf16"
    "a_40M"
    "file26.bmp"
    "file28.bmp"
    "aes.tar"
    "openssl"
    "wells_the_invisible_man"
    "la_regenta_utf8"
    "la_regenta_utf8_duplicado"
    "YeMi.dna"
    )

prefix="test_files/"

for i in $files; do 
    echo "Testing file $i"
    time python $program -c $prefix$i 
done;
