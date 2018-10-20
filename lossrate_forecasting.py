from pandas import DataFrame, Series

import ipdb

from amortization import Loan

from os import listdir



# annual incidence curves tell you b/w time t and t-1, what proportion of the bad portfolio goes bad

ANNUAL_INCIDENCE_CURVES = {

	3:Series([.233, .367, .40], index=[1,2,3]),

	2:Series([.388, .612], index=[1,2]),

	1:Series([1.0], index=[1])

}



BADRATE_DIR = 'badrate_tables/'

LOSSRATE_DIR = 'lossrate_tables/'



def get_amortized_balance_curve(interest_rate, term, periods_per_year):

	"""

		Return a Series of remaining balance at each period in time for a fully amortized loan with the inputs.

	"""

	loan = Loan(interest_rate/periods_per_year, term*periods_per_year, 1)

	balance_curve = {}

	period_count = 1

	for period in loan.schedule():

		balance = period.balance

		balance_curve[period_count] = balance

		period_count += 1

	balance_curve = Series(balance_curve)

	return balance_curve



def get_incidence_curves(term, periods_per_year):

	"""

		Returns a Series representing what proportion of the bad portfolio goes bad b/w time t and t-1, where t are periods according to the input periods_per_year

	"""

	annual_incidence_curve = ANNUAL_INCIDENCE_CURVES[term]

	new_index = []

	new_incidence = []

	index_count = 1

	for i in annual_incidence_curve.index:

		annual_incidence = annual_incidence_curve[i]

		# evenly allocate annual incidence across year

		for n in range(periods_per_year):

			new_index.append(index_count)

			new_incidence.append(annual_incidence/periods_per_year)

			index_count += 1 

	return Series(new_incidence, index=new_index)



def forecast_loss_rates_from_bad_rates(bad_rate_csv, term, avg_interest_rate=.14, recovery_rate=0.1, periods_per_year=24):

	"""

		Given an input of a csv of a smoothed bad rate table, spits out forecasted loss rate table in a csv

	"""

	# read bad rates

	bad_rate_df = DataFrame.from_csv(bad_rate_csv)

	orig_cols = bad_rate_df.columns

	orig_rows = bad_rate_df.index

	# calculate amortization curve, given term, avg interest rate, avg loan size

	balance_curve = get_amortized_balance_curve(avg_interest_rate, term, periods_per_year)

	# calculate "incidence curve" (hard coded for now); straight line for 1 year term

	incidence_curve = get_incidence_curves(term, periods_per_year)

	

	data = {}

	# for each cell in the bad rate table

	for col in bad_rate_df.columns:

		new_row = {}

		for row in bad_rate_df.index:

			# get current bad rate

			cur_bad_rate = bad_rate_df[col][row]

			# keep track of cumulative principal lost

			bad_sum = 0

			# for each period

			for period_count in range(1, (term*periods_per_year)+1):

				# calculate periodic bad rate: split bads according to an "incidence curve"

				periodic_bad_rate = cur_bad_rate * incidence_curve[period_count]

				# get previous principal on principal/balance curve

				if period_count == 1:

					previous_balance = 1

				else:

					previous_balance = balance_curve[period_count-1]

				# get current principal on principal/balance curve

				current_balance = balance_curve[period_count]

				# calculate average

				average_balance = (previous_balance + current_balance) / 2.

				# multiply by this period's bad rate

				# multiply by (1-recovery rate)

				cur_bad = average_balance * periodic_bad_rate * (1-recovery_rate)

				# result represents principal lost this period, add it to the counter

				bad_sum += cur_bad

			new_row[row] = bad_sum

		data[col] = new_row

	return DataFrame(data).reindex(columns=orig_cols, index=orig_rows)



def find_csv_filenames( path_to_dir, suffix=".csv" ):

    filenames = listdir(path_to_dir)

    return [ filename for filename in filenames if filename.endswith( suffix ) ]



def _extract_term_from_filename(filename):

	# assuming term is a number, and filename is _ delimited

	tokens = filename.split('_')

	for token in tokens:

		try:

			term = int(token)

			return term

		except:

			continue

	return None



def batch_forecast_loss_rates():

	csvs_names = find_csv_filenames(BADRATE_DIR)

	if len(csvs_names) != 12:

		print 'WARNING: only found %s bad rate tables, not 12' % (len(csvs_names))

	for csv_name in csvs_names:

		term = _extract_term_from_filename(csv_name)

		lossrate_df = forecast_loss_rates_from_bad_rates('%s%s' % (BADRATE_DIR, csv_name), term)

		new_csv_name = csv_name.replace('badrates', 'lossrates')

		lossrate_df.to_csv('%s%s' % (LOSSRATE_DIR, new_csv_name))

		print 'forecasted loss rates for csv %s' % csv_name
