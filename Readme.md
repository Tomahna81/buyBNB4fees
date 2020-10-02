### Documentation for buyBNB4fees

## Purpose of the program

This program was written specifically to work jointly on a Binance account linked to the SmartUSD 4C Trading services [https://4c-trading.com/](https://4c-trading.com/)
Its purpose is to ensure that there is always a minimum amount of BNB to ensure that the discount on Binance fees (25%) will always be applied during a trade.
It works with any triptic of symbols, but it was thoroughly tested and specifically designed to work to buy BNB when the balance is either BTC or USDT as the concept was built to handle the SmartUSD BTC 4C bot. The recent update of the bots from 4C (**on 1 Oct 2020**) now also allows to use this same program to handle the SmartUSD ETH and the SmartUSD LINK as there is virtually no difference with the currencies, appart from a configuration perspective. 

The code implements two adjustment stategy, one for deciding the buy price (using a limit order) and when to cancel an order, and another for deciding the quantity to buy. The basic concept behind the way this automaton works is twofold:

**[1] Dealing with the buy price.**
If the BNB balance can ensure a large number of trades with respect to the total available balance of the account, there is no urgency to perform a BNBXXX trade. In the SmartUSD context, XXX stands for either USDT, BTC, ETH or LINK. However, if the BNB amount gradually starts to be lower and lower (for examplem, due to successive trades made by the SmartUSD bot), then the bot will increase the urgency level of the order and adjust the limit price to buy BNB in order to reflect that level of urgency. The current version of the code implements 4 level of urgencies:
   - Urgency Level 0: If the amount of BNB allows to perform more than 4 trades at discounted rate using the full available balance, then no order if placed 
   - Urgency Level 1: If the amount of BNB allows 3 or 4 trades, then an order with a 1d lifetime is placed, with a price very far from the current price. It is therefore an opportunistic trade, in case the BNB price collapse strongly relative to USDT or BTC etc...  The threshold are manually set in the code, and the logic behind will be described in the section 'Defining the offset price'.
   - Urgency Level 2: If the amount of BNB allows to perfom between 2 and 3 trades, the limit price is set quite close to the current price.
   - Urgency Level 3: If the amount of BNB allows to perform 1 to 2 trades, the limit price is even further closer to the current price.
   - Urgency Level 4: If the amount of BNB allows less than 1 trade, the limit price is placed at the current price. Thus, a buy will very likely occur almost instantly.
In all those scenario, the order must be filled within a 1 day period and the main balance must not have swaped to another currency between two consecutive checks of the Binance account status (currently set to every 15min). The first condition ensure that the order adjust to the hardly predictible price of the asset. The second condition allows to account for the possiblity that the SmartUSD bot actually perform a trade that would e.g. convert the full USDT balance into BTC and thus preventing any buy of BNB (insuficient balance scenario). 
If those conditions are not fullfilled, the order is cancelled and a new one may be put at the next Binance account status check.

**[2] Dealing with the order quantity. The ordered quantity is autoadjusting using three factors:**
   - The minimum quantity requested to be bought by the user. It is not a very critical quantity, but it is recommended to be set so that it covers a few trades (to avoid to constantly having orders)
   - An user-defined fraction of the total amount of coins for the main asset, ie. for the asset with the highest capital. For example, if the considered assets are BNB, USDT and BTC (Scenario of a SmartUSD BTC), with a balance(USDT)=1000 USD, balance(BTC)=0 USD, then the highest capital is in USDT. If the user set the fraction to 5%, then the maximum amount of BNB that we are allowed to buy is of "0.05 x 1000 = 50 USD". The amount of BNB set to be bought will then of course depend on the current rate for the pair BNBUSDT.
   - The relative difference between the current price and the average price for a given period, along with its variance. The average price serves as a reference to evaluate the possibility of an uptrend (in the case the current price is higher than the mentionned average) or in a downtrend (in the case the current price is lower than the average). Basically, if the price 'looks cheap' compared to the average value, then we should buy a higher quantity than if the price 'looks expensive'. Cheap and Expensive being relative notion, they will be highly dependent on the considered period for computing the average price and variance. Currently the average price is set to be calculated over a period of 3 months (excluding the current month). 

Based on those three variables and some functional defined in the **eval_asset_qty() function**, the quantity of BNB to buy is decided.
This function calculate the quantity to buy by (1) taking a given period (eg. 3 months) in months, (2) determining the sigma and median price over that period
and (3) define a curve like below to evaluate the quantity q to buy, vs price:
```		         
                         ^ q
			 |-----------+ (Pmin, qmax)
			 |            +
			 |	       +
			 |		+
			 |		 + (Pmed, qmin)
			 |	          + -------------
			 |-----------|----|-------------> Price
			           Pmin  Pmed       
```

Here, Pmed is the median price over the specified period (of 3 months). Above that price, we only buy qmin.  Down to **Pmin=Pmed-Nsig.sigma**, the bought quantity increase linearly with the current price. The lower the current price, the more we buy. In the relation just before, sigma is the standard deviation of the price over the specified period and Nsig is fixed to 5. Below the price Pmin, we do not increase the bought quantity as we reach the maximum allowed in term of percent of capital
