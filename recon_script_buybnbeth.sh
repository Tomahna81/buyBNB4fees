#!/bin/bash 
COUNTER=1
while true; do
	echo Counter $COUNTER
	#python3.6 hello_test.py
	python3.6 buy4fees.py > log.log
	echo The main program exited... will restart in 60 seconds... If you want to leave, type Ctrl+C in that interval
	#./send_python_exit.sh
	sleep 60s
	COUNTER=`expr $COUNTER + 1`
	#test $? -gt 128 && break;
	echo retry...
done
