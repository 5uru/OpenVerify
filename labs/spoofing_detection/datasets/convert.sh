#!/bin/bash

directory='/Users/jonathansuru/PycharmProjects/OpenVerify/labs/spoofing_detection/datasets/tmp1'

for file in "$directory"/*
do
    uuid=$(uuidgen)
    output_file="${directory}/${uuid}.mp4"
    ffmpeg -i "$file" -q:v 0 "$output_file"
    rm "$file"
    mv "$output_file" "/Users/jonathansuru/PycharmProjects/OpenVerify/labs/spoofing_detection/datasets/tmp"
    echo "Converted $file to $output_file"
done