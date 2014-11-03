#!/bin/bash
awk '{print$1}' < proxy_to_clean.txt >> prox.txt
echo "" > proxy_to_clean.txt
