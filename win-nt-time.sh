#!/bin/bash

# Context
# Active Directory stores time values as a large integer that represents the number of 100-nanosecond intervals since January 1, 1601 (UTC). ie. Windows NT time.  The Gregorian calendar operates on a 400-year cycle, and 1601 is the first year of the cycle that was active at the time Windows NT was being designed. In other words, it was chosen to make the math come out nicely.
# ex. lockoutTime: 132236602206716148

# Purpose
# This will convert that time to a human readable format. 

read -p  "Enter the value given by Active Directory:" WINNTTIME
# round it up by dividing it by 10000000 and since windows timestamp start from 1601-01-01 then remove seconds between 1601-01-01 and 1970-01-01 
seconds=$(expr ${WINNTTIME} / 10000000 - 11644477200)
# linux would require date -d, but MacOS uses date -r
date -r ${seconds}
