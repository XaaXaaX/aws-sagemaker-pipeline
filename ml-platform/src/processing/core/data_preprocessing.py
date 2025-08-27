import random
import numpy as np
from kink import inject
import fireducks.pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from fs_repository_interface import FileSystemRepository
from logging import Logger

@inject()
class DataPreProcessing:
	target_label = "relevance"
	intentions = {'view': 1, 'addtocart': 1, 'transaction': 1}

	def __init__(self, repository: FileSystemRepository, logger: Logger):
		self.data_repository = repository
		self.logger = logger

	def prepare_events(self, df):
		df.loc[:, 'event_code'] = df.loc[:, 'event'].map(self.intentions).astype(int)
		df.loc[:, 'views'] = df[df.loc[:, 'event_code'] == 1].groupby(['visitorid', 'itemid']).transform('count')['event_code'].astype(int)
		df.loc[:, 'favorites'] = df[df.loc[:, 'event_code'] == 2].groupby(['visitorid', 'itemid']).transform('count')['event_code'].astype(int)
		df.loc[:, 'purchased'] = df[df.loc[:, 'event_code'] == 3].groupby(['visitorid', 'itemid']).transform('count')['event_code'].astype(int)

		df.drop_duplicates(['visitorid', 'itemid', 'event_code'], inplace=True)
		df = df.groupby(['visitorid', 'itemid']).max().reset_index()
		df.fillna({'transactionid': 0}, inplace=True)
		df.sort_values(['visitorid', 'timestamp'], inplace=True)
		df.drop(columns=['event', 'timestamp', 'transactionid', 'event_code'], inplace=True)
		df.set_index(['visitorid', 'itemid'], inplace=True)
		self.logger.info(f"Total Visitor Events Data Shape: {df.shape}")

		return df
	
	def prepare_items_stats(self, df):
		df = df.groupby(['itemid']).sum()
		self.logger.info(f"Items Stats Data Shape: {df.shape}")
		return df
	
	def prepare_item_characteristics(self, df):
		df = df[df.loc[:, 'property'] == 'categoryid']
		df['category'] = df.loc[:, 'value'].astype(int)
		df.drop(columns=['property', 'value'], inplace=True)
		df.set_index('itemid', inplace=True)
		df.sort_values('itemid', inplace=True)
		self.logger.info(f"Item Categories: {df.shape}")
		self.logger.debug(f"All Items: \n{df.head()}")
		return df

	def assign_random_per_category(self, group, column):
		price_step = range(1, 900, 50)
		step = random.choice(price_step)
		min_val = random.choice(range(5000, 54000, step))

		possible_max = list(range(min_val + step, 55000, step))
		if not possible_max:
			possible_max = [min_val + step]

		max_val = random.choice(possible_max)

		if max_val <= min_val:
			max_val = min_val + step

		items = range(min_val, max_val)
		group[column] = np.random.choice(items, size=len(group))
		return group
	
	def enrich_data(self, df):
		weights = {
            "views": 1,
            "favorites": 3,
            "purchased": 5
        }

		df.fillna({"views": 0, "favorites": 0, "purchased": 0}, inplace=True)
		df["views"] = df["views"].clip(lower=1)
		df["favorites"] = df["favorites"].clip(lower=0)
		df["purchased"] = df["purchased"].clip(lower=0)

		df.loc[:, self.target_label] = \
			weights["views"] * df['views'] + \
			weights["favorites"] * df['favorites'] + \
			weights["purchased"] * df['purchased']

		
		df = df.groupby("category", group_keys=False)[df.columns].apply(self.assign_random_per_category, column="price")
		df["views_norm"] = df.groupby("category")["views"].transform( lambda x: x / (x.mean() + 1e-6) )
		df["price_rel_cat"] = df.groupby("category")["price"].transform( lambda x: x / (x.median() + 1e-6) )
		df['price_x_views'] = df['price'] * df['views_norm']
		df['price_rel_cat_x_views'] = df['price_rel_cat'] * df['views_norm']


		return df

	def normalize(self, encoder, df, columns):
		norm = encoder.fit(df[columns].values)
		df[columns] = norm.transform(df[columns].values)
		return df

	def normalize_score(self, df):
		return self.normalize(MinMaxScaler(), df, ["price"])

	def prepare(self):
		self.logger.info(f"Starting data Processing...")

		df_events = self.data_repository.read('events.csv')
		df_items = pd.concat([ 
			self.data_repository.read('item_properties_part1.csv').drop('timestamp', axis=1),
			self.data_repository.read('item_properties_part2.csv').drop('timestamp', axis=1)
		])

		df_events = self.prepare_events(df_events)
		df_items_stats = self.prepare_items_stats(df_events.copy(deep=True))
		df_items = self.prepare_item_characteristics(df_items)

		df_items = df_items.join(df_items_stats, how='left', lsuffix='', rsuffix='_right', on='itemid')
		df_items.drop_duplicates(inplace=True)

		df_items = self.enrich_data(df_items)
		
		self.logger.info(f"Final Items: {df_items.shape}")
		self.logger.debug(f"Final Items: \n{df_items.head()}")

		# Split the data into training and testing sets
		train_set, test_set = train_test_split(
			df_items, 
			train_size=0.70, 
			test_size=0.30, 
			random_state=42
		)

		# Save the datasets
		self.logger.info(f"Shape of test_set:  \n {test_set.shape}")
		self.data_repository.save(data=test_set, path=f'testing.csv', index=True, force=True)
		self.logger.info(f"Shape of train_set:  \n {train_set.shape}")
		self.data_repository.save(data=train_set, path=f'training.csv', index=True, force=True)
