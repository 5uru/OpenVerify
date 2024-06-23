#!/bin/bash

directory='/Users/jonathansuru/PycharmProjects/OpenVerify/labs/spoofing_detection/datasets/real'
csv_file='/Users/jonathansuru/PycharmProjects/OpenVerify/labs/spoofing_detection/datasets/real.csv'

# Empty the CSV file
echo "" > "$csv_file"

# Iterate over the files in the directory
for file in "$directory"/*
do
    # Write the file name and type to the CSV file
    echo "$(basename "$file"),1" >> "$csv_file"
done