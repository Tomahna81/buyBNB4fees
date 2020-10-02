# Use the binance client available at https://github.com/sammchardy/python-binance
# Nicely done help available at: https://python-binance.readthedocs.io/en/latest/market_data.html
from binance.client import Client
import numpy as np
import time
import dateparser
from datetime import datetime
import pytz
import json
import glob
import os, fnmatch
from scipy import interpolate
import math
import copy
#from uncertainties import unumpy

# Return the values that were deposited or withdrawn for each asset along with 
# the time of the transaction, the amount transfered and its equivalent amount in btc at
# the time of the  transaction
def get_historical_depositswithdraws(client, output_dir=''):

	# constantsupdate_history_symbol
	#dt=60000 # minimum time interval is 1 min (in ms)
	dt=interval_to_milliseconds('1d')

	# Get how much was deposited initially in the account
	deposits=client.get_deposit_history() # list how much has been deposited in all kind of currency
	Ndeposits=len(deposits['depositList'])
	
	d_assets=[]
	d_time=np.zeros(Ndeposits)
	d_amount=np.zeros(Ndeposits)
	d_btc_price=np.zeros(Ndeposits) # the btc price of the asset at the time of deposit
	print('Getting the list of deposits...')
	print('    Total number of deposits: ' + str(Ndeposits))
	for p in range(Ndeposits):
		d_assets.append(deposits['depositList'][p]['asset'])
		d_time[p]=deposits['depositList'][p]['insertTime']
		d_amount[p]=deposits['depositList'][p]['amount']
		if str.strip(d_assets[p]) != 'BTC':
			print('   ['+ str(p) +']' + ' Converting price using '+ d_assets[p]+'BTC' + ' conversion rate...')
			kline_tmp=client.get_historical_klines(d_assets[p]+'BTC', Client.KLINE_INTERVAL_1MINUTE, str(d_time[p]), str(d_time[p]+dt))
			#print(kline_tmp)
			if kline_tmp[0][1] != 0:
				d_btc_price[p]=np.mean(np.double(kline_tmp[0][1:5]))
			else:
				print('Error: returned value of the coin are 0!')
				print('Need debug. Program will exit now')
				exit()
			time.sleep(1)
		else:
			print('   ['+ str(p) +']' + ' Dealing with a deposit in BTC... no required conversion')
			d_btc_price[p]=1.
	

	# Get how much was withdraw
	withdraws = client.get_withdraw_history()
	Nwithdraws=len(withdraws['withdrawList'])
	
	w_assets=[]
	w_time=np.zeros(Nwithdraws, dtype=int)
	w_amount=np.zeros(Nwithdraws)
	#w_fees=np.zeros(Nwithdraws)
	w_btc_price=np.zeros(Nwithdraws) # the btc price of the asset at the time of withdrawal
	print('Getting the list of withdrawals...')
	print('    Total number of withdrawals: ' + str(Nwithdraws))
	for p in range(Nwithdraws):
		w_assets.append(withdraws['withdrawList'][p]['asset'])
		w_time[p]=withdraws['withdrawList'][p]['successTime']
		w_amount[p]=withdraws['withdrawList'][p]['amount']
		#w_fees[p]=client.get_withdraw_fee(asset=w_assets[p])
		if str.strip(w_assets[p]) != 'BTC':
			print('   ['+ str(p) +']' + ' Converting price using '+ w_assets[p]+'BTC' + ' conversion rate...')
			kline_tmp=client.get_historical_klines(w_assets[p]+'BTC', Client.KLINE_INTERVAL_1MINUTE, str(w_time[p]), str(w_time[p]+dt))
			if kline_tmp[0][1] != 0:
				w_btc_price[p]=np.mean(np.double(kline_tmp[0][1:5]))
			else:
				print('Error: returned value of the coin are 0!')
				print('Need debug. Program will exit now')
				exit()
			time.sleep(0.5)
		else:
			print('   ['+ str(p) +']' + ' Dealing with a withdraw in BTC... no required conversion')
			w_btc_price[p]=1.
			
	# Convert all deposits/withdraws into BTC (and TUSD later)
	d_amount_btc=d_amount*d_btc_price
	w_amount_btc=w_amount*w_btc_price
	
	
	dic_deposit={'assets':d_assets, 'time':d_time, 'amount':d_amount, 'amount_btc':d_amount_btc, 'btc_price':d_btc_price}
	dic_withdraw={'assets':w_assets, 'time':w_time, 'amount':w_amount, 'amount_btc':w_amount_btc, 'btc_price':w_btc_price}

	print('Summary files for deposits and withdraws saved in ' + output_dir)
	np.save(output_dir+'deposits.npy', dic_deposit)
	np.save(output_dir+'withdraws.npy', dic_withdraw)

	# return all these balances and time evolution
	return dic_deposit, dic_withdraw


# Return the values that were deposited or withdrawn for each asset along with 
# the time of the transaction, the amount transfered and its equivalent amount in btc at
# the time of the  transaction
def get_historical_depositswithdraws_v2(client, output_dir=''):

	# constantsupdate_history_symbol
#	dt=60000 # minimum time interval is 1 min (in ms)
	dt=interval_to_milliseconds('1d')
	
	# Get how much was deposited initially in the account
	deposits=client.get_deposit_history() # list how much has been deposited in all kind of currency
	Ndeposits=len(deposits['depositList'])
	
	d_assets=[]
	d_time=np.zeros(Ndeposits, dtype=np.long)
	d_amounts=np.zeros((Ndeposits,3), dtype=np.float)
	print('Getting the list of deposits...')
	print('    Total number of deposits: ' + str(Ndeposits))
	for p in range(Ndeposits):
		d_assets.append(deposits['depositList'][p]['asset'])
		d_time[p]=deposits['depositList'][p]['insertTime']
		d_amounts[p,0]=deposits['depositList'][p]['amount']
		if str.strip(d_assets[p]) != 'BTC':
			print('   ['+ str(p) +']' + ' Converting price using '+ d_assets[p]+'BTC' + ' conversion rate...')
			kline_tmp=client.get_historical_klines(d_assets[p]+'BTC', Client.KLINE_INTERVAL_1MINUTE, str(d_time[p]), str(d_time[p]+dt))
			#print(kline_tmp)
			if kline_tmp[0][1] != 0:
				d_amounts[p,2]=np.median(np.double(kline_tmp[0][1:5]))
				print('       Conversion rate: ', d_amounts[p,2])
			else:
				print('Error: returned value of the coin are 0!')
				print('Need debug. Program will exit now')
				exit()
			time.sleep(1)
		else:
			print('   ['+ str(p) +']' + ' Dealing with a deposit in BTC... no required conversion')
			d_amounts[p,2]=1.

		d_amounts[p,1]=d_amounts[p,0]*d_amounts[p,2]
	
#	inds=np.argsort(d_time)
#	u1=d_time[inds]
#	u2=np.array(d_assets)[inds]
#	u3=d_amounts[inds]
#	for i in range(len(u1)):
#		print('unstructured list of deposits:', u1[i], u2[i], u3[i])
#	exit()

	# Get how much was withdraw
	withdraws = client.get_withdraw_history()
	Nwithdraws=len(withdraws['withdrawList'])
	
	w_assets=[]
	w_time=np.zeros(Nwithdraws, dtype=np.long)
	w_amounts=np.zeros((Nwithdraws, 3), dtype=np.float)
	#w_fees=np.zeros(Nwithdraws)
	print('Getting the list of withdrawals...')
	print('    Total number of withdrawals: ' + str(Nwithdraws))
	for p in range(Nwithdraws):
		w_assets.append(withdraws['withdrawList'][p]['asset'])
		w_time[p]=withdraws['withdrawList'][p]['successTime']
		w_amounts[p,0]=withdraws['withdrawList'][p]['amount']
		#w_fees[p]=client.get_withdraw_fee(asset=w_assets[p])
		if str.strip(w_assets[p]) != 'BTC':
			print('   ['+ str(p) +']' + ' Converting price using '+ w_assets[p]+'BTC' + ' conversion rate...')
			kline_tmp=client.get_historical_klines(w_assets[p]+'BTC', Client.KLINE_INTERVAL_1MINUTE, str(w_time[p]), str(w_time[p]+dt))
			if kline_tmp[0][1] != 0:
				w_amounts[p,2]=np.median(np.double(kline_tmp[0][1:5]))
				print('       Conversion rate: ', w_amounts[p,2])
			else:
				print('Error: returned value of the coin are 0!')
				print('Need debug. Program will exit now')
				exit()
			time.sleep(0.5)
		else:
			print('   ['+ str(p) +']' + ' Dealing with a withdraw in BTC... no required conversion')
			w_amounts[p,2]=1.
		
		w_amounts[p,1]=w_amounts[p,0]*w_amounts[p,2]
	

	d_org_assets, d_org_amounts=sort_deposits_withdraws(d_time, d_assets, d_amounts)
	w_org_assets, w_org_amounts=sort_deposits_withdraws(w_time, w_assets, w_amounts)

	dic_deposit={'assets':d_org_assets, 'time':d_time, 'amount':d_org_amounts}
	dic_withdraw={'assets':w_org_assets, 'time':w_time, 'amount':w_org_amounts}

	print('Summary files for deposits and withdraws saved in ' + output_dir)

	np.save(output_dir+'deposits.npy', dic_deposit)
	np.save(output_dir+'withdraws.npy', dic_withdraw)

	# return all these balances and time evolution
	return dic_deposit, dic_withdraw

# Take outputs from deposit_withdraws of get_historical_depositswithdraws_v2() (an unstructured list of trades) 
# and organize them in a nice numpy 3D array that contains for each asset and at each epoch:
#       - values of all commission in BTC and in local value
# The function returns also the input time vector (the y dimension of the 3D array)
# and the asset names (the x dimension of the 3D array)
def sort_deposits_withdraws(time, asset_name, array2d):

	if len(time) != np.shape(array2d)[0]:
		print('Time and array of deposits/withdraws are not of the same size!')
		print('Cannot pursue. The program will exit now')
		exit()

	# Making a list of traded assets
	traded_assets=[]
	for e in asset_name:
		if e not in traded_assets:
			traded_assets.append(e)

	Ntradedassets=len(traded_assets)
	# Now we can make a grid that contains all required values
	trades=np.zeros((Ntradedassets, len(time),3)) + np.inf # For each asset, every time a transaction exist, stock the buy/sell (signed) val in (ind=0) btc and in (ind=1) local currency, and the commision in (ind=2) btc and in (ind=3) local currency
		
	for i0 in range(len(time)):
		pos=traded_assets.index(asset_name[i0])
		
		trades[pos,i0,0]=array2d[i0, 0] # val in local currency
		trades[pos,i0,1]=array2d[i0, 1] # val in btc
		trades[pos,i0,2]=array2d[i0, 2] # conversion rate at the time of the transaction
		
	return traded_assets, trades

# -----------------------------	

# Extract the list of coins and the combinations
# of symbols that available for trading
# Might not need to be run more than once every month
# Results of this function should be save on-disk
def get_trade_lists(client):

	# Load informations from the Binance Exchange platform
	exchange=client.get_exchange_info()
	timestamp=exchange['serverTime']
	# Get a full list of coin traded in Binance
	Nsymbols=len(exchange['symbols'])
	assets_list=[] # List of coins
	assets_tradelist=[]  # List of all tradable combinations
	for p in range(Nsymbols):
		tmp=exchange['symbols'][p]['baseAsset']
		if any(tmp in s for s in assets_list) == 0: # This look for the asset in the current list of asset... No need to list it if already in the list
			assets_list.append(tmp)
		assets_tradelist.append(exchange['symbols'][p]['symbol'])

	return assets_list, assets_tradelist, timestamp

# returns all current balances for all coins
def get_current_balances(assets_list, client):
	Nassets=len(assets_list) # Total number of coins available in Binance

	allbalances=np.zeros(Nassets)
	allbalances_status=np.zeros(Nassets) 
	pos_OK=[]
	for p in range(Nassets):
		tmp=client.get_asset_balance(asset=assets_list[p])
		allbalances[p]=tmp['free']
		if allbalances[p] != 0:
			print('   ['+str(i)+'] ' + str(len(allbalances[p])) + ' of balance found for '+ assets_list[p])
			allbalances_status[p]=1
			pos_OK.append(p)
	pos_OK=np.array(pos_OK, dtype=int)
	
	return allbalances[pos_OK]

# returns all traded assets along with the time of transaction,
# the amount and the equivalent amount in btc at the time of the transaction
# If the price in BTC required an interpolation, the uncertainty (computed as the stddev([low, high, open, close]) is also given
# The commission is also returned. Everything is in the form of lists
def get_historical_trades(assets_tradelist, assets_list, client, hist_directory, cadence, trades_dir):
	
	Nrequests=0
	
	silent=1
		
	Nassets=len(assets_tradelist) # Total number of symbols available in Binance

	# To assess which assets have ever have been traded, we could look at the balance of each coin
	# The used strategy consider that coins that were never traded should have exactly a 0 balance.
	# The problem is that we are then not able to access to past balances (prior first execution of the code)
	# An alternative approach is to look at all historical trades ever made on all possible asset combinations
	# Although more systematic (and thus robust), this might be way much slower as you have 400 tradable combinations
	# It is then easy to hit the 1200 operation/min allowed by the binance api
	i=0
	#trades=[]
	Ntrades=[]
	
	time=[]
	asset_name=[]
	deposit_withdraw=[]
	commission=[]
	
	# A. Sync with Binance
	# Download the data for all past transaction of all possible symbols
	# We convert all these into simpler to read lists: time, asset_name, deposit_withdraw, commission
	Nreq_avg=0
	t0_stamp=datetime.utcnow()
	t0_stamp=t0_stamp.timestamp()
	
	dt0=interval_to_milliseconds('1d')

	for p in range(Nassets):
		
		tmp=client.get_my_trades(symbol=assets_tradelist[p])
		#trades.append(tmp) # Keeping in json form all trades/asset 
		Ntrades.append(str(len(tmp))) # Keeping information about the number of trades/asset
		
		if len(tmp) !=0: # If there was trades in the past, collect past information about the coin

			print('   ['+str(i)+'] ' + str(len(tmp)) + ' trades found for '+ assets_tradelist[p])
			
			f=open('dbg/debug_TMP_' + str(assets_tradelist[p]) + '.txt', 'w')
			keys=['symbol', 'id', 'price', 'qty', 'commission', 'commissionAsset', 'time', 'isBuyer', 'isMaker', 'isBestMatch']
			for ii in range(len(tmp)):
				for jj in range(10):
					f.write(keys[jj] + ' ' + str( tmp[ii][keys[jj]] ) + '\n') 
				f.write('\n')
			f.close()
			f=open('dbg/debug_splittransaction_' + str(assets_tradelist[p]) + '.txt', 'w')

			#A.1 Get the klines using both data on disk and online
			tmin=str(int(tmp[0]['time']) - dt0) # PUT THE MIN TIMESTAMP GIVEN BY TMP
			tmax=str(int(tmp[-1]['time']) + dt0) # PUT THE MAX TIMESTAMP GIVEN BY TMP		
	
#			data,status,Nrequests=update_history_symbol(assets_tradelist[p], hist_directory+assets_tradelist[p], tmin, tmax, cadence, client, silent) # use a disk cache whenever possible
			data_symbol,status,Nrequests=load_history_symbol(symbol, hist_directory, tmin, tmax, cadence_str, client, silent) # use offline data for DEBUG

			#A.2 Take price of the trade and its amount to compute the expense in the traded currency : TMP using data ===> prices[0][:] 
			# We consider the general case XXX ---> YYY (buy YYY) or XXX <--- YYY (sell YYY)
			# Then the save pair XXXYYY will be used but:
			# XXX ---> YYY will have isBuyer=True
			# XXX <--- YYY will have isBuyer=False 
			# By convention, I will use NEGATIVE price for sell (isBuyer=False) and POSITIVE prices for buy (isBuyer=True)
			two_assets=get_asset_from_symbol(assets_list, assets_tradelist[p]) # Get the names for XXX and YYY
			f.write('two_assets: ')
			f.write(two_assets[0] + '   ')
			f.write(two_assets[1] + '\n')

			f.write('\n transaction:\n') 			
			for t in range(len(tmp)):
				transaction, fees=buysell_from_trade(tmp[t])
				# For XXX
				asset_name.append(two_assets[0])
				time.append(transaction[0,0])
				commission.append(fees)

				f.write('   \n time=' + str(transaction[0,0]) + '\n')
				f.write('   tr=  \n')
				for ii in range(len(transaction[:,0])):
					for jj in range(len(transaction[0,:])):
						f.write(str(transaction[ii,jj]))
						f.write('   ')
					f.write('\n')
				f.write('\n\n')
				
				ttt=condition_buysell(two_assets, transaction)
				lblXXX=['val('+two_assets[0]+')', 'val(BTC)' , 'val(ETH)', 'val(USDT)']
				lblYYY=['val('+two_assets[1]+')', 'val(BTC)' , 'val(ETH)', 'val(USDT)']
								
				f.write('XXX='+two_assets[0] +'\n')
				for iii in range(len(ttt)):
					f.write(lblXXX[iii] + '  ' + str(ttt[0][iii]) + '\n')			
				deposit_withdraw.append(ttt[0])
		
				asset_name.append(two_assets[1])
				time.append(transaction[1,0])
				commission.append(fees)
				
				f.write('YYY='+two_assets[1] +'\n')
				for iii in range(len(ttt[1])):
					f.write(lblYYY[iii] + '  ' + str(ttt[1][iii]) + '\n')			
				deposit_withdraw.append(ttt[1])
				
		
			f.write('\n\n\n\n')											
			f.close()
			i=i+1
		
		Nreq_avg, t0_stamp=time_control(Nrequests, Nreq_avg, t0_stamp)		
		
	# B. When necessary, convert the prices into BTC prices at the time of the transaction
	# Evaluate the btc price at the time of the transaction. Two possible strategies:
	# [1] Download the tick curve with some cadence (e.g. 15min) and interpolate at the time of 
	#     transaction (The 1min cadence would need some special care as it is too big data and takes too long for sync). 
	#	  The problem is that this might not be accurate as error propagation will occur
	#     when computing the total balance. The inaccuracy should be tested using the request for balance
	#     all_balances=client.get_account(). A Trick is needed to manage
	#	  problems of large data download (tick curve is highly resolved, e.g. cadence of 5min) or
	#     of accuracy
	# [2] The second solution would be to get price info only at the time of each trades. This solution 
	#     is extremely time consuming and might hit the limitation in operation per minutes if too
	#     many were done in the past
	# I choose solution [1], implemented in here...
	
	tmin=min(time)-dt0 # Use the oldest transaction time to know the data range to look at
	tmax=max(time)+dt0 # Use the newest transaction time to know the data range to look at
	
	print(' ')
	print('-----------------------------------------------')
	print('Converting values in BTC using linear interpolation...')
	print('-----------------------------------------------')
	
	Nreq_avg=0
	t0_stamp=datetime.utcnow()
	t0_stamp=t0_stamp.timestamp()
	#for a in assets_list:
	ind=0.
	for a in assets_list:
		print(' ['+str(round(ind+1))+'/' + str(len(assets_list)) + ']  Conversion for ' + a + '...')
		pos_asset=[i for i,x in enumerate(asset_name) if x==a] # returns a list with all positions for trades related to the asset 'a'
		if a !='BTC' and pos_asset != []:	
			#print('pos_asset=', pos_asset)
			if a != 'USDT':
				symbol_do=asset_name[pos_asset[0]] + 'BTC'
			else:
				symbol_do='BTCUSDT'	#asset_name[pos_asset[0]]	
					
			#data_symbol,status,Nrequests=update_history_symbol(symbol_do, hist_directory+symbol_do, tmin, tmax, cadence, client, silent) # download and/or read disk for YYYBTC klines
			data_symbol,status,Nrequests=load_history_symbol(symbol, hist_directory, tmin, tmax, cadence_str, client, silent) # use offline data for DEBUG
			Ndata=len(data_symbol)
			t=np.zeros(Ndata)
			p=np.zeros(Ndata)
			sig_p=np.zeros(Ndata)
			for i in range(Ndata):
				t[i]=(data_symbol[i][0]+data_symbol[i][6])/2. # mean time (average of open time and close time)
				#t[i]=np.double(data_symbol[i][0])
				p[i]=np.median(np.asarray(data_symbol[i][1:5], dtype='double')) # median price using the open, close, low, high price
				sig_p[i]=np.std(np.asarray(data_symbol[i][1:5], dtype='double')) # A very rough estimate of the standard deviation (might be overestimated)
			fm = interpolate.interp1d(t, p-sig_p) 
			fmed = interpolate.interp1d(t, p)
			fp = interpolate.interp1d(t, p+sig_p)
		
			tmp_time=np.zeros(len(pos_asset))
			for j in range(len(pos_asset)):
				tmp_time[j]=np.double(time[pos_asset[j]])
		
			cBTCmed=fmed(np.double(tmp_time))
			cBTCm=fm(np.double(tmp_time))
			cBTCp=fp(np.double(tmp_time))
			if a == 'USDT':
				cBTCmed=1./cBTCmed
				cBTCm=1./cBTCm
				cBTCp=1./cBTCp
		else:
			cBTCmed=1
			cBTCm=1
			cBTCp=1
		
		for j in range(len(pos_asset)):
			if deposit_withdraw[j][1] == -99999 and deposit_withdraw[j][0] != -99999: # Do we have already a BTC value for that coin? If no then convert				
					deposit_withdraw[j][1]=cBTCmed*deposit_withdraw[j][0] # The transfered median value in BTC
					deposit_withdraw[j][2]=cBTCm*deposit_withdraw[j][0] # median - 1 sigma error
					deposit_withdraw[j][3]=cBTCp*deposit_withdraw[j][0] # median + 1 sigma error
		
		Nreq_avg,t0_stamp=time_control(Nrequests, Nreq_avg, t0_stamp)
		ind=ind+1
		
	Ntrades=np.array(Ntrades, dtype=int)

	print('Done... Saving the unsorted deposit/withdraw/commission tables in numpy format...')
	
	np.save('tmp/time.npy', time)
	np.save('tmp/assetname.npy', asset_name)
	np.save('tmp/deposit_withdraw.npy', deposit_withdraw)
	np.save('tmp/commission.npy', commission)
	print('Done...')
	
	# --------
	# C. Format everything in a nice 3D numpy table
	# --------
	print(' ')
	print('-----------------------------------------------')
	print('Organizing into a nice numpy array (Matrix of buy/sell for all asset at any time...')
	print('-----------------------------------------------')
	traded_assets, time, trades_all=sort_buysell(time, asset_name, deposit_withdraw, commission)
	
	np.save(trades_dir+'traded_assets.npy', traded_assets)
	np.save(trades_dir+'time.npy', time)
	np.save(trades_dir+'trades_all.npy', trades_all)
	
	print('Done')
	
	return traded_assets, time, trades_all, Ntrades
# -----------------------------	


# returns all traded assets along with the time of transaction,
# the amount and the equivalent amount in btc at the time of the transaction
# If the price in BTC required an interpolation, the uncertainty (computed as the stddev([low, high, open, close]) is also given
# The commission is also returned. Everything is in the form of lists
def get_historical_trades_v2(assets_tradelist, assets_list, client, hist_directory, cadence, trades_dir, debug=True):

	Nrequests=0
	
	silent=1
		
	Nassets=len(assets_tradelist) # Total number of symbols available in Binance

	# To assess which assets have ever have been traded, we could look at the balance of each coin
	# The used strategy consider that coins that were never traded should have exactly a 0 balance.
	# The problem is that we are then not able to access to past balances (prior first execution of the code)
	
	# The alternative approach is to look at all historical trades ever made on all possible asset combinations
	# Although more systematic (and thus robust), this might be way much slower as you have 400 tradable combinations
	# It is then easy to hit the 1200 operation/min allowed by the binance api
	i=0
	#trades=[]
	Ntrades=[]
	
	time=[]
	asset_name=[]
	buysell=[]
	commission=[]
	
	# A. Sync with Binance
	# Download the data for all past transaction of all possible symbols
	# We convert all these into simpler to read lists: time, asset_name, buysell, commission
	Nreq_avg=0
	t0_stamp=datetime.utcnow()
	t0_stamp=t0_stamp.timestamp()
	
	dt0=interval_to_milliseconds('1d')

	for p in range(Nassets):
	#for p in range(1,3):
		Nrequests=Nrequests + 2

		tmp=client.get_my_trades(symbol=assets_tradelist[p])
		Ntrades.append(str(len(tmp))) # Keeping information about the number of trades/asset
		
		if len(tmp) !=0: # If there was trades in the past, collect past information about the coin

			print('   ['+str(i)+'] ' + str(len(tmp)) + ' trades found for '+ assets_tradelist[p])
			
			f=open('dbg/debug_TMP_' + str(assets_tradelist[p]) + '.txt', 'w')
			keys=['symbol', 'id', 'price', 'qty', 'commission', 'commissionAsset', 'time', 'isBuyer', 'isMaker', 'isBestMatch']
			for ii in range(len(tmp)):
				for jj in range(10):
					f.write(keys[jj] + ' ' + str( tmp[ii][keys[jj]] ) + '\n') 
				f.write('\n')
			f.close()
			f=open('dbg/debug_splittransaction_' + str(assets_tradelist[p]) + '.txt', 'w')

			#A Take price of the trade and its amount to compute the expense in the traded currency : TMP using data ===> prices[0][:] 
			# We consider the general case XXX ---> YYY (buy YYY) or XXX <--- YYY (sell YYY)
			# Then the save pair XXXYYY will be used but:
			# XXX ---> YYY will have isBuyer=True
			# XXX <--- YYY will have isBuyer=False 
			# By convention, I will use NEGATIVE price for sell (isBuyer=False) and POSITIVE prices for buy (isBuyer=True)
			two_assets=get_asset_from_symbol(assets_list, assets_tradelist[p]) # Get the names for XXX and YYY
			if debug == True:
				f.write('two_assets: ')
				f.write(two_assets[0] + '   ')
				f.write(two_assets[1] + '\n')
				f.write('\n transaction:\n') 

			for t in range(len(tmp)):
				#transaction, fees=buysell_from_trade(tmp[t])
				transaction=buysell_from_trade_v2(tmp[t])
				transaction_clearing=condition_buysell_v2(two_assets, transaction)
				# For XXX
				asset_name.append(two_assets[0])

				time.append(transaction[0,0])
				#commission.append(fees)
				buysell.append(transaction_clearing[0]) # DOING THIS PUT [PRICE_IN_XXX, PRICE_IN_BTC]
				
				# For YYY	
				asset_name.append(two_assets[1])
				time.append(transaction[1,0])
				#commission.append(fees)				
				buysell.append(transaction_clearing[1]) # DOING THIS PUT [PRICE_IN_YYY, PRICE_IN_BTC]

				if debug == True:
					f.write('   \n time=' + str(transaction[0,0]) + '\n')
					f.write('   tr=  \n')
					for ii in range(len(transaction[:,0])):
						for jj in range(len(transaction[0,:])):
							f.write(str(transaction[ii,jj]))
							f.write('   ')
						f.write('\n')
					f.write('\n\n')

					lblXXX=['val('+two_assets[0]+')', 'val(BTC)' , 'val(ETH)', 'val(USDT)']
					lblYYY=['val('+two_assets[1]+')', 'val(BTC)' , 'val(ETH)', 'val(USDT)']
									
					f.write('XXX='+two_assets[0] +'\n')
					for iii in range(len(transaction_clearing)):
						f.write(lblXXX[iii] + '  ' + str(transaction_clearing[0][iii]) + '\n')			

					f.write('YYY='+two_assets[1] +'\n')
					for iii in range(len(transaction_clearing[1])):
						f.write(lblYYY[iii] + '  ' + str(transaction_clearing[1][iii]) + '\n')			

			if debug == True:
				f.write('\n\n\n\n')											
				f.close()
		
			i=i+1
		
		Nreq_avg, t0_stamp=time_control(Nrequests, Nreq_avg, t0_stamp)		

	# --------
	# B. Adding interpolated values for trades without BTC information
	# --------
	print(' ')
	print('-----------------------------------------------')
	print('Converting values in BTC using linear interpolation...')
	print('-----------------------------------------------')
	buysell_new=interpolate_historical_trades_v2(time, buysell, assets_list, asset_name, client, hist_directory, cadence)

	buysell=buysell_new
	# --------
	# C. Format everything in a nice 3D numpy table
	# --------
	print(' ')
	print('-----------------------------------------------')
	print('Organizing into a nice numpy array (Matrix of buy/sell for all asset at any time...')
	print('-----------------------------------------------')

	time=np.array(time, dtype=np.long)
	Ntrades=np.array(Ntrades, dtype=np.long)

	traded_assets, trades_all=sort_buysell_v2(time, asset_name, buysell)

	print('Summary files for trades saved in ' + trades_dir)
	np.save(trades_dir+'traded_assets_nointerp.npy', traded_assets)
	np.save(trades_dir+'time_nointerp.npy', time)
	np.save(trades_dir+'trades_all_nointerp.npy', trades_all)
	np.save(trades_dir+'Ntrades_nointerp.npy', Ntrades)
	
	print('Done')

	return traded_assets, time, trades_all, Ntrades


def interpolate_historical_trades_v2(time, buysell, assets_list, asset_name_trades, client, hist_directory, cadence):
	# When necessary, convert the prices into BTC prices at the time of the transaction
	# Evaluate the btc price at the time of the transaction. Two possible strategies:
	# [1] Download the tick curve with some cadence (e.g. 15min) and interpolate at the time of 
	#     transaction (The 1min cadence would need some special care as it is too big data and takes too long for sync). 
	#	  The problem is that this might not be accurate as error propagation will occur
	#     when computing the total balance. The inaccuracy should be tested using the request for balance
	#     all_balances=client.get_account(). A Trick is needed to manage
	#	  problems of large data download (tick curve is highly resolved, e.g. cadence of 5min) or
	#     of accuracy
	# [2] The second solution would be to get price info only at the time of each trades. This solution 
	#     is extremely time consuming and might hit the limitation in operation per minutes if too
	#     many were done in the past
	# I choose solution [1], implemented in here...
	
	buysell_new=copy.deepcopy(buysell)
	
	dt0=interval_to_milliseconds('1d')

	silent=1

	tmin=min(time)-dt0 # Use the oldest transaction time to know the data range to look at
	tmax=max(time)+dt0 # Use the newest transaction time to know the data range to look at

	Nrequests=0
	Nreq_avg=0
	t0_stamp=datetime.utcnow()
	t0_stamp=t0_stamp.timestamp()
	#for a in assets_list:
	ind=0.
	for a in assets_list:
		print(' ['+str(round(ind+1))+'/' + str(len(assets_list)) + ']  Conversion for ' + a + '...')
		pos_asset=[i for i,x in enumerate(asset_name_trades) if x==a] # returns a list with all positions for trades related to the asset 'a'
		print('         ', pos_asset)
		print('   np.shape(assets_list)=', np.shape(assets_list))
		print('   np.shape(asset_name_trades)=', np.shape(asset_name_trades))
		print('   np.shape(buysell)=', np.shape(buysell))
		if a !='BTC' and pos_asset != []:	# Need to not be BTC, to have been traded, and to require interpolation in BTC
			print(len(pos_asset))
			replace=False
			for i in range(len(pos_asset)):
				if np.abs(buysell[pos_asset[i]][1]) == np.inf :
					replace=True
			if replace == True:
				#print('pos_asset=', pos_asset)
				if a != 'USDT':
					symbol_do=asset_name_trades[pos_asset[0]] + 'BTC'
				else:
					symbol_do='BTCUSDT'	#asset_name_trades[pos_asset[0]]	

				print('condition BTC , pos_assset and buysell fullfilled')
				data_symbol,status,Nrequests=update_history_symbol(symbol_do, hist_directory+symbol_do, tmin, tmax, cadence, client, silent) # download and/or read disk for YYYBTC klines
				#data_symbol,status,Nrequests=load_history_symbol(symbol_do, hist_directory+symbol_do, tmin, tmax, cadence, client, silent) # use offline data for DEBUG
				Ndata=len(data_symbol)
				t=np.zeros(Ndata)
				p=np.zeros(Ndata)
				sig_p=np.zeros(Ndata)
				for i in range(Ndata):
					t[i]=(data_symbol[i][0]+data_symbol[i][6])/2. # mean time (average of open time and close time)
					#t[i]=np.double(data_symbol[i][0])
					p[i]=np.median(np.asarray(data_symbol[i][1:5], dtype='double')) # median price using the open, close, low, high price
					sig_p[i]=np.std(np.asarray(data_symbol[i][1:5], dtype='double')) # A very rough estimate of the standard deviation (might be overestimated)
				fm = interpolate.interp1d(t, p-sig_p) 
				fmed = interpolate.interp1d(t, p)
				fp = interpolate.interp1d(t, p+sig_p)
		
				tmp_time=np.zeros(len(pos_asset))
				for j in range(len(pos_asset)):
					tmp_time[j]=np.double(time[pos_asset[j]])
		
				cBTCmed=fmed(np.double(tmp_time))
				cBTCm=fm(np.double(tmp_time))
				cBTCp=fp(np.double(tmp_time))
				if a == 'USDT':
					cBTCmed=1./cBTCmed
					cBTCm=1./cBTCm
					cBTCp=1./cBTCp
			#	print('cBTCmed:', cBTCmed)
			#	#print('Interpolation leads to np.inf...')
			#	print('tmin:', tmin, '  tmax:', tmax)
			#	print('data_tmin:', min(t), ' data_tmax:', max(t))
			#	print('data_med(min, max):', min(p), max(p))
			#	print('data_sig(min,max):', min(sig_p), max(sig_p))
			#if a == 'BTC':
			#	cBTCmed=1
			#	cBTCm=1
			#	cBTCp=1

				print('----------------')		
				for j in range(len(pos_asset)):
					if buysell_new[pos_asset[j]][1] == np.inf: #and buysell_new[j][0] != np.inf: # Do we have already a BTC value for that coin? If no then convert				
							buysell_new[pos_asset[j]][1]=cBTCmed[j]*buysell_new[pos_asset[j]][0] # The transfered median value in BTC
							#buysell_new[j][2]=cBTCm*buysell_new[j][0] # median - 1 sigma error
							#buysell_new[j][3]=cBTCp*buysell_new[j][0] # median + 1 sigma error
					if buysell_new[pos_asset[j]][0] == np.inf:
						print('Something weird: the value is inf on the local currency')
				
				for i in range(len(pos_asset)):
					print('     ', buysell[pos_asset[i]][1], '   =====>    ', buysell_new[pos_asset[i]][1])
				print('----------------')		

		Nreq_avg,t0_stamp=time_control(Nrequests, Nreq_avg, t0_stamp)
		ind=ind+1
		
	return buysell_new
# -----------------------------	


def buysell_from_trade_v2(trade):
	transaction=np.zeros((2,2)) # Values for asset XXX and YYY
	transaction[0,0]=np.double(trade['time']) # transaction[0,:] : Bought/sold XXX
	transaction[1,0]=np.double(trade['time']) # transaction[1,:] : Bought/sold YYY
	if trade['isBuyer']== True: #case of XXXYYY with: XXX ---> YYY
		transaction[0,1]=np.double(trade['qty']) # BUYING XXX IN UNIT OF XXX (the price in units of YYY is simply same as [1,1]
		transaction[1,1]=np.double(trade['price'])*np.double(trade['qty']) # Equivalent amount in YYY (price given in units of YYY)
	else:
		transaction[0,1]=-np.double(trade['qty'])  # SELLING XXX IN UNIT OF XXX
		transaction[1,1]=-np.double(trade['price'])*np.double(trade['qty']) # Equivalent amount in YYY IN UNITS OF YYY
	return transaction

# Function that help to organize the temporary vectors that define what is sold, what is bought
def condition_buysell_v2(two_assets, transaction):

	passed=0
	if two_assets[0] != 'BTC' and two_assets[1] != 'BTC':
		tXXX=[transaction[0, 1], np.inf] #  -99999]
		tYYY=[-transaction[1, 1], np.inf] # -99999]
		out=[tXXX,tYYY]
		passed=1
	
	if two_assets[0] != 'BTC' and two_assets[1] == 'BTC':
		tXXX=[transaction[0, 1], transaction[1, 1]]
		tYYY=[-transaction[1, 1], -transaction[1, 1]]
		out=[tXXX,tYYY]
		passed=2

	if two_assets[0] == 'BTC' and two_assets[1] != 'BTC':
		tXXX=[transaction[0, 1], transaction[0, 1]]
		tYYY=[-transaction[1, 1], -transaction[0, 1]]
		out=[tXXX,tYYY]
		passed=3

	if two_assets[0] == 'BTC' and two_assets[1] == 'BTC':
		print('XXX=BTC and YYY=BTC should never happen')
		passed=0

	if passed == 0:
		print('None of the valid conditions specified in condition_buysell was fulfilled. This is a bug.')
		print('Need serious debug... the program will exit now')
		exit()
	
#	print(two_assets)
#	print('passed in ', passed)
#	print('txxx=', tXXX)
#	print('tyyy=', tYYY)
	return out

# Take outputs from step B of get_historical_trades() (an unstructured list of trades) 
# and organize them in a nice numpy 3D array that contains for each asset and at each epoch:
#       - values of all commission in BTC and in local value
# The function returns also the input time vector (the y dimension of the 3D array)
# and the asset names (the x dimension of the 3D array)
def sort_buysell_v2(time, asset_name, buysell):#, commission):
	percent_com=2.5/100. # This function don't read commissions. It put a fiduciary value proportional to the buysell order

	tr_assets0=asset_name

	if len(time) != len(buysell):
		print('Time and buy/sell order list are not of the same size!')
		print('Cannot pursue. The program will exit now')
		exit()

	#f=open('dbg/debug_trades_numpy.txt', 'w')
	# Looking for the full list of assets that where traded at least once
	
	# Making a list of traded assets
	traded_assets=[]
	for e in asset_name:
		if e not in traded_assets:
			traded_assets.append(e)

	print('List of all traded_assets:', traded_assets)
	Ntradedassets=len(traded_assets)
	# Now we can make a grid that contains all required values
	trades=np.zeros((Ntradedassets, len(time),2)) + np.inf # For each asset, every time a transaction exist, stock the buy/sell (signed) val in (ind=0) btc and in (ind=1) local currency, and the commision in (ind=2) btc and in (ind=3) local currency
		
	for i0 in range(len(time)):
		pos=traded_assets.index(asset_name[i0])
		
		trades[pos,i0,0]=buysell[i0][0] # val in local currency
		trades[pos,i0,1]=buysell[i0][1] # val in BTC 		
#		trades[pos,i0,2]=percent_com*buysell[i0][0] #commission[i0][0] # commission in local currency
		
	return traded_assets, trades


'''
# Take a trade json structure and return (1) The timestamp of the transaction
#										 (2) A signed value telling us what was bought or sold (double)
#                                        (3) The name of the two assets that involved in the transaction 
#                                        (4) The commission value (double)
#                                        (5) The asset used for the commission
# assets_list is the full list of tradable assets
def buysell_from_trade(trade):
	transaction=np.zeros((2,2)) # Values for asset XXX and YYY
	transaction[0,0]=np.double(trade['time']) # transaction[0,:] : Bought/sold XXX
	transaction[1,0]=np.double(trade['time']) # transaction[1,:] : Bought/sold YYY
	if trade['isBuyer']== True: #case of XXXYYY with: XXX ---> YYY
		transaction[0,1]=np.double(trade['qty']) # BUYING XXX IN UNIT OF XXX (the price in units of YYY is simply same as [1,1]
		transaction[1,1]=np.double(trade['price'])*np.double(trade['qty']) # Equivalent amount in YYY (price given in units of YYY)
	else:
		transaction[0,1]=-np.double(trade['qty'])  # SELLING XXX IN UNIT OF XXX
		transaction[1,1]=-np.double(trade['price'])*np.double(trade['qty']) # Equivalent amount in YYY IN UNITS OF YYY
			
	commission=np.zeros(2) # Commission in BNB or in BTC
	if trade['commissionAsset'] == 'BNB':
		commission=[trade['commission'], -99999, -99999, -99999]
	if trade['commissionAsset'] == 'BTC':
		commission=[-1, trade['commission'], -99999, -99999]
	#if trade['commissionAsset'] != 'BNB' and trade['commissionAsset'] != 'BTC' and trade['commissionAsset'] != 'ETH':
	#	print('Something wrong in buysell_from_trade(trade)... The commission should always be either BNB or BTC')
	#	print('But found trade["commissionAsset"] =' + trade['commissionAsset']  + ' instead!')
	#	print('Need debug. The program will exit now')
	#	exit()
	if trade['commissionAsset'] != 'BNB' and trade['commissionAsset'] != 'BTC' :
		print("----------------------------------------------------------------------")
		print("WARNING: trade['commissionAsset'] =", trade['commissionAsset'], ' found... NO YET IMPLEMENTED')
		print("----------------------------------------------------------------------")
	return transaction, commission


# Function that help to organize the temporary vectors that define what is sold, what is bought
def condition_buysell(two_assets, transaction):

	passed=0
	if two_assets[0] != 'BTC' and two_assets[1] != 'BTC':
		tXXX=[transaction[0, 1], -99999, -99999, -99999]
		tYYY=[transaction[1, 1], -99999, -99999, -99999]
		out=[tXXX,tYYY]
		passed=1
	
	if two_assets[0] != 'BTC' and two_assets[1] == 'BTC':
		tXXX=[transaction[0, 1], transaction[1, 1], -99999, -99999]
		tYYY=[transaction[1, 1], transaction[1, 1], -99999, -99999]
		out=[tXXX,tYYY]
		passed=1

	if two_assets[0] == 'BTC' and two_assets[1] != 'BTC':
		tXXX=[transaction[0, 1], transaction[0, 1], -99999, -99999]
		tYYY=[transaction[1, 1], transaction[0, 1], -99999, -99999]
		out=[tXXX,tYYY]
		passed=1

	if two_assets[0] == 'BTC' and two_assets[1] == 'BTC':
		print('XXX=BTC and YYY=BTC should never happen')
		passed=0

	if passed == 0:
		print('None of the valid conditions specified in condition_buysell was fulfilled. This is a bug.')
		print('Need serious debug... the program will exit now')
		exit()
	
	return out
'''


'''
# Take outputs from step B of get_historical_trades() (an unstructured list of trades) 
# and organize them in a nice numpy 3D array that contains for each asset and at each epoch:
# 		- values of all buys and sells in BTC and in local value
#       - values of all commission in BTC and in local value
# The function returns also the input time vector (the y dimension of the 3D array)
# and the asset names (the x dimension of the 3D array)
def sort_buysell(time, asset_name, buysell, commission):
	tr_assets0=asset_name

	#f=open('dbg/debug_trades_numpy.txt', 'w')
	# Looking for the full list of assets that where traded at least once
	
	# Making a list of traded assets
	traded_assets=[]
	for e in asset_name:
		if e not in traded_assets:
			traded_assets.append(e)

	Ntradedassets=len(traded_assets)
	# Now we can make a grid that contains all required values
	trades=np.zeros((Ntradedassets, len(time), 6)) # For each asset, every time a transaction exist, stock the buy/sell (signed) val in (ind=0) btc and in (ind=1) local currency, and the commision in (ind=2) btc and in (ind=3) local currency
		
	for i0 in range(len(time)):
		pos=traded_assets.index(asset_name[i0])
		
		trades[pos,i0,0]=buysell[i0][1] # val in btc
		trades[pos,i0,1]=buysell[i0][0] # val in local currency
		trades[pos,i0,2]=commission[i0][1] # commission in btc
		trades[pos,i0,3]=commission[i0][0] # commission in local currency
		trades[pos,i0,4]=buysell[i0][2] # med-1sig in btc
		trades[pos,i0,5]=buysell[i0][3] # med+1sig in btc
		
	return traded_assets, time, trades
'''

# A function that gets a raw json list and organize it into nice numpy arrays
# All is embedeed into a dictionary
def convert_jsondata2nparray(data):

	Ndata=len(data)
	time=np.zeros((Ndata,2), dtype=np.long) # Open and close time
	prices=np.zeros((Ndata,4), dtype=np.float) # Open, high, low, close price
	volumes=np.zeros(Ndata, dtype=np.float)  # Transaction Volume
	ntrades=np.zeros(Ndata, dtype=np.long) # Number of trades
	quotevols=np.zeros(Ndata, dtype=np.float) # Quote asset volume
	takerbasevols=np.zeros(Ndata, dtype=np.float) # Taker buy base asset volume
	takerquotevols=np.zeros(Ndata, dtype=np.float) # Taker buy quote asset volume
	
	for i in range(Ndata):
		time[i,0]=data[i][0]
		time[i,0]=data[i][6]
		prices[i,:]=data[i][1:4]
		volumes[i]=data[i][5]
		quotevols[i]=data[i][7]
		ntrades[i]=data[i][8]
		takerbasevols[i]=data[i][9]
		takerquotevols[i]=data[i][10]

	dic={'time':time, 'prices':prices, 'volumes':volumes, 'quotevols':quotevols, 'ntrades':ntrades, 'takerquotevols':takerquotevols, 'takerbasevols':takerbasevols}

	return dic

# This function use a trade list to calculate how the balance of
# each coin evolved overtime. Will typcially use outputs provided by: get_historical_trades(assets_tradelist, assets_list, client, hist_directory, cadence)
def compute_historical_balances(time, asset_name, commission, buysell):

				
	return 0
	
	
# Function that update the deposit/withdraws list 
# by only sending requests for new transactions
def update_historical_depositswithdraws(dic_d, dic_w, client):

	return 0

	
# function that decides if we need to refresh the list
# if the data were written too long ago
# returns whether the file was refreshed
def update_tradablelist_binance_file(file_assets, file_symbols, check_period, client):

	do_write=0
	try:
		#print('Trying to read ' + file_assets)
		f=open(file_assets, 'r')
		#print('Trying to read ' + file_symbols)
		f2=open(file_symbols, 'r')
		
		timestamp=f.readlines() # The first line contains the timestamp in ms
		timestamp=int(timestamp[0])/1e3 # convert to integer and in seconds
		timenow=datetime.utcnow()
		timenow_s=int(timenow.timestamp())
		
		print(timenow_s - timestamp)
		print(check_period)
		print((timenow_s - timestamp) >= check_period)
		if (timenow_s - timestamp) >= check_period:
			print('Files listing Binance assets are too old... refreshing them')
			do_write=1
	except IOError:
		print('Files listing Binance assets not found... Creating them')
		do_write=1
	
	
	if do_write == 1:
		assets_list, assets_tradelist, timestamp=get_trade_lists(client) # Might need to be run only once a month (need to save it on disk however)
		usdt=[i for i,x in enumerate(assets_list) if x=='USDT']
		if usdt == []:
			assets_list.append('USDT')
			
		f=open(file_assets, 'w')
		f.write(str(timestamp) + '\n')
		for i in range(len(assets_list)):
			stri=str(assets_list[i]) +'\n'
			f.write(stri)
		f.close()	
		f=open(file_symbols, 'w')
		f.write(str(timestamp) + '\n')
		for i in range(len(assets_list)):
			stri=str(assets_tradelist[i])  +'\n'
			f.write(stri)
		f.close()	
		
		print(assets_list)

	else:
		print('Files are up-to-date. No need to refresh them')
		
	return do_write
	
def read_tradablelist_binance_file(file_assets, file_symbols):
	
	f=open(file_assets, 'r')
	tmp=f.readlines()
	timestamp=int(tmp[0])
	f.close()
	assets_list=[]	
	for p in range(len(tmp)-1):
		assets_list.append(tmp[p+1].rstrip())
	
	#print(assets_list)
	
	f=open(file_symbols, 'r')
	tmp=f.readlines()
	assets_tradelist=[]	
	for p in range(len(tmp)-1):
		assets_tradelist.append(tmp[p+1].rstrip())
	f.close()	
			
	#print(assets_tradelist)

	return assets_list, assets_tradelist, timestamp

def get_history_prices(t0, tmax, symbol, cadence, client):
##    1499040000000,      # Open time
##    "0.01634790",       # Open
##    "0.80000000",       # High
##    "0.01575800",       # Low
##    "0.01577100",       # Close
##    "148976.11427815",  # Volume
##    1499644799999,      # Close time
##    "2434.19055334",    # Quote asset volume
##    308,                # Number of trades
##    "1756.87402397",    # Taker buy base asset volume
##    "28.46694368",      # Taker buy quote asset volume
##    "17928899.62484339" # Ignore
    
	if(cadence == '1min'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, t0, tmax)
	if(cadence == '3min'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_3MINUTE, t0, tmax)
	if(cadence == '5min'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_5MINUTE, t0, tmax)
	if(cadence == '15min'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_15MINUTE, t0, tmax)
	if(cadence == '30min'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_30MINUTE, t0, tmax)
	if(cadence == '1h'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1HOUR, t0, tmax)
	if(cadence == '2h'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_2HOUR, t0, tmax)
	if(cadence == '4h'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_4HOUR, t0, tmax)
	if(cadence == '6h'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_6HOUR, t0, tmax)	
	if(cadence == '8h'):
			klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_8HOUR, t0, tmax)
	if(cadence == '12h'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_12HOUR, t0, tmax)
	if(cadence == '1day'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY, t0, tmax)
	if(cadence == '3day'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_3DAY, t0, tmax)
	if(cadence == '1week'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1WEEK, t0, tmax)
	if(cadence == '1month'):
		klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MONTH, t0, tmax)
	return klines
	

# This function (1) look if there is a file with data on values of a given symbol
#               (2) update it if it exist, so that we have data between tmin and tmax
#				(3) create it otherwise and write data from tmin and tmax at cadence 
def update_history_symbol(symbol, hist_directory, tmin, tmax, cadence_str, client, silent):

	Nrequests=0
	
	tmin=int(tmin)
	tmax=int(tmax)

	# Look for a file
	files=glob.glob(hist_directory+'/Binance_'+symbol+'_' + cadence_str + '_*.json')

	#print('syntax: ', hist_directory+'/Binance_'+symbol+'_' + cadence_str + '_*.json')
    # Case we don't find anything that matches the syntax...
	if len(files) == 0:
		if silent == 0:
			print('No existing file... Data will be downloaded, starting at date: ' + str(tmin) + '... ending date: ' + str(tmax)) 
		nofile=1
	else:
		if len(files) > 1:
			print('Warning: Multiple saved files found for the pair ' + symbol + ' and for the cadence' +cadence_str +'!')
			print ('        Please check the present files and possibly erase them or move them out of the current directory...')
			print('Information for debug:')
			print('         Filenames :')
			print(files)
			print('         Directory :' + hist_directory)
			print('         Cadence   :' + cadence_str)
			print('         Symbol    :' + symbol)
			print('The program will exit now')
			exit()
    # Case we found a single file that match the syntax...	
		if len(files) == 1:
			if silent == 0:
				print('Found a file... Updating existing file')
			file=files[0]
			nofile=0

	# If a proper history file was found...
	fileupdated=0 # Let us now if the file was modified or not
	if nofile == 0:
		#tmp=file.split('_')
		#timestamps_file=tmp[-1].split('.')[0].split('-') # get t0 and t1... used to properly refresh the file
		with open(file, "r") as read_file:
			data = json.load(read_file)
	
		timestamps=[int(data[0][0]), int(data[-1][0])] # Better to read the data than taking the filename... in case there is some divergence...
				
		if timestamps[0] > tmin: # Case there is missing data before the minimum time
			# We need to download data starting at tmin and finishing at timestamps[0]
			newdata=get_history_prices(str(tmin), str(timestamps[0]), symbol, cadence_str, client)
			Nrequests=Nrequests+5 # I suspect that the function is actually making 4 request and not 1...
			# Then insert the downloaded block at the beginning of the data block
			if (len(newdata) != 0):
				istart=0
				while newdata[istart][0] < timestamps[0]:
					istart=istart+1
				if (istart !=0): # or istart < len(newdata): # Insert data before, only if there was effectively new data to insert
					for i in range(istart):
						data.insert(0, newdata[istart-i-1]) # need to insert backward to preserve timeline
					fileupdated=2
					
		if timestamps[1] < tmax: # Case there is missing data at the end
			# We need to download data starting at timestamps[1] and finishing at tmax
			newdata=get_history_prices(str(timestamps[1] + 1), str(tmax), symbol, cadence_str, client)
			Nrequests=Nrequests+5 # I suspect that the function is actually making 4 request and not 1...
			# Then insert the downloaded block at the end of the data block
			if (len(newdata) != 0):
				for d in newdata:
					data.append(d)
				fileupdated=3
    	
    	# Delete the old file with partial data
		if fileupdated >= 2 :
			os.remove(file)
   
	else: # else there was no data file
		# We need to download data starting at tmin and finishing at tmax
		timestamps=[tmin, tmax]
		data=get_history_prices(str(tmin), str(tmax), symbol, cadence_str, client)
		Nrequests=Nrequests+5 # I suspect that the function is actually making 4 request and not 1...
		if data != []: # Only if there is data, then we can write it in a file...
			fileupdated=1
			#print('No file =1 and data in time interval ... full download')
		
	# Finally save the updated data block on disk, if required
	if fileupdated >= 1:
		save_data_json(data, symbol, str(timestamps[0]), str(timestamps[1]), cadence_str, hist_directory)
 
	return data, fileupdated, Nrequests


# Usefull if we just want to load offline data. No internet connection required.
# The function returns the data in a json format if the file exists
# otherwise, it returns an empty list
def load_history_symbol(symbol, hist_directory, tmin, tmax, cadence_str, client, silent):
	
	tmin=int(tmin)
	tmax=int(tmax)

	# Look for a file
	files=glob.glob(hist_directory+'/Binance_'+symbol+'_' + cadence_str + '_*.json')

	#print('syntax: ', hist_directory+'/Binance_'+symbol+'_' + cadence_str + '_*.json')
    # Case we don't find anything that matches the syntax...
	if len(files) == 0:
		if silent == 0:
			print('No existing file... Cannot load data for the symbol: ' + symbol) 
		nofile=1
	else:
		if len(files) > 1:
			print('Warning: Multiple saved files found for the pair ' + symbol + ' and for the cadence' +cadence_str +'!')
			print ('        Please check the present files and possibly erase them or move them out of the current directory...')
			print('Information for debug:')
			print('         Filenames :')
			print(files)
			print('         Directory :' + hist_directory)
			print('         Cadence   :' + cadence_str)
			print('         Symbol    :' + symbol)
			print('The program will exit now')
			exit()
    # Case we found a single file that match the syntax...	
		if len(files) == 1:
			if silent == 0:
				print('Found a file... loading existing file')
			file=files[0]
			nofile=0

	# If a proper history file was found...
	if nofile == 0:
		with open(file, "r") as read_file:
			data = json.load(read_file)
	   
	else: # else there was no data file
		data=[]
 
	fileupdated=0
	Nrequests=0
	return data, fileupdated, Nrequests


# Save on disk a formated json file using 
# a specific syntax that depends on the symbol and the time interval 
# NOT WORKING DUE TO THE FACT THAT JSON FORMAT HAS A LAST } CHARACTER...
def save_data_json(data, symbol, start, end, interval, hist_directory):
	write_type='w'
	with open(
	    hist_directory+"/Binance_{}_{}_{}-{}.json".format(
	        symbol, 
	        interval, 
	        date_to_milliseconds(start),
	        date_to_milliseconds(end)
	    ),
	    write_type # set file write mode
	) as f:
		f.write(json.dumps(data))


def current_prices(verbose):
	prices = client.get_all_tickers()
	values=np.empty(len(prices))
	i=0
	for p in prices:
		if (i==0): 
			symbols=p['symbol']
		else:
			symbols=[symbols, p['symbol']]
		values[i]=p['price']
		if(verbose == 1):
			print('Symbol: ' + p['symbol'] + '  Price:' + p['price'])
		i=i+1
	return (symbols, values)



# Find a file within a path that match a specific pattern
def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result
    

# Provided a list of traded assets (assets_list), 
# identify the two assets that are named in the variable 'symbol'
def get_asset_from_symbol(assets_list, symbol):
	
	nfirst=0
	nlast=0
	for i in assets_list:
		p=symbol.find(i)
		#if p == -1:
		#	print(i + ' not found...')
		if p == 0:
			#first=p
			nfirst=nfirst+1
		if p >= 2:
			last=p
			nlast=nlast+1
		if p > 0 and p < 2:
			print(' Something wrong in get_asset_from_symbol(assets_list, symbol)... assets should have at least 3 characters')
			
	if nfirst == 1 and nlast == 1: # We want to be sure that only one combination exists
		assets=[symbol[0:last], symbol[last:]]
	else: # Otherwise, send an error message
		print('Something wrong in get_asset_from_symbol(assets_list, symbol)... multiple assets seems to match the string... Need serious debuging')
		print('nfirst=', nfirst, ' nlast=', nlast)
		print('symbol = ', symbol)
		print(symbol[0:last], symbol[last:])
		print('The program will exit now')
		
		exit()
  	
	return assets
    
    
def date_to_milliseconds(date_str):
    """Convert UTC date to milliseconds
    If using offset strings add "UTC" to date string e.g. "now UTC", "11 hours ago UTC"
    See dateparse docs for formats http://dateparser.readthedocs.io/en/latest/
    :param date_str: date in readable format, i.e. "January 01, 2018", "11 hours ago UTC", "now UTC"
    :type date_str: str
    """
    # get epoch value in UTC
    epoch = datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)
    # parse our date string
    d = dateparser.parse(date_str)
    # if the date is not timezone aware apply UTC timezone
    if d.tzinfo is None or d.tzinfo.utcoffset(d) is None:
        d = d.replace(tzinfo=pytz.utc)

    # return the difference in time
    return int((d - epoch).total_seconds() * 1000.0)


def interval_to_milliseconds(interval):
    """Convert a Binance interval string to milliseconds
    :param interval: Binance interval string 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w
    :type interval: str
    :return:
         None if unit not one of m, h, d or w
         None if string not in correct format
         int value of interval in milliseconds
    """
    ms = None
    seconds_per_unit = {
        "m": 60,
        "h": 60 * 60,
        "d": 24 * 60 * 60,
        "w": 7 * 24 * 60 * 60
    }

    unit = interval[-1]
    if unit in seconds_per_unit:
        try:
            ms = int(interval[:-1]) * seconds_per_unit[unit] * 1000
        except ValueError:
            pass
    return ms

def time_control(Nreq, Nreq_avg, t0_stamp):

	check_interval=20
	vmax_binance=1200./2.

	t=datetime.utcnow()
	dt=(t.timestamp() -t0_stamp) # minutes
	#print(dt, Nreq_avg)				
	if dt < check_interval: # e.g. check every 20 seconds 
		Nreq_avg=Nreq+Nreq_avg
	else:
		v=Nreq_avg/dt*60. # transaction/minutes
		vmax=vmax_binance*0.4 # Maximum allowed transaction rate per minutes (binance limit this to 1200)
		if v > vmax or v < 100:
			print('Transaction speed: ', v, ' vs max allowed speed ', vmax)
		if v > vmax:
			dtr=vmax/dt # maximum number of transaction during a dt (sec) laps 
			dt_sleep=4.*math.ceil(dtr/(v-vmax)) # time in second required to sleep in order to avoid to hit the limit
			time.sleep(dt_sleep)
			#print('Binance has a limit of 1200 transactions/minute... We nearly reached this... Need to sleep a bit to avoid ban')
			print('Time spend on sleep: ', dt_sleep)
					
		Nreq_avg=0
		t0_stamp=datetime.utcnow()
		t0_stamp=t0_stamp.timestamp() # in s

	return Nreq_avg, t0_stamp