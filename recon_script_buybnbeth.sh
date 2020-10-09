#!/bin/bash 
COUNTER=1
while true; do
	echo Counter $COUNTER
	python buy4fees.py > log.log
	echo The main program exited... will restart in 60 seconds... If you want to leave, type Ctrl+C in that interval
	#./send_mail_exit.sh
	sleep 60s
	COUNTER=`expr $COUNTER + 1`
	echo retry...
done
