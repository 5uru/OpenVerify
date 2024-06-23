#!/bin/bash

source_directory='/Users/jonathansuru/PycharmProjects/OpenVerify/labs/spoofing_detection/datasets/attack'
target_directory='/Users/jonathansuru/PycharmProjects/OpenVerify/labs/spoofing_detection/datasets/attack_new'
number_of_files=268

# Find all files in the source directory and store them in an array
files=("$source_directory"/*)

# Shuffle the array
files=("$(shuf -e "${files[@]}")")

# Move the first 268 files to the target directory
for i in $(seq 1 $number_of_files); do
    mv "${files[$((i-1))]}" "$target_directory"
done
