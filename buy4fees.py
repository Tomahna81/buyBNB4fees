# Use the binance client available at https://github.com/sammchardy/python-binance
# Nicely done help available at: https://python-binance.readthedocs.io/en/latest/market_data.html

import numpy as np
from binance.client import Client
import gzip
import time, sys
import os, errno
from datetime import datetime
import os.path
from os import path
import json # to dump json structure into log files

def eval_asset_qty(client, pair, Pcurrent, balance, cost_Ntr0, Flimit=0.02, period=3, Nsigma=3):
	''' This function calculate the quantity to buy by 
		(1) Taking a given period (eg. 3 months) in months,  
		(2) Determining the sigma and median price over that period
		(4) We define a curve like this to evaluate the quantity q to buy, vs price:
		     q
			 |---------+ (Pmin, qmax(cost_Ntrmax))
			 |			+
			 |			 +
			 |			  +
			 |			   + (Pmed, qmin(cost_Ntr0))
			 |			    + ----------
			 |----------|----|-------------> Price
			           Pmin  Pmed       
		Ntr0 (definition): The minimum number of transaction made possible by the buy. This is not
			  a variable here, its nomination is important as it fix the total cost for the buy
		cost_Ntr0 (input): The total amount to be bought associated to Ntr0 
		cost_Ntrmax (definition): This is the related cost to qmax
		qmax (definition): Quantity to be bought at most
		balance (input): Balance of the asset used to buy (e.g. USDT or BTC)
		Flimit (input): maximal Fraction of the balance that we will buy for that asset 
	'''
	print('---------------')
	print(' pair      :', pair)
	print(' Pcurrent  :', Pcurrent)
	print(' Balance   :', balance)
	print(' cost_Ntr0 :', cost_Ntr0)
	print(' Flimit    :', Flimit)
	print(' period    :', period)
	print(' Nsigma    :', Nsigma)
	error=False
	# Take the last period months, excluding the current month (as it is not closed yet)
	stats_pair = client.get_klines(symbol=pair, interval=client.KLINE_INTERVAL_1MONTH, limit=period+1)
	#Pcurrent=client.get_avg_price(symbol=pair)
	#Pcurrent=np.double(Pcurrent['price'])
	l=[]
	for i in range(0, period):
		for j in range(1,5):
			l.append(stats_pair[i][j])
	Pmed=np.median(np.double(l))
	Psigma=np.std(np.double(l))
	Pmin=Pmed - Nsigma*Psigma # Place the Pmin in terms of standard deviation instead than in terms of min ==> More robust
	#Pmin=np.min(np.double(stats_pair[1:][3]))
	if Pcurrent >= Pmed:
		q=cost_Ntr0/Pcurrent
		print('In the upper price range, q=', q)
	if Pcurrent >= Pmin and Pcurrent <=Pmed:
		qmin=cost_Ntr0/Pcurrent
		qmax=balance*Flimit/Pmin
		a=(qmax-qmin)/(Pmin-Pmed)
		b=qmin-a*Pmed
		q=a*Pcurrent + b
		print('In the linear regime, q=', q)
		print(' qmin=', qmin)
		print(' qmax=', qmax)
		print(' a=', a)
		print(' b=', b)
	if Pcurrent <= Pmin:
		q=balance*Flimit/Pmin
		print('In the low price range, q=', q)
	# Safety
	if Pcurrent*q > balance*Flimit:
		print('Warning: The calculation led to a higher quantity than the allowed quantity by Flimit and balance')
		print('         We will cap it to balance*Flimit')
		q=balance*Flimit/Pcurrent
	if cost_Ntr0 > balance*Flimit:
		print('Error: The minimum amount to be used exceeds the alowed balance*Flimit limit amount')
		print('       No transaction can be performed')
		error=True
	print('----------------')
	return q, error

def data_stream(file_noextension, timestamp, balance_asset_A, balance_asset_B, balance_asset_ref, pair, asset_qty, pair_AB, pair_Aref, orders_open_check_Aref, orders_open_check_AB, Nmaxtrades, offset_price, mean_price_pair, limit_order_timeout, status_order,status_cancel ):				
		orders_in_Aref=len(orders_open_check_Aref)
		orders_in_AB=len(orders_open_check_AB)		
		test=path.exists(file_noextension + ".log")
		f=open(file_noextension + ".log", "a+")
		if test == False:
			header='#timestamp         pair     asset_qty offset_price   mean_price   Nmaxtrades  status_cancel  status_order  balance_asset_A   balance_asset_B   balance_asset_ref   orders_in_AB   orders_in_Aref   limit_order_timeout \n'
			f.write(header)
		stri='{0}      {1}  {2:.8f}     {3:.8f}   {4:.8f}   {5:f}   {6:10d}    {7:10d}   {8:.8f}    {9:.8f}   {10:.8f}    {11:d}    {12:d}   {13}'.format(round(timestamp), pair, asset_qty, offset_price, mean_price_pair, Nmaxtrades, round(status_cancel), round(status_order), balance_asset_A, balance_asset_B, balance_asset_ref, orders_in_AB, orders_in_Aref, limit_order_timeout)
		f.write(stri +'\n')
		f.close()
		if orders_in_Aref >0:
			file_orders=file_noextension + '_' + str(timestamp) + '_Aref.log'
			f=open(file_orders, "w")
			f.write("# Open order for the pair: " + str(pair_Aref))
			f.close()
			with open(file_orders, 'a+') as outfile:
				json.dump(orders_open_check_Aref, outfile)
		if orders_in_AB >0:
			file_orders=file_noextension + '_' + str(timestamp) + '_AB.log'
			f=open(file_orders, "w")
			f.write("# Open order for the pair: " + str(pair_AB))
			f.close()
			with open(file_orders, 'a+') as outfile:
				json.dump(orders_open_check_AB, outfile)	
		return 0

def get_precision_from_binance(client, pair):
	''' Give the precision set by binance for a given pair
	'''
	info=client.get_symbol_info(pair)
	return info['baseAssetPrecision']

def apply_filter_conditions(client, pair, value, qty, Nprecision, tolerance=0.01, verbose=True):
	''' Binance imposes that submitted order are not too far from 
		the current average price. The limits are imposed by diferent
		filters. 
		The current function (1) go through all those filters, 
		(2) check that it matches the Binance requirements and,
		(3) (a) if it is the casereturn the value=value field
            (b) if it is not the case, return the value field
            	after limiting to the lower or upper allowed bound
        In all cases, a boolean (the variable filtered) is returned
        that specify whether the limitation was enforced or not
        (4) I also return a flag variable that is set to 
        	(a) 'OK' if the price below current price*(1 + tolerance) (in fraction of percent) 
        	(b) or 'WARNING' if it is above. This flag is a safety to by pass 
        	    any order placement if the limit order is too high (would mean a bug somewhere)
	'''
	error_increment=10**-Nprecision # used to avoid to be rounding too low or too high.
	old_value=value
	old_qty=qty
	if isinstance(value, str):
		value=np.double(value)
	if isinstance(qty, str):
		qty=np.double(qty)
	info=client.get_symbol_info(pair)
	filters=info['filters']
	filtered=False
	# Modify price in order  to pass price-associated filters of Binance
	for f in filters:
		if f['filterType'] == 'PRICE_FILTER':
			if value >  np.double(f['maxPrice']):
				value = np.double(f['maxPrice']) #- error_increment
				if verbose == True:
					print('          PRICE_FILTER Applied. Value caped using maxPrice: ',  'old value: ', old_value, '  new value: ', value)
				filtered=True
			if value <  np.double(f['minPrice']):
				value = np.double(f['minPrice'])  #+ error_increment
				if verbose == True:
					print('          PRICE_FILTER Applied. Value caped using minPrice: ', f['minPrice'])
				filtered=True
			# Ticksize acts as a minumum resolution. We have to ensure that the price matches the resolution constraint
			# As we pass on the fitlers, we get the necessary information to enforce that rule at the end of this routine
			resol_val=np.double(f['tickSize'])
		if f['filterType'] == 'PERCENT_PRICE':
			avgprice=client.get_avg_price(symbol=pair) # Get the average price over 5 last mins
			if avgprice['mins'] == np.double(f['avgPriceMins']):
				weightedavgprice=np.double(avgprice['price'])
				if value > np.double(f['multiplierUp'])*weightedavgprice:
					value=np.double(f['multiplierUp'])*weightedavgprice  #- error_increment
					if verbose == True:
						print('          PERCENT_FILTER Applied. Value caped using multiplierUp and weightedavgprice. old value: ', old_value, '  new value: ', value)
					filtered=True
				if value < np.double(f['multiplierDown'])*weightedavgprice:
					value=np.double(f['multiplierDown'])*weightedavgprice  #+ error_increment
					if verbose == True:
						print('          PERCENT_FILTER Applied. Value caped using multiplierUp and weightedavgprice. old value: ', old_value, '  new value: ', value)
					filtered=True
			else:
				print('ERROR: The average provided by the two binance function (get_avg_price and  and get_symbol_info)')
				print('       Is not performed on the same timescale. The filters cannot be enforced')
				print('       Likely a problem on Binance side. The program will exit now')
				sys.exit()
	#if round(Q)%1 !=0:
	Q=value/resol_val # How many ticks for the decided value? Need to round this after all the filters were applied
	value=np.ceil(Q)*resol_val # We take a slightly upper value
	if verbose == 1:
		print('          PRICE_FILTER Applied. value rounded to match allowed tickSize =', resol_val, '  old value', old_value, ' new value:', value) 
	# After having adjusted prices, check if the minimum notional (the quantity * value) is sufficient to pass the MIN_NOTIONAL value from Binance
	for f in filters:
		if f['filterType'] == 'MIN_NOTIONAL':
			avgprice=client.get_avg_price(symbol=pair) # Get the average price over 5 last mins
			if avgprice['mins'] == np.double(f['avgPriceMins']):
				if value*qty < np.double(f['minNotional']):
					qty=np.double(f['minNotional'])/value
					if verbose == True:
						print('          MIN_NOTIONAL filter APPLIED. qty adjusted to pass the minNotional filter. old qty:', old_qty, '  new qty: ', qty)
					filtered=True
	# Filter on Quantity conditions
	for f in filters:
		if f['filterType'] == 'LOT_SIZE':
			resol_qty=np.double(f['stepSize'])
			Q=qty/resol_qty
			qty=np.ceil(Q)*resol_qty
			if verbose == 1:
				print('          LOT_SIZE filter APPLIED. qty rounded to match allowed stepSize =', f['stepSize'], '  new qty:', qty)
	# Safety check: Do we place an order that is below current price*(1 + tolerance)?
	avgprice=client.get_avg_price(symbol=pair) # Get the average price over 5 last mins
	avgprice=np.double(avgprice['price'])
	if value <= avgprice*(1. + tolerance):
		flag='OK'
	else:
		flag='WARNING'
	return value, qty, filtered, flag

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

def eval_offsetprice(balance_asset, balance_asset_ref, max_fees, delta_change_pair, offsets_percent):
	'''
	This function determine the number of possible trades (Nmaxtrades) in function of the available quantity of paying fees (balance_asset)
	and of the quantity of the traded asset (balance_asset_ref). 
	max_fees defines the cost of a single transaction
	offsets_percent is a 5-element list that contain the configuration for determining how low the buy the limit order price offset relative to
	the current price should be.
	***Warning: The units for balance_asset and balance_asset_ref must be the same (e.g. usdt)***
	'''
	verbose=1
	# Evaluate the maximum number of possible trades using either asset_A or asset_B, depending on which position is the heaviest...
	if balance_asset_ref !=0 and max_fees !=0:
		Nmaxtrades=balance_asset/(balance_asset_ref*max_fees) # How many trades are possible at most with the current bnb amount
	else:
		Nmaxtrades=10000
	if Nmaxtrades < 1: # The most critical situation... no trade anymore possible with the bnb discount
		#offset_price=relative_change_pair*offsets_percent[0]*mean_price_pair # How much we offset the limit order relative to the current mean price
		offset_price=delta_change_pair*offsets_percent[0] # How much we offset the limit order relative to the current mean price
	if Nmaxtrades >= 1 and Nmaxtrades < 2: # We can still do one trade... but cannot do more. Quite critical case 
		offset_price=delta_change_pair*offsets_percent[1] # How much we offset the limit order relative to the current mean price
	if Nmaxtrades >= 2 and Nmaxtrades < 3: # We can still do two trades... but cannot do more. We can afford to buy anytime for the next day or so
		offset_price=delta_change_pair*offsets_percent[2] # How much we offset the limit order relative to the current mean price
	if Nmaxtrades >= 3 and Nmaxtrades <= 4: # We can still do 3 or 4 trades... We can afford to buy anytime for the few days
		offset_price=delta_change_pair*offsets_percent[3] # How much we offset the limit order relative to the current mean price
	if Nmaxtrades > 4:
		offset_price=delta_change_pair*offsets_percent[4] # For more than 4 trades
	if verbose == 1:
		print('- Evaluation of the offset price -')
		print('balance_asset (in ref units) = ' + str(balance_asset))
		print('balance_asset_ref = ' + str(balance_asset_ref))
		print('max_fees =' + str(max_fees))
		print('Nmaxtrades = ' + str(Nmaxtrades))
		print('offset_price =' + str(offset_price))
		print('-')
	return Nmaxtrades, offset_price

def decide_place_order(client, asset_pair, asset_qty, orders_open_1, orders_open_2, Nmaxtrades, offset_price, mean_price, timeout_h):
# Function that define when orders are cancelled and when new limit order are put
# Case of place order for pair_A = BNB/USDT:
#   asset_pair= pair_Aref
#   set orders_open_1 = orders_open_check_Bref
#	set orders_open_2 = orders_open_check_Aref
# Case of place order for pair_B = BNB/BTC:
#   asset_pair= pair_Bref
#   set orders_open_1 = orders_open_check_Aref
#	set orders_open_2 = orders_open_check_Bref
	#if (len(orders_open_1) == 0) and (len(orders_open_2) == 0): # If there is no order for the considered pairs
	#	if Nmaxtrades <= 4 : # Perform any kind of buy only if the number of total trades possible is below or equal to 4
	#		place_order(client, mean_price, offset_price, asset_qty, asset_pair
	status_order=False # Default no new order is placed
	status_cancel=False # Default no cancelation is performed
	if (len(orders_open_1) == 0 and len(orders_open_2) == 0): # [D] If no order is listed ===> Nothing to cancel (status_cancel must be True)
		status_cancel=True
	if 	(len(orders_open_1) == 0) and (len(orders_open_2) != 0): # [A] If there is an order in the asset_B and none in asset_A
		print('open order 2 not empty ====> CANCEL ONLY IF TIMEOUT')
		# You cancel the old order only if it is too old and put a new one
		status_cancel=decide_cancel_timeout(client, timeout_h, orders_open_2)
	if 	(len(orders_open_1) != 0) and (len(orders_open_2) == 0): # [B] If there is an order in the asset_A and none in asset_B
		print('open order 1 not empty ====> CANCEL ORDER in 1 (SAFETY)')
		# You cancel the old order only if it is too old and put a new one
		print("All order in queue will be canceled, as they are in the wrong pair")
		for order in orders_open_1:
			result = client.cancel_order(symbol=order["symbol"], orderId=order["orderId"])
			print('raw result for cancel_order(): ', result)
			print("Order " , order["orderId"] , " for " ,  order["symbol"] , " initiated at time " , datetime.fromtimestamp(order['time']/1000.) , " is CANCELLED")
		status_cancel=True
	if 	(len(orders_open_1) != 0) and (len(orders_open_2) != 0): # [C] If there is an order in the asset_A and none in asset_B
		print('open order 1 and 2 not empty  ====> CANCEL ORDERS in 1 and 2 (SAFETY)')
		# You cancel the old order only if it is too old and put a new one
		print("Warning: Found orders in both allowed traded pairs! All will be canceled for safety before setting a new order...")
		for order in orders_open_1:
			result = client.cancel_order(symbol=order["symbol"], orderId=order["orderId"])
			print("Order " , order["orderId"] , " for " ,  order["symbol"] , " initiated at time " , datetime.fromtimestamp(order['time']/1000.) , " is CANCELLED")
		for order in orders_open_2:
			result = client.cancel_order(symbol=order["symbol"], orderId=order["orderId"])
			print("Order " , order["orderId"] , " for " ,  order["symbol"] , " initiated at time " , datetime.fromtimestamp(order['time']/1000.) , " is CANCELLED")
		status_cancel=True	
	if Nmaxtrades <=4 and status_cancel==True: # Put a new order only if the old one was removed and Nmaxtrade is fine
		print('Nmaxtrades is <4 and status is True  ====> PLACING ORDER')
		place_order(client, mean_price, offset_price, asset_qty, asset_pair)
		status_order=True
	if Nmaxtrades <=4 and status_cancel==False:
		print('Nmaxtrades <=4 but a still valid order was put less than', timeout_h , 'd ago    ====> NO NEED FOR A NEW ORDER')
	if Nmaxtrades >4:
		print('Nmaxtrades is >4 ===> NO NEED FOR A NEW ORDER')
	return status_order, status_cancel

def place_order(client, mean_price, offset_price, asset_qty, pair):
	Nprecision=get_precision_from_binance(client, pair)
	form='{0:.' + str(Nprecision) + 'f}'
	limit_price=mean_price - offset_price
	print('Attempting to buy at:' , offset_price , ' below the current ' , pair , ' price...')
	morepass=0
	limit_price, asset_qty, filtered, flag=apply_filter_conditions(client, pair, limit_price, asset_qty, Nprecision, tolerance=0.01, verbose=True)
	limit_price=form.format(limit_price) # Impose the limit_price to be of the same precision as the mean_price
	asset_qty=form.format(asset_qty)
	print('      - Quantity: ', asset_qty)
	print('      - Current price: ' , mean_price)
	print('      - Limit price : '  , limit_price)
	print('      - Percent below current price: ' , '{:0.4f}'.format((np.float(limit_price)-mean_price)/mean_price * 100))
	try:
		#print("    SIMULATED BUY")
		print("    REAL BUY")
		if flag == 'OK':
			order = client.create_order(symbol=pair, side=client.SIDE_BUY, type=client.ORDER_TYPE_LIMIT, quantity=asset_qty, price=limit_price, timeInForce=client.TIME_IN_FORCE_GTC)# REAL BUY
			#order = client.create_test_order(symbol=pair, side=client.SIDE_BUY, type=client.ORDER_TYPE_LIMIT, quantity=asset_qty, price=limit_price, timeInForce=client.TIME_IN_FORCE_GTC)# SIMULATED BUY
			print('Limit order placed')
			print('order:', order)
		if flag == 'WARNING':
			print('Warning: The limit price is ', limit_price, ' which violate the condition limit_price <= current_price*(1 + tolerance) where tolerance=', tolerance, ' and current_price=', mean_price)
			print('Limit order NOT placed')
	except:
		print('Could not place a limit order')
		print('Debug required')
		exit()
	return 0

def decide_cancel_timeout(client, timeout_h, order_list, cancel_all_on_warning=True):
# If an order gets too old, it is canceled. 
# client: main client session
# timeout_h : The requested timeout in hours
# order_list : A list of json-formated order from Binance
# cancel_all_on_warning : If there is a warning, all order in the list are cancel for safety
	timeout_ms=interval_to_milliseconds(timeout_h)
	current_time= client.get_server_time()
	current_time=current_time['serverTime']
	status=False
	print("Number of orders:", len(order_list))
	print(order_list)
	if len(order_list) > 1:
		print("Warning, we are not supposed to have several orders in queue!")
		if cancel_all_on_warning == True:
			print("All order in queue will be canceled, for safety...")
			for order in order_list:
				result = client.cancel_order(symbol=order["symbol"], orderId=order["orderId"])
				print("		Order " , order["orderId"] , " for " ,  order["symbol"] , " initiated at date/time " , datetime.fromtimestamp(order["time"]/1000) , " is CANCELLED")
				status=True
	else:
		for order in order_list:
			if (current_time - np.long(order["time"])) > timeout_ms:
				result = client.cancel_order(symbol=order["symbol"], orderId=order["orderId"])
				print('order["orderId"] =', order["orderId"] )
				print('order["symbol"] =', order["symbol"])
				print(" Age of the listed order in days: ", (current_time - np.long(order['time']))/1000./86400.)
				print("		Order " , order["orderId"] , " for " ,  order["symbol"] , " initiated at date/time " , datetime.fromtimestamp(order["time"]/1000) , " is CANCELLED")
				status=True	
	return status

# --------- START OF THE MAIN --------
	
# Put your READ-ONLY keys
api_key='PUT YOUR API KEY HERE' # smartusd BTC/ETH/LINK API KEY
api_secret='PUT YOUR API SECRET HERE' # smartusd BTC/ETH/LINK API SECRET

# Setup for local data
logfile_noext='~/Trades/buyBNB/logs/datalog'

# Initialisation
stored_exception=None
client = Client(api_key, api_secret)

# Configuration
#check_interval=client.KLINE_INTERVAL_1MINUTE 
check_interval=client.KLINE_INTERVAL_30MINUTE # Time interval between two consecutive checks of the balances and between orders
max_fees_threshold=0.075/100. # Maximum fees that are applied by the exchange. Binance fees are 0.075% but a higher value can be set to ensure bnb margin in the account
asset_A="BNB" # typically the asset for the fees
asset_ref="USDT" # The asset of the stablecoin
asset_B="ETH" # The asset of the smartusd... Typically 'BTC' 'ETH' or 'LINK'
cap_ref=10000. # upper limit on the traded amount. This is due to the new cap introduced on smartusd

pair_Aref=asset_A + asset_ref # The pair considered for refilling the asset used for fees 
pair_AB=asset_A + asset_B # The other possible pair considered for refilling the asset used for fees 
pair_trade=asset_B + asset_ref # The pair considered for the smartusd trade
verbose_lvl=1 # 0 No verbose except errors, 1 full verbose

# Constants: DO NOT CHANGE UNLESS YOU KNOW WHAT YOU ARE DOING
limit_order_timeout=client.KLINE_INTERVAL_1DAY # Maximum time for the limit order to be put before cancelation. If reached the order will be canceled and a new one will be initiated

# offset_price_percent:
# Control by how much we offset the price of the limit order relative to the current price of the 'pair_fees'.
# e.g if the current bnb price is 10usdt, the price amplitude (max-min) over 24h was 1usdt, then with offset_price_percent=10/100, the limit
# order will be at [bnb price] - [bnb amplitude over 24h]*offset_price_percent = 10 - 1*0.1=9.9usdt
# If the order is not filled over 'limit_order_timeout', then a recalculation is performed in a similar manner
# offset_price_percent = offset_price_percent3 if the code detects that the bnb amount available is still fine for 3 to 4 trades
# offset_price_percent = offset_price_percent2 if the code detects that the bnb amount available is still fine for two trades
# offset_price_percent = offset_price_percent1 if the code detects that the bnb amount available is still fine for one trade
# offset_price_percent = offset_price_percent0 if the code detects that the bnb anount available is not fine for at least one trade
offset_price_percent4=1000./100 # if more than 4 trades possible (in practice not used)
offset_price_percent3=150./100 # if 3 or 4 trades possible
offset_price_percent2=30./100 # if 2 trades possible
offset_price_percent1=10./100 # if 1 trade possible
offset_price_percent0=0 # if 0 trades are possible, the limit price is 0% here meaning the buying price is the current price 
offsets_percent=[offset_price_percent0, offset_price_percent1, offset_price_percent2, offset_price_percent3, offset_price_percent4]

asset_qty0 = 4 # Minimal amount to be bought

exit=False
while exit == False:
	t=client.get_server_time()
	time0=t['serverTime']
	tdate=datetime.fromtimestamp(time0/1000)
	if verbose_lvl == 1:
		print('Time ' + str(tdate) + ' (' + str(time0) + ')...'),
		# Getting information on price of the relative value of asset_A vs asset_ref trough pair_Aref
	try:
		stats_pair_Aref = client.get_klines(symbol=pair_Aref, interval=limit_order_timeout, limit=2) # Used to evaluate the variance over the time interval limit_order_timeout
		mean_price_pair_Aref= client.get_avg_price(symbol=pair_Aref)
		# Extract information 
		mean_price_pair_Aref=np.double(mean_price_pair_Aref['price'])
		min_price_pair_Aref=np.double(stats_pair_Aref[0][3]) # [0] is to pick the first object (with limit=1 this is the lated daily candle... me be better to take the closed candle instead)
		max_price_pair_Aref=np.double(stats_pair_Aref[0][2])
		delta_change_pair_Aref=(max_price_pair_Aref-min_price_pair_Aref) #/mean_price_pair_Aref # Changed occured over the last 'limit_order_timeout' (typically 24h)
	except:
		print('could not get the klines or average price for ' + pair_Aref)
		#print('Need debug. Will stop here')
	# Getting information on price of the relative value of asset_A vs asset_B trough pair_AB
	try:
		stats_pair_AB = client.get_klines(symbol=pair_AB, interval=limit_order_timeout, limit=2) # Used to evaluate the variance over the time interval limit_order_timeout
		mean_price_pair_AB= client.get_avg_price(symbol=pair_AB)
		# Extract information
		mean_price_pair_AB=np.double(mean_price_pair_AB['price'])
		min_price_pair_AB=np.double(stats_pair_AB[0][3])
		max_price_pair_AB=np.double(stats_pair_AB[0][2])
		delta_change_pair_AB=(max_price_pair_AB-min_price_pair_AB) #/mean_price_pair_AB # Changed occured over the last 'limit_order_timeout' (typically 24h)
	except:
		print('could not get the klines or average price for ' + pair_AB)
		#print('Need debug. Will stop here')
	# Getting information on price of the relative value of asset_B vs asset_ref trough pair_trade
	try:
		stats_pair_trade = client.get_klines(symbol=pair_trade, interval=limit_order_timeout, limit=2) # Used to evaluate the variance over the time interval limit_order_timeout
		mean_price_pair_trade= client.get_avg_price(symbol=pair_trade)
		mean_price_pair_trade=np.double(mean_price_pair_trade['price'])
	except:
		print('could not get the klines or average price for ' + pair_trade)
		#print('Need debug. Will stop here')

	# Getting the balances for asset A, B and C
	error=True
	while error == True:
		try:
			balance_asset_A = client.get_asset_balance(asset_A) 
			balance_asset_A=np.double(balance_asset_A['free']) # Take the free balance
			print('Balance Asset A (' + asset_A + ') = ' , balance_asset_A )
			error=False
		except :
			print('could not obtain balance for ' + asset_A  + '...Trying again in 10 sec')
			time.sleep(10)
			pass
		error=True
		try:
			balance_asset_ref = client.get_asset_balance(asset_ref)
			balance_asset_ref=np.double(balance_asset_ref['free']) # Take the free balance
			print('Balance Asset ref (' + asset_ref + ') = ' , balance_asset_ref )
			error=False
		except:
			print('could not obtain balance for ' + asset_ref + '...Trying again in 10 sec')
			time.sleep(10)
			pass
		try:
			balance_asset_B = client.get_asset_balance(asset_B)
			balance_asset_B=np.double(balance_asset_B['free']) # Take the free balance
			print('Balance Asset B (' + asset_B + ') = ' , balance_asset_B )
			error=False
		except:
			print('could not obtain balance for ' + asset_B + '...Trying again in 10 sec')
			time.sleep(10)
			pass
	print('----------')

	if error == False:
		# Convert value of asset_B into a value of asset_ref 
		balance_asset_A_base_ref=balance_asset_A*mean_price_pair_Aref # Convert asset_B balance into value of asset_ref
		balance_asset_B_base_ref=balance_asset_B*mean_price_pair_trade # Convert asset_B balance into value of asset_ref
		# Imposing the cap as the maximum balance that is possible to trade
		if balance_asset_A_base_ref > cap_ref and cap_ref>0:
			balance_asset_A_base_ref=cap_ref
		if balance_asset_B_base_ref > cap_ref and cap_ref>0:
			balance_asset_B_base_ref=cap_ref			
		print("Value of " + asset_B + " in " + asset_B + " :", str(balance_asset_B))
		print("Value of " + asset_B + " in " + asset_ref + " :" + str(balance_asset_B_base_ref))
		Nmaxtrades_Aref, offset_price_Aref=eval_offsetprice(balance_asset_A_base_ref, balance_asset_ref, max_fees_threshold, delta_change_pair_Aref, offsets_percent)  # Number of possible trades between asset_A=BNB and asset_ref=USDT
		Nmaxtrades_AB, offset_price_AB=eval_offsetprice(balance_asset_A_base_ref, balance_asset_B_base_ref, max_fees_threshold, delta_change_pair_AB, offsets_percent) # Numver of possible trades between asset_A=BNB and asset_B=BTC
		orders_open_check_Aref = client.get_open_orders(symbol=pair_Aref) # List all open orders of the pair asset_A/asset_ref
		orders_open_check_AB = client.get_open_orders(symbol=pair_AB) # List all open orders of the pair asset_A/asset_B
	
		# Safety to avoid negative prices dues to an offset exceeding the mean price
		# This is likely to happen only when Nmaxtrades_X is very high and should not have any impact on the proper working of the buy (as the buy will not be triggered)
		if offset_price_Aref >= mean_price_pair_Aref:
			offset_price_Aref=0.999*mean_price_pair_Aref
		if offset_price_AB >= mean_price_pair_AB:
			offset_price_AB=0.999*mean_price_pair_AB

		print('  balance_asset_B=', balance_asset_B, ' (' + asset_B + ')')
		print('  balance_asset_ref=', balance_asset_ref,  ' (' + asset_ref + ')')
		if balance_asset_B_base_ref >= balance_asset_ref:
			cost_Ntr0=asset_qty0*mean_price_pair_AB
			asset_qty, error_qty=eval_asset_qty(client, pair_AB, mean_price_pair_AB, balance_asset_B, cost_Ntr0, Flimit=0.02, period=3, Nsigma=3)
			status_order,status_cancel=decide_place_order(client, pair_AB, asset_qty, orders_open_check_Aref, orders_open_check_AB, Nmaxtrades_AB, offset_price_AB, mean_price_pair_AB, limit_order_timeout)
			print('status_order=', status_order)
			s=data_stream(logfile_noext, time0, balance_asset_A, balance_asset_B, balance_asset_ref, pair_AB, asset_qty, pair_AB, pair_Aref, orders_open_check_Aref, orders_open_check_AB, Nmaxtrades_AB, offset_price_AB, mean_price_pair_AB, limit_order_timeout, status_order,status_cancel )
		else:
			cost_Ntr0=asset_qty0*mean_price_pair_Aref
			asset_qty, error_qty=eval_asset_qty(client, pair_Aref, mean_price_pair_Aref, balance_asset_ref, cost_Ntr0, Flimit=0.02, period=3, Nsigma=3)
			status_order,status_cancel=decide_place_order(client, pair_Aref, asset_qty, orders_open_check_AB, orders_open_check_Aref, Nmaxtrades_Aref, offset_price_Aref, mean_price_pair_Aref, limit_order_timeout)
			s=data_stream(logfile_noext, time0, balance_asset_A, balance_asset_B, balance_asset_ref, pair_Aref, asset_qty, pair_AB, pair_Aref, orders_open_check_Aref, orders_open_check_AB, Nmaxtrades_Aref, offset_price_Aref, mean_price_pair_Aref, limit_order_timeout, status_order,status_cancel )

		time.sleep(interval_to_milliseconds(check_interval)/1000.)

# REMAIN TO BE DONE:
#      - Small improvments in the cancellation management: Verify that the order is effectively cancelled by using the client.get_open_orders() command)
#      - Perform the cancellation specifically for the trades that were open and not all associated to the pair ==> requires tracking opened trades IDs

#sys.exit() 
