from logging import Logger
import numpy as np
from kink import inject
from pandas import DataFrame
from sklearn.metrics import ndcg_score, average_precision_score
from sklearn.model_selection import ParameterGrid
import fireducks.pandas as pd
from fs_repository_interface import FileSystemRepository
from catboost import Pool

@inject()
class ModelValidation:
    MAX_COUNT = 50000
    TARGET_LABEL = "relevance"
    PREDICTION_LABEL = "pred_score"
    GROUPINGS = ["category"]
    FULL_FEATURES = [ "category", "price_bucket", "price", "log_price", "views_norm", "price_rel_cat"]
    STUDENT_FEATURES=[ "category", "price_bucket", "price", "log_price" ]
    VALIDATION_CATEGORY_IDS = [1113, 1219]

    def __init__(self, repository: FileSystemRepository, logger: Logger) -> None:
        self.repository = repository
        self.logger = logger

    def categorize_columns(self, df, categorical_feature):
        for col in categorical_feature:
            df[col] = df[col].astype("category").astype(str)

        return df

    def groupwise_ndcg(self, y_true, y_score, group_ids, k=5):
        results = []
        for g in np.unique(group_ids):
            mask = group_ids == g
            if mask.sum() > 1:
                ndcg = ndcg_score(
                    [y_true[mask]], 
                    [y_score[mask]], 
                    k=k
                )
                results.append((g, ndcg))

        group_ndcg_df = pd.DataFrame(results, columns=['group_id', f'NDCG@{k}'])
        self.logger.debug(group_ndcg_df.describe())  # see distribution
        self.logger.debug(f"NDCG@{k}: \n {group_ndcg_df.sort_values(f'NDCG@{k}').head(100)}")
        return group_ndcg_df

    def calculate_precision_recall_ap(self, y_true, y_pred, group_id, k=10):
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        group_id = np.array(group_id)
        
        unique_groups = np.unique(group_id)

        precision_at_k = []
        recall_at_k = []
        average_precision_list = []


        failed_groups = []
        for group in unique_groups:
            try:
                self.logger.debug(f"Processing group: {group}")
                average_precision = 0.0
                group_indices = np.where(group_id == group)[0]
                y_true_group = y_true[group_indices]
                y_pred_group = y_pred[group_indices]
                sorted_indices = np.argsort(-y_pred_group)
                y_true_sorted = y_true_group[sorted_indices]

                if len(y_true_sorted) > 0:
                    relevant_items_at_k = y_true_sorted[:k] > 0
                    precision_at_k.append(np.mean(relevant_items_at_k))
                    self.logger.debug(f"    Precision@{k}: {precision_at_k[-1]}")
                    
                    total_relevant = np.sum(y_true_sorted > 0)
                    retrieved_relevant = np.sum(relevant_items_at_k)
                    recall_at_k.append(retrieved_relevant / total_relevant if total_relevant > 0 else 0)
                    self.logger.debug(f"    Recall@{k}: {recall_at_k[-1]}")
                
                # Compute Average Precision (AP)
                average_precision = average_precision_score(np.array(y_true_group[:k]), np.array(y_pred_group[:k].reshape(-1, 1)))
                average_precision_list.append(average_precision)
                self.logger.debug(f"    Average Precision: {average_precision}")
            except:
                failed_groups.append(group)

        self.logger.debug(f"Failed {failed_groups}")

        # Calculate the average of the metrics across all groups
        avg_precision_at_k = np.mean(precision_at_k) if precision_at_k else 0
        avg_recall_at_k = np.mean(recall_at_k) if recall_at_k else 0
        avg_average_precision = np.mean(average_precision_list) if average_precision_list else 0

        return avg_precision_at_k, avg_recall_at_k, avg_average_precision

    def evaluate_model(self, df, ranking_model, categorical_columns, features, target, model_name):
        threshold = np.percentile(df[target], 30)
        df[target] = (df[target] >= threshold).astype(int)

        X_test_std, y_test_std, group_ids_test = self.get_stds(df, features, target)
        evaluation_test_pool = Pool(X_test_std, label=y_test_std, group_id=group_ids_test, cat_features=categorical_columns)

        metrics = ranking_model.eval_metrics(
                evaluation_test_pool,
                metrics=[
                    "NDCG:top=5",
                    "PrecisionAt:top=5",
                    "RecallAt:top=5",
                    "MAP:top=5",
                    "MRR:top=5",
                    "ERR:top=5",
                    ]
            )

        self.repository.save_metrics(metrics, f"metrics/{model_name}.json")

    def get_stds(self, df, features, target):
        X = df[features]
        X_std = X.iloc[:self.MAX_COUNT].copy()
        X_std = X_std.sort_values(by=self.GROUPINGS)
        y_std = df[target].iloc[:self.MAX_COUNT].fillna(0)
        group_ids = X_std[self.GROUPINGS]
        return X_std, y_std, group_ids

    def validate(self):
        hyperParameters = self.repository.get_hyperparameters("input/hyperparameters.json")

        self.logger.info(f"[Testing]: Loading Testing Dataset")
        df_test = self.repository.read("testing.csv")

        self.logger.info(f"[Testing]: Testing Data Shape: \n {df_test.shape}")
        self.logger.debug(f"[Testing]: Testing Data: \n {df_test.head()}")

        df_test = self.categorize_columns(df_test, self.GROUPINGS)

        for params in ParameterGrid(hyperParameters):
            df_test = self.Validate_Model(df_test, self.TARGET_LABEL, self.GROUPINGS, self.FULL_FEATURES, params, 'teacher')
            self.logger.info(f"[Testing]: Teacher Model Validation Completed")
            self.logger.info(f"[Testing]: Teacher ended with df_test Sample: \n {df_test.head()}")

            self.Validate_Model(df_test, f"{self.TARGET_LABEL}_teacher", self.GROUPINGS, self.STUDENT_FEATURES + [f"{self.TARGET_LABEL}_teacher"], params, 'student')
            self.logger.info(f"[Testing]: Student Model Validation Completed")
            self.logger.info(f"[Testing]: Student ended with df_test Sample: \n {df_test.head()}")

    def Validate_Model(self, df_test, target, categorical_columns, feature_cols, params, model_type):
        
        model_name=f"model-{params['loss_function']}-{params['depth']}-{params['l2_leaf_reg']}-{params['learning_rate']}-{model_type}"

        X_test_std, y_test_std, group_ids_test = self.get_stds(df_test, feature_cols, target)
        ranking_model = self.repository.load_model("models", f"{model_name}")
        self.evaluate_model(df_test, ranking_model, categorical_columns, feature_cols, target, model_name)

        self.logger.info(f"[Testing]: Making predictions")
        y_pred = ranking_model.predict(X_test_std)
        y_true = y_test_std.values.flatten()
        df_test[f"{target}_{model_type}"] = X_test_std[f"{target}_{model_type}"] = y_pred
        ndcg_global = ndcg_score([y_true], [y_pred.flatten()], k=5)
        self.logger.debug(f"NDCG@5 Global: {ndcg_global}")

        self.logger.info(f"[Testing]: Calculating Full Dataset Group-wise NDCG...")
        flattended_prediction = y_pred.flatten()
        self.groupwise_ndcg(y_true, flattended_prediction, group_ids_test["category"], 5)
        self.groupwise_ndcg(y_true, flattended_prediction, group_ids_test["category"], 10)
        self.groupwise_ndcg(y_true, flattended_prediction, group_ids_test["category"], 100)


        self.logger.info(f"[Testing]: Calculating Choosen Categories")
        for category_id in self.VALIDATION_CATEGORY_IDS:
            mask = (group_ids_test["category"].astype(int).values == category_id)
            y_true_group = y_test_std.values[mask]
            y_pred_group = y_pred.flatten()[mask]

            ndcg = ndcg_score([y_true_group], [y_pred_group], k=5)
            self.logger.debug(f"NDCG@5 Category {category_id}: {ndcg}")
            ndcg = ndcg_score([y_true_group], [y_pred_group], k=10)
            self.logger.debug(f"NDCG@10 Category {category_id}: {ndcg}")
            ndcg = ndcg_score([y_true_group], [y_pred_group], k=100)
            self.logger.debug(f"NDCG@100 Category {category_id}: {ndcg}")

        return df_test


    def ndcg_calculated_metrics(self, target, X, y_true, y_pred):
        self.logger.info(f"[Testing]: Evaluating Custom Calculated NDCG Metrics...")
        # Sort by predicted scores to get the ranking order
        descending_indices = np.argsort(-y_pred)
        y_true_score_sorted = y_true[descending_indices]
        y_true_ideally_sorted = y_true.sort_values(ascending=False)
        
        # Calculating DGC
        X["dcg"] = y_true_score_sorted.to_frame().reset_index().apply(
            lambda row: (row[target] / np.log2(row.name + 2)),
            axis=1
        )
        self.logger.info(f"[Testing]: DCG: \n {X['dcg'].sum()}")
        self.repository.save(X.sort_values(self.PREDICTION_LABEL, ascending=False), "dcg.csv", index=False, force=True)

        # Calculating IDCG
        X["idcg"] = y_true_ideally_sorted.to_frame().reset_index().apply(
            lambda row: (row[target] / np.log2(row.name + 2)),
            axis=1
        )
        self.logger.info(f"[Testing]: IDCG: \n {X['idcg'].sum()}")
        self.repository.save(X.sort_values(target, ascending=False), "idcg.csv", index=False, force=True)

        # Calculating NDCG
        ndcg = X["dcg"].sum() / X["idcg"].sum()
        self.logger.info(f"[Testing]: NDCG: \n {ndcg}")

        return X
