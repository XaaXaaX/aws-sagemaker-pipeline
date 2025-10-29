from logging import Logger
from kink import inject
from sagemaker_repository_interface import SagemakerLocalRepository
import matplotlib.pyplot as plot
import fireducks.pandas as pd
import seaborn as sns

@inject()
class DataUnderstander:
	def __init__(self, repository: SagemakerLocalRepository, logger: Logger):
		self.data_repository = repository
		self.logger = logger
	
	def understand(self):
		self.logger.info(f"Starting data Understanding...")
		df_items = self.data_repository.read('final_items_dataset.csv')

		# for i in list(final_dataset.dtypes[final_dataset.dtypes!=object].index):
		# 	self.logger.info(f"Creating boxplot for: {i}")
		# 	sns.boxplot(data=final_dataset,x=i,orient='v')
		# 	plot.show()



		# for i in list(final_dataset.dtypes[final_dataset.dtypes!=object].index):
		# 	self.logger.info(f"Creating histogram for: {i}")
		# 	sns.histplot(final_dataset[i], kde=True, stat="density")
		# 	plot.show()	

		# self.logger.info(f"Creating correlation matrix")
		corr = df_items.corr(numeric_only=True)
		self.logger.info(f"Correlation Matrix: \n{corr}")
		sns.heatmap(corr, annot=True, fmt=".2f", cmap='coolwarm')
		plot.show()


		self.logger.info(f"Creating pairplot")
		sns.pairplot(data=df_items.head(100000), hue='views', diag_kind='kde')
		plot.show()


		# for i in df_full_items.columns:
		# 	sns.scatterplot(data=df_full_items,x=i,y='category', hue='views')
		# 	plot.show()

		self.logger.info(f"Data Understanding Finished")

		input("Press Enter to continue...")

